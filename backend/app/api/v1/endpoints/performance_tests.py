"""
性能测试 API 端点
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime

from app.db.session import get_db
from app.models.performance_test import PerformanceTest
from app.models.project import Project
from app.schemas.performance_test import (
    PerformanceTestCreate, PerformanceTestUpdate, PerformanceTestOut,
    PerformanceTestDetail, K6ScriptGenerateRequest, K6ScriptGenerateResponse,
    PerformanceTestExecuteRequest, PerformanceTestAnalysisRequest
)
from app.services.k6_executor import K6Executor
from app.services.k6_analysis_service import K6AnalysisService
from ai_engine.processors.k6_test_generator import K6TestGenerator
from ai_engine.models.ai_client import AIClient

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化服务
try:
    k6_executor = K6Executor()
except RuntimeError as e:
    logger.warning(f"k6 执行器初始化失败: {e}，性能测试功能可能不可用")
    k6_executor = None

k6_analysis_service = K6AnalysisService()
ai_client = AIClient()
k6_generator = K6TestGenerator(ai_client)


@router.post("/generate-script", response_model=K6ScriptGenerateResponse)
async def generate_k6_script(
    request: K6ScriptGenerateRequest,
    db: Session = Depends(get_db)
):
    """通过 AI 生成 k6 性能测试脚本"""
    try:
        logger.info(f"[API] 收到生成脚本请求: test_description={request.test_description[:100]}, target_url={request.target_url}, load_config={request.load_config}")
        # 调用 AI 生成 k6 脚本
        result = await k6_generator.generate(
            test_description=request.test_description,
            target_url=request.target_url,
            load_config=request.load_config
        )
        logger.info(f"[API] 脚本生成结果: status={result.get('status')}")
        
        if result.get("status") == "success":
            return K6ScriptGenerateResponse(
                status="success",
                script=result.get("script"),
                test_description=request.test_description
            )
        else:
            return K6ScriptGenerateResponse(
                status="error",
                test_description=request.test_description,
                error=result.get("error", "生成失败")
            )
            
    except Exception as e:
        logger.error(f"生成 k6 脚本失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/", response_model=PerformanceTestOut)
async def create_performance_test(
    request: PerformanceTestCreate,
    db: Session = Depends(get_db)
):
    """创建性能测试（仅创建，不自动执行）"""
    try:
        # 验证项目存在
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        # 生成 k6 脚本
        script_result = await k6_generator.generate(
            test_description=request.test_description,
            target_url=request.target_url,
            load_config=request.load_config
        )
        
        if script_result.get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail=f"生成 k6 脚本失败: {script_result.get('error', '未知错误')}"
            )
        
        k6_script = script_result.get("script")
        
        # 创建性能测试记录
        performance_test = PerformanceTest(
            project_id=request.project_id,
            name=request.name,
            description=request.description,
            k6_script=k6_script,
            script_generated_by_ai="yes",
            ai_prompt=request.test_description,
            execution_config=request.load_config or {},
            status="pending"
        )
        
        db.add(performance_test)
        db.commit()
        db.refresh(performance_test)
        
        return PerformanceTestOut.model_validate(performance_test)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建性能测试失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


async def execute_performance_test_async(
    performance_test_id: int,
    db: Session = None
):
    """异步执行性能测试"""
    # 创建独立的数据库session，避免阻塞主请求的数据库连接
    from app.db.session import SessionLocal
    import asyncio
    
    if db is None:
        db = SessionLocal()
    
    try:
        performance_test = db.query(PerformanceTest).filter(
            PerformanceTest.id == performance_test_id
        ).first()
        
        if not performance_test:
            logger.error(f"性能测试 {performance_test_id} 不存在")
            return
        
        if not k6_executor:
            logger.error("k6 执行器未初始化")
            performance_test.status = "failed"
            performance_test.end_time = datetime.utcnow()
            db.commit()
            return
        
        # 状态已经在 execute_performance_test 中更新为 running，这里不需要再次更新
        # 但如果状态不是 running（可能是其他情况），确保设置为 running
        if performance_test.status != "running":
            performance_test.status = "running"
            if not performance_test.start_time:
                performance_test.start_time = datetime.utcnow()
            db.commit()
        
        # 在线程池中执行阻塞的 k6 调用，避免阻塞 FastAPI 事件循环
        # 使用 run_in_executor 在线程池中执行，这样不会阻塞事件循环
        logger.info(f"开始在线程池中执行 k6 脚本（性能测试 ID: {performance_test_id}）")
        loop = asyncio.get_event_loop()
        execution_result = await loop.run_in_executor(
            None,  # 使用默认的 ThreadPoolExecutor
            k6_executor.execute,
            performance_test.k6_script,  # script_content
            "summary"  # output_format，使用summary格式，数据量小
        )
        logger.info(f"k6 脚本执行完成（性能测试 ID: {performance_test_id}）")
        
        # 更新结果
        # k6_executor返回的status可能是"success"或"completed"，统一转换为"completed"
        executor_status = execution_result.get("status", "failed")
        if executor_status == "success":
            performance_test.status = "completed"
        else:
            performance_test.status = executor_status
        performance_test.end_time = datetime.utcnow()
        
        if performance_test.start_time:
            duration = (performance_test.end_time - performance_test.start_time).total_seconds()
            performance_test.duration = duration
        
        # 保存执行结果（只保存汇总数据，不保存详细的时间序列数据）
        results = {
            "execution_result": {
                "status": execution_result.get("status"),
                "exit_code": execution_result.get("exit_code", -1),
                "executed_at": execution_result.get("executed_at"),
                # 保存错误信息（如果有）
                "error": execution_result.get("error"),
                # 保存stderr的最后1000个字符（用于调试，不保存全部因为可能很大）
                "stderr": execution_result.get("stderr", "")[-1000:] if execution_result.get("stderr") else None,
                # 保存stdout的最后2000个字符（用于查看关键输出）
                "stdout": execution_result.get("stdout", "")[-2000:] if execution_result.get("stdout") else None,
            },
            "metrics": execution_result.get("metrics", {}),
            "summary": execution_result.get("summary", {}),  # 保存汇总JSON
        }
        
        # 如果执行失败，记录详细错误信息
        if execution_result.get("status") != "success":
            error_msg = execution_result.get("error", "执行失败")
            stderr = execution_result.get("stderr", "")
            stdout = execution_result.get("stdout", "")
            logger.error(f"k6执行失败 - 退出码: {execution_result.get('exit_code')}, 错误: {error_msg}")
            if stderr:
                logger.error(f"k6 stderr: {stderr[:500]}")  # 只记录前500字符
            if stdout:
                logger.warning(f"k6 stdout: {stdout[:500]}")  # 只记录前500字符
        performance_test.results = results
        flag_modified(performance_test, "results")
        
        db.commit()
        db.refresh(performance_test)
        
        # 自动分析结果
        if execution_result.get("status") == "success" and execution_result.get("metrics"):
            analysis_result = await k6_analysis_service.analyze_performance_results(
                performance_test_id=performance_test.id,
                test_name=performance_test.name,
                test_description=performance_test.description or "",
                k6_results=execution_result,
                k6_metrics=execution_result.get("metrics", {})
            )
            
            performance_test.analysis = analysis_result.get("analysis", {})
            performance_test.analysis_generated_at = datetime.utcnow()
            flag_modified(performance_test, "analysis")
            db.commit()
        
    except Exception as e:
        logger.error(f"执行性能测试失败: {e}", exc_info=True)
        # 更新状态为失败
        try:
            performance_test = db.query(PerformanceTest).filter(
                PerformanceTest.id == performance_test_id
            ).first()
            if performance_test:
                performance_test.status = "failed"
                performance_test.end_time = datetime.utcnow()
                db.commit()
        except Exception as commit_error:
            logger.error(f"更新失败状态时出错: {commit_error}")
    finally:
        # 确保关闭独立的数据库session
        if db is not None:
            db.close()


@router.get("/", response_model=List[PerformanceTestOut])
async def list_performance_tests(
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取性能测试列表（快速响应，不阻塞）"""
    try:
        # 使用独立的查询，避免被长时间运行的后台任务阻塞
        query = db.query(PerformanceTest)
        
        if project_id:
            query = query.filter(PerformanceTest.project_id == project_id)
        
        # 只查询必要字段，减少数据传输量
        performance_tests = query.order_by(PerformanceTest.created_at.desc()).offset(skip).limit(limit).all()
        
        # 快速返回，不等待后台任务完成
        return [PerformanceTestOut.model_validate(pt) for pt in performance_tests]
    except Exception as e:
        logger.error(f"获取性能测试列表失败: {e}", exc_info=True)
        # 检查是否是表不存在的问题
        try:
            from sqlalchemy import inspect
            from app.db.session import engine
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if 'performance_tests' not in tables:
                raise HTTPException(
                    status_code=500,
                    detail="performance_tests 表不存在，请运行数据库迁移或初始化脚本：cd backend && python init_db.py"
                )
        except Exception:
            pass  # 如果检查失败，继续抛出原始错误
        raise HTTPException(status_code=500, detail=f"获取性能测试列表失败: {str(e)}")


@router.get("/{performance_test_id}", response_model=PerformanceTestDetail)
async def get_performance_test(
    performance_test_id: int,
    db: Session = Depends(get_db)
):
    """获取性能测试详情"""
    performance_test = db.query(PerformanceTest).filter(
        PerformanceTest.id == performance_test_id
    ).first()
    
    if not performance_test:
        raise HTTPException(status_code=404, detail="性能测试不存在")
    
    return PerformanceTestDetail.model_validate(performance_test)


@router.post("/{performance_test_id}/execute", response_model=PerformanceTestOut)
async def execute_performance_test(
    performance_test_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """手动执行性能测试"""
    if not k6_executor:
        raise HTTPException(status_code=503, detail="k6 未安装，请先安装 k6")
    
    performance_test = db.query(PerformanceTest).filter(
        PerformanceTest.id == performance_test_id
    ).first()
    
    if not performance_test:
        raise HTTPException(status_code=404, detail="性能测试不存在")
    
    if performance_test.status == "running":
        raise HTTPException(status_code=400, detail="测试正在执行中")
    
    if not performance_test.k6_script:
        raise HTTPException(status_code=400, detail="测试脚本不存在")
    
    # 立即更新状态为 running，确保前端可以立即看到状态变化
    performance_test.status = "running"
    performance_test.start_time = datetime.utcnow()
    db.commit()
    db.refresh(performance_test)
    
    # 在后台执行（不传递db session，让后台任务创建独立的session）
    background_tasks.add_task(
        execute_performance_test_async,
        performance_test_id
    )
    
    # 返回更新后的性能测试对象
    return PerformanceTestOut.model_validate(performance_test)


@router.post("/{performance_test_id}/analyze", response_model=PerformanceTestOut)
async def analyze_performance_test(
    performance_test_id: int,
    db: Session = Depends(get_db)
):
    """分析性能测试结果"""
    print(f"\n{'='*80}")
    print(f"[API] ========== 收到分析请求 ==========")
    print(f"[API] 请求的测试ID: {performance_test_id}")
    print(f"[API] 请求路径: /performance-tests/{performance_test_id}/analyze")
    print(f"{'='*80}\n")
    logger.info(f"[API] ========== 收到分析请求 ==========")
    logger.info(f"[API] 请求的测试ID: {performance_test_id}")
    logger.info(f"[API] 请求路径: /performance-tests/{performance_test_id}/analyze")
    
    performance_test = db.query(PerformanceTest).filter(
        PerformanceTest.id == performance_test_id
    ).first()
    
    if not performance_test:
        logger.error(f"[API] ❌ 性能测试不存在: ID={performance_test_id}")
        raise HTTPException(status_code=404, detail="性能测试不存在")
    
    print(f"[API] ✅ 找到性能测试: ID={performance_test.id}, 名称={performance_test.name}, 状态={performance_test.status}")
    logger.info(f"[API] ✅ 找到性能测试: ID={performance_test.id}, 名称={performance_test.name}, 状态={performance_test.status}")
    
    # 检查测试是否已完成
    if performance_test.status not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="请先完成测试执行")
    
    if not performance_test.results:
        raise HTTPException(status_code=400, detail="测试结果不存在，请先执行测试")
    
    results = performance_test.results
    execution_result = results.get("execution_result", {})
    metrics = results.get("metrics", {})
    # 获取原始执行输出（stdout）
    k6_stdout = execution_result.get("stdout", "") or results.get("stdout", "")
    
    # 获取项目信息
    project = performance_test.project
    project_name = project.name if project else "未知项目"
    project_description = project.description if project and hasattr(project, 'description') else ""
    
    # 执行分析
    print(f"[API] 开始分析性能测试: ID={performance_test.id}")
    print(f"[API] 测试名称: {performance_test.name}")
    print(f"[API] 测试状态: {performance_test.status}")
    print(f"[API] 是否有结果: {bool(performance_test.results)}")
    print(f"[API] 是否有指标: {bool(metrics)}")
    print(f"[API] 是否有stdout: {bool(k6_stdout)}, 长度: {len(k6_stdout) if k6_stdout else 0} 字符")
    logger.info(f"[API] 开始分析性能测试: ID={performance_test.id}")
    logger.info(f"[API] 测试名称: {performance_test.name}")
    logger.info(f"[API] 测试状态: {performance_test.status}")
    logger.info(f"[API] 是否有结果: {bool(performance_test.results)}")
    logger.info(f"[API] 是否有指标: {bool(metrics)}")
    logger.info(f"[API] 是否有stdout: {bool(k6_stdout)}, 长度: {len(k6_stdout) if k6_stdout else 0} 字符")
    
    analysis_result = await k6_analysis_service.analyze_performance_results(
        performance_test_id=performance_test.id,
        test_name=performance_test.name,
        test_description=performance_test.description or "",
        test_requirement=performance_test.ai_prompt or performance_test.description or "",
        project_name=project_name,
        project_description=project_description,
        k6_results=execution_result,
        k6_metrics=metrics,
        k6_stdout=k6_stdout
    )
    
    logger.info(f"[API] 分析完成，结果状态: {analysis_result.get('status')}")
    logger.info(f"[API] ==========================================")
    
    # 检查分析结果状态
    if analysis_result.get("status") == "error":
        logger.error(f"性能测试分析失败: {analysis_result.get('error')}")
        raise HTTPException(
            status_code=500,
            detail=analysis_result.get("error", "AI分析失败")
        )
    
    # 保存分析结果
    analysis_data = analysis_result.get("analysis", {})
    if not analysis_data or (isinstance(analysis_data, dict) and len(analysis_data) == 0):
        logger.warning(f"性能测试分析结果为空")
        raise HTTPException(
            status_code=500,
            detail="AI分析结果为空，请检查AI引擎是否正常运行"
        )
    
    # 记录分析数据的结构
    logger.info(f"[API] 保存分析结果，键: {list(analysis_data.keys())[:10]}")
    if "markdown" in analysis_data:
        logger.info(f"[API] Markdown字段存在，长度: {len(analysis_data['markdown']) if isinstance(analysis_data['markdown'], str) else 'N/A'}")
    else:
        logger.warning(f"[API] ⚠️ Markdown字段不存在于分析结果中")
    
    performance_test.analysis = analysis_data
    performance_test.analysis_generated_at = datetime.utcnow()
    flag_modified(performance_test, "analysis")
    db.commit()
    db.refresh(performance_test)
    
    # 验证保存后的数据
    if performance_test.analysis and isinstance(performance_test.analysis, dict):
        logger.info(f"[API] 保存后的分析数据键: {list(performance_test.analysis.keys())[:10]}")
        if "markdown" in performance_test.analysis:
            logger.info(f"[API] ✅ Markdown已保存到数据库")
    
    logger.info(f"[API] ✅ 分析完成并保存，返回更新后的性能测试对象")
    # 返回更新后的性能测试对象（符合PerformanceTestOut模型）
    return performance_test


@router.put("/{performance_test_id}", response_model=PerformanceTestOut)
async def update_performance_test(
    performance_test_id: int,
    request: PerformanceTestUpdate,
    db: Session = Depends(get_db)
):
    """更新性能测试"""
    performance_test = db.query(PerformanceTest).filter(
        PerformanceTest.id == performance_test_id
    ).first()
    
    if not performance_test:
        raise HTTPException(status_code=404, detail="性能测试不存在")
    
    if request.name:
        performance_test.name = request.name
    if request.description is not None:
        performance_test.description = request.description
    if request.k6_script:
        performance_test.k6_script = request.k6_script
    if request.execution_config:
        performance_test.execution_config = request.execution_config
        flag_modified(performance_test, "execution_config")
    
    db.commit()
    db.refresh(performance_test)
    
    return PerformanceTestOut.from_orm(performance_test)


@router.delete("/{performance_test_id}")
async def delete_performance_test(
    performance_test_id: int,
    db: Session = Depends(get_db)
):
    """删除性能测试"""
    performance_test = db.query(PerformanceTest).filter(
        PerformanceTest.id == performance_test_id
    ).first()
    
    if not performance_test:
        raise HTTPException(status_code=404, detail="性能测试不存在")
    
    db.delete(performance_test)
    db.commit()
    
    return {"status": "success", "message": "性能测试已删除"}


# 添加 logger
import logging
logger = logging.getLogger(__name__)

