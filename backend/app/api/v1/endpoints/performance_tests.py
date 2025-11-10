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
    from app.core.config import settings
    k6_binary_path = settings.K6_BINARY_PATH if hasattr(settings, 'K6_BINARY_PATH') else None
    k6_executor = K6Executor(k6_binary_path=k6_binary_path)
    logger.info(f"k6 执行器初始化成功，使用路径: {k6_executor.k6_binary_path}")
except RuntimeError as e:
    logger.warning(f"k6 执行器初始化失败: {e}，性能测试功能可能不可用")
    k6_executor = None
except Exception as e:
    logger.error(f"k6 执行器初始化异常: {e}", exc_info=True)
    k6_executor = None

k6_analysis_service = K6AnalysisService()
ai_client = AIClient()
k6_generator = K6TestGenerator(ai_client)


async def _auto_analyze_performance_test(
    performance_test_id: int,
    db: Session = None
):
    """
    自动分析性能测试结果（内部函数，不抛出异常）
    
    Args:
        performance_test_id: 性能测试ID
        db: 数据库会话（如果为None，会创建新的会话）
    """
    logger.info(f"[自动分析] ===== 开始自动分析性能测试: {performance_test_id} =====")
    
    from app.db.session import SessionLocal
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True
        logger.info(f"[自动分析] 创建新的数据库会话")
    
    try:
        # 重新查询测试记录（确保获取最新数据）
        performance_test = db.query(PerformanceTest).filter(
            PerformanceTest.id == performance_test_id
        ).first()
        
        if not performance_test:
            logger.error(f"[自动分析] 性能测试不存在: {performance_test_id}")
            return
        
        # 检查是否已有分析结果
        if performance_test.analysis and performance_test.analysis.get("markdown"):
            logger.info(f"[自动分析] 测试 {performance_test_id} 已有分析结果，跳过自动分析")
            return
        
        # 检查是否有测试结果
        if not performance_test.results:
            logger.warning(f"[自动分析] 测试 {performance_test_id} 没有测试结果，无法分析")
            return
        
        # 检查测试状态（只分析成功完成的测试）
        if performance_test.status not in ["completed", "success"]:
            logger.info(f"[自动分析] 测试 {performance_test_id} 状态为 {performance_test.status}，跳过自动分析")
            return
        
        logger.info(f"[自动分析] 开始分析测试 {performance_test_id}")
        
        # 获取项目信息
        project = db.query(Project).filter(Project.id == performance_test.project_id).first()
        project_name = project.name if project else ""
        project_description = project.description if project else ""
        
        # 从 results 中提取 metrics 和 stdout
        results = performance_test.results if isinstance(performance_test.results, dict) else {}
        metrics = results.get("metrics", {})
        execution_result = results.get("execution_result", {})
        stdout = execution_result.get("stdout", "") if isinstance(execution_result, dict) else ""
        
        # 调用分析服务（不传入自定义提示词，使用默认分析）
        analysis_result = await k6_analysis_service.analyze_performance_results(
            performance_test_id=performance_test_id,
            test_name=performance_test.name or "",
            test_description=performance_test.description or "",
            test_requirement=performance_test.ai_prompt or "",
            project_name=project_name,
            project_description=project_description,
            k6_results=results,
            k6_metrics=metrics,
            k6_stdout=stdout,
            prompt=None  # 使用默认分析提示词
        )
        
        # 检查分析结果状态
        if analysis_result.get("status") == "error":
            error_msg = analysis_result.get("error", "分析失败")
            logger.error(f"[自动分析] 分析服务返回错误: {error_msg}")
            # 不抛出异常，只记录错误，不影响测试结果
            return
        
        # 获取分析数据
        analysis_data = analysis_result.get("analysis", {})
        
        if not analysis_data:
            logger.warning(f"[自动分析] 分析结果为空: {performance_test_id}")
            return
        
        # 保存分析结果
        performance_test.analysis = analysis_data
        performance_test.analysis_generated_at = datetime.utcnow()
        flag_modified(performance_test, "analysis")
        db.commit()
        
        logger.info(f"[自动分析] 分析完成，已保存到数据库: performance_test_id={performance_test_id}")
        logger.info(f"[自动分析] ===== 自动分析流程结束 =====")
        
    except Exception as e:
        # 自动分析失败不应该影响测试执行结果
        logger.error(f"[自动分析] 自动分析失败: {performance_test_id}, 错误: {e}", exc_info=True)
        # 不抛出异常，只记录错误
    
    finally:
        # 如果创建了新的数据库会话，需要关闭
        if should_close_db and db is not None:
            try:
                db.close()
                logger.info(f"[自动分析] 数据库会话已关闭: {performance_test_id}")
            except Exception as e:
                logger.error(f"[自动分析] 关闭数据库会话失败: {e}", exc_info=True)


@router.post("/generate-script", response_model=K6ScriptGenerateResponse)
async def generate_k6_script(
    request: K6ScriptGenerateRequest,
    db: Session = Depends(get_db)
):
    """生成 k6 性能测试脚本"""
    try:
        logger.info(f"生成 k6 脚本，模式: {request.generation_mode}")
        result = await k6_generator.generate(
            test_description=request.test_description,
            target_url=request.target_url,
            load_config=request.load_config,
            generation_mode=request.generation_mode or "regex"
        )
        return K6ScriptGenerateResponse(**result)
    except Exception as e:
        logger.error(f"生成 k6 脚本失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成 k6 脚本失败: {str(e)}")


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
        
        # 生成或使用提供的 k6 脚本
        if request.k6_script and request.k6_script.strip():
            # 如果提供了有效的脚本，直接使用（前端已生成）
            logger.info(f"[创建性能测试] 使用前端提供的脚本（长度: {len(request.k6_script)} 字符）")
            k6_script = request.k6_script
        else:
            # 如果脚本为空或未提供，后端生成脚本
            if request.k6_script:
                logger.warning(f"[创建性能测试] 前端提供的脚本为空，将重新生成")
            # 否则，后端生成脚本
            generation_mode = getattr(request, 'generation_mode', 'regex') or "regex"
            logger.info(f"[创建性能测试] 使用生成模式: {generation_mode}")
            
            try:
                script_result = await k6_generator.generate(
                    test_description=request.test_description,
                    target_url=request.target_url,
                    load_config=request.load_config,
                    generation_mode=generation_mode
                )
            except Exception as e:
                logger.error(f"[创建性能测试] 生成脚本异常: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(
                    status_code=500,
                    detail=f"生成 k6 脚本时发生错误: {str(e)}"
                )
            
            if script_result.get("status") != "success":
                error_msg = script_result.get('error', '未知错误')
                logger.error(f"[创建性能测试] 生成脚本失败: {error_msg}")
                raise HTTPException(
                    status_code=400,
                    detail=f"生成 k6 脚本失败: {error_msg}"
                )
            
            k6_script = script_result.get("script")
            if not k6_script or not k6_script.strip():
                logger.error(f"[创建性能测试] 生成的脚本为空")
                raise HTTPException(
                    status_code=400,
                    detail="生成的脚本为空，无法创建测试。请检查测试需求描述或AI服务状态。"
                )
        
        # 最终验证脚本是否有效
        if not k6_script or not k6_script.strip():
            logger.error(f"[创建性能测试] 脚本验证失败：脚本为空")
            raise HTTPException(
                status_code=400,
                detail="脚本验证失败：脚本为空。无法创建测试。"
            )
        
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
        
        # 再次验证保存后的脚本是否存在
        if not performance_test.k6_script or not performance_test.k6_script.strip():
            logger.error(f"[创建性能测试] 保存后脚本验证失败：脚本为空")
            db.delete(performance_test)
            db.commit()
            raise HTTPException(
                status_code=500,
                detail="保存后脚本验证失败：脚本为空。无法创建测试。"
            )
        
        logger.info(f"[创建性能测试] 测试创建成功，ID: {performance_test.id}")
        return PerformanceTestOut.model_validate(performance_test)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建性能测试失败: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建性能测试失败: {str(e)}")


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
    
    # 更新字段
    if request.name is not None:
        performance_test.name = request.name
    if request.description is not None:
        performance_test.description = request.description
    if request.k6_script is not None:
        performance_test.k6_script = request.k6_script
    if request.load_config is not None:
        performance_test.execution_config = request.load_config
        flag_modified(performance_test, "execution_config")
    
    db.commit()
    db.refresh(performance_test)
    
    return PerformanceTestOut.model_validate(performance_test)


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
    
    return {"message": "性能测试已删除"}


async def execute_performance_test_async(
    performance_test_id: int,
    db: Session = None
):
    """异步执行性能测试"""
    logger.info(f"[异步执行] ===== 开始执行性能测试: {performance_test_id} =====")
    
    from app.db.session import SessionLocal
    if db is None:
        db = SessionLocal()
        logger.info(f"[异步执行] 创建新的数据库会话")
    
    try:
        logger.info(f"[异步执行] 查询测试记录: {performance_test_id}")
        performance_test = db.query(PerformanceTest).filter(
            PerformanceTest.id == performance_test_id
        ).first()
        
        if not performance_test:
            logger.error(f"[异步执行] 性能测试不存在: {performance_test_id}")
            return
        
        logger.info(f"[异步执行] 找到测试记录: ID={performance_test_id}, 名称={performance_test.name}, 当前状态={performance_test.status}")
        
        # 验证脚本是否存在
        if not performance_test.k6_script or not performance_test.k6_script.strip():
            logger.error(f"[异步执行] 性能测试脚本为空: {performance_test_id}")
            performance_test.status = "failed"
            performance_test.end_time = datetime.utcnow()
            # 将错误信息存储在results中
            performance_test.results = {"error": "测试脚本为空，无法执行"}
            db.commit()
            return
        
        script_length = len(performance_test.k6_script)
        logger.info(f"[异步执行] 脚本长度: {script_length} 字符")
        logger.info(f"[异步执行] 开始执行性能测试: {performance_test_id}")
        performance_test.status = "running"
        performance_test.start_time = datetime.utcnow()  # 使用模型中的字段名 start_time
        db.commit()
        
        # 执行 k6 测试
        if k6_executor is None:
            error_msg = "k6 执行器未初始化，请检查k6是否已安装"
            logger.error(f"[异步执行] {error_msg}")
            performance_test.status = "failed"
            performance_test.end_time = datetime.utcnow()
            performance_test.results = {"error": error_msg}
            db.commit()
            return
        
        logger.info(f"[异步执行] k6执行器可用，路径: {k6_executor.k6_binary_path}")
        logger.info(f"[异步执行] 准备在线程池中执行k6命令")
        
        # k6_executor.execute 是同步方法，需要在后台线程中运行
        import asyncio
        loop = asyncio.get_event_loop()
        try:
            logger.info(f"[异步执行] 在线程池中执行k6命令，开始时间: {datetime.utcnow()}")
            result = await loop.run_in_executor(
                None,
                lambda: k6_executor.execute(
                    script_content=performance_test.k6_script,
                    output_format="summary"
                )
            )
            logger.info(f"[异步执行] k6执行完成，结束时间: {datetime.utcnow()}")
            logger.info(f"[异步执行] k6执行结果 - 状态: {result.get('status')}, 退出码: {result.get('exit_code')}")
            
            if result.get("stderr"):
                stderr_preview = result.get("stderr")[:500]
                logger.warning(f"[异步执行] k6 stderr (前500字符): {stderr_preview}")
            if result.get("stdout"):
                stdout_preview = result.get("stdout")[-500:] if len(result.get("stdout")) > 500 else result.get("stdout")
                logger.debug(f"[异步执行] k6 stdout (最后500字符): {stdout_preview}")
            if result.get("error"):
                logger.error(f"[异步执行] k6返回错误: {result.get('error')}")
                
        except Exception as e:
            error_msg = f"执行k6测试失败: {str(e)}"
            logger.error(f"[异步执行] 执行k6测试时抛出异常: {e}", exc_info=True)
            performance_test.status = "failed"
            performance_test.end_time = datetime.utcnow()
            performance_test.results = {"error": error_msg, "exception": str(e)}
            # 计算执行时长
            if performance_test.start_time and performance_test.end_time:
                duration = (performance_test.end_time - performance_test.start_time).total_seconds()
                performance_test.duration = duration
            db.commit()
            logger.error(f"[异步执行] 测试状态已更新为failed，错误信息已保存")
            return
        
        # 更新测试结果
        result_status = result.get("status", "completed")
        logger.info(f"[异步执行] 准备更新测试结果，状态: {result_status}")
        
        # 统一状态：将 "success" 映射为 "completed"（前端只识别 completed）
        if result_status == "success":
            result_status = "completed"
            logger.info(f"[异步执行] 状态从 'success' 映射为 'completed'")
        
        performance_test.status = result_status
        performance_test.end_time = datetime.utcnow()  # 使用模型中的字段名 end_time
        
        # 构建results对象，保留完整的execution_result信息，以便前端访问
        results_data = {
            "summary": result.get("summary", {}),
            "metrics": result.get("metrics", {}),
            # 保留execution_result信息，供前端使用
            "execution_result": {
                "status": result.get("status", "completed"),
                "exit_code": result.get("exit_code", 0),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "script_path": result.get("script_path", ""),
                "executed_at": result.get("executed_at", ""),
            }
        }
        
        # 如果有错误信息，也包含在results和execution_result中
        if result.get("error"):
            error_msg = result.get("error")
            logger.warning(f"[异步执行] k6返回错误信息: {error_msg}")
            results_data["error"] = error_msg
            results_data["execution_result"]["error"] = error_msg
            if result.get("status") == "failed":
                performance_test.status = "failed"
        
        performance_test.results = results_data
        
        # 计算执行时长
        if performance_test.start_time and performance_test.end_time:
            duration = (performance_test.end_time - performance_test.start_time).total_seconds()
            performance_test.duration = duration
            logger.info(f"[异步执行] 测试执行时长: {duration:.2f} 秒")
        
        # 记录结果数据大小
        results_size = len(str(performance_test.results)) if performance_test.results else 0
        logger.info(f"[异步执行] 结果数据大小: {results_size} 字符")
        logger.info(f"[异步执行] results类型: {type(performance_test.results)}")
        if performance_test.results:
            logger.info(f"[异步执行] results keys: {list(performance_test.results.keys()) if isinstance(performance_test.results, dict) else 'Not a dict'}")
            if isinstance(performance_test.results, dict) and "metrics" in performance_test.results:
                metrics = performance_test.results.get("metrics", {})
                if metrics:
                    logger.info(f"[异步执行] metrics keys: {list(metrics.keys()) if isinstance(metrics, dict) else 'Not a dict'}")
                    logger.info(f"[异步执行] 指标数量: {len(metrics)}")
                    metric_names = list(metrics.keys())[:5] if isinstance(metrics, dict) else []
                    if metric_names:
                        logger.info(f"[异步执行] 指标示例: {', '.join(metric_names)}")
        
        flag_modified(performance_test, "results")
        db.commit()
        logger.info(f"[异步执行] 数据库提交成功")
        
        logger.info(f"[异步执行] 性能测试执行完成: {performance_test_id}")
        logger.info(f"[异步执行] 最终状态: {performance_test.status}")
        logger.info(f"[异步执行] 完成时间: {performance_test.end_time}")
        logger.info(f"[异步执行] 执行时长: {performance_test.duration:.2f} 秒" if performance_test.duration else "[异步执行] 执行时长: 未计算")
        
        # 如果测试成功完成，自动触发分析（异步，不阻塞）
        if performance_test.status in ["completed", "success"]:
            logger.info(f"[异步执行] 测试 {performance_test_id} 执行成功，启动自动分析")
            try:
                # 使用 asyncio.create_task 异步执行分析，不阻塞当前流程
                # 注意：这会在当前事件循环中创建一个后台任务
                import asyncio
                # 由于 execute_performance_test_async 是异步函数，我们可以在其中创建任务
                task = asyncio.create_task(_auto_analyze_performance_test(performance_test_id, db=None))
                logger.info(f"[异步执行] 自动分析任务已创建: {performance_test_id}")
            except RuntimeError as e:
                # 如果没有运行的事件循环，尝试使用 ensure_future
                logger.warning(f"[异步执行] 无法创建任务（可能没有事件循环），尝试其他方式: {e}")
                try:
                    import asyncio
                    asyncio.ensure_future(_auto_analyze_performance_test(performance_test_id, db=None))
                    logger.info(f"[异步执行] 使用 ensure_future 创建自动分析任务: {performance_test_id}")
                except Exception as e2:
                    logger.error(f"[异步执行] 创建自动分析任务失败: {performance_test_id}, 错误: {e2}", exc_info=True)
            except Exception as e:
                # 创建分析任务失败不应该影响测试执行结果
                logger.error(f"[异步执行] 创建自动分析任务失败: {performance_test_id}, 错误: {e}", exc_info=True)
        
        logger.info(f"[异步执行] ===== 异步执行流程结束 =====")
        
    except Exception as e:
        logger.error(f"[异步执行] ===== 执行性能测试异常: {performance_test_id}, 错误: {e} =====", exc_info=True)
        try:
            performance_test = db.query(PerformanceTest).filter(
                PerformanceTest.id == performance_test_id
            ).first()
            if performance_test:
                performance_test.status = "failed"
                performance_test.end_time = datetime.utcnow()
                performance_test.results = {"error": str(e), "exception_type": type(e).__name__}
                # 计算执行时长
                if performance_test.start_time and performance_test.end_time:
                    duration = (performance_test.end_time - performance_test.start_time).total_seconds()
                    performance_test.duration = duration
                db.commit()
                logger.error(f"[异步执行] 异常处理：测试状态已更新为failed")
                logger.error(f"[异步执行] 测试状态已更新为failed: {performance_test_id}, 错误: {str(e)}")
        except Exception as commit_error:
            logger.error(f"[异步执行] 更新测试状态失败: {commit_error}", exc_info=True)

    finally:
        # 确保关闭独立的数据库session
        if db is not None:
            try:
                db.close()
                logger.info(f"[异步执行] 数据库会话已关闭: {performance_test_id}")
            except Exception as e:
                logger.error(f"[异步执行] 关闭数据库会话失败: {e}", exc_info=True)


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
    request: Optional[PerformanceTestExecuteRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """执行性能测试"""
    logger.info(f"[执行接口] ===== 收到执行请求 =====")
    logger.info(f"[执行接口] 路径参数 performance_test_id: {performance_test_id}")
    logger.info(f"[执行接口] 请求体 request: {request}")
    logger.info(f"[执行接口] 请求体类型: {type(request)}")
    if request:
        logger.info(f"[执行接口] 请求体字典: {request.dict()}")
        logger.info(f"[执行接口] request.performance_test_id: {getattr(request, 'performance_test_id', 'N/A')}")
        logger.info(f"[执行接口] request.additional_args: {getattr(request, 'additional_args', 'N/A')}")
    else:
        logger.info(f"[执行接口] 请求体为None或未提供（这是正常的，测试ID在路径中）")
    
    logger.info(f"[执行接口] k6_executor 状态: {'可用' if k6_executor else '不可用'}")
    if k6_executor:
        logger.info(f"[执行接口] k6_executor.k6_binary_path: {k6_executor.k6_binary_path}")
    
    try:
        performance_test = db.query(PerformanceTest).filter(
            PerformanceTest.id == performance_test_id
        ).first()
        
        if not performance_test:
            logger.error(f"[执行接口] 性能测试不存在: {performance_test_id}")
            raise HTTPException(status_code=404, detail="性能测试不存在")
        
        logger.info(f"[执行接口] 找到测试记录: ID={performance_test.id}, 名称={performance_test.name}")
        logger.info(f"[执行接口] 当前状态: {performance_test.status}")
        logger.info(f"[执行接口] 脚本是否存在: {bool(performance_test.k6_script)}")
        logger.info(f"[执行接口] 脚本长度: {len(performance_test.k6_script) if performance_test.k6_script else 0} 字符")
        if performance_test.k6_script:
            script_preview = performance_test.k6_script[:200] + "..." if len(performance_test.k6_script) > 200 else performance_test.k6_script
            logger.info(f"[执行接口] 脚本预览（前200字符）: {script_preview}")
        
        # 检查测试状态
        if performance_test.status == "running":
            logger.warning(f"[执行接口] 测试正在运行中: {performance_test_id}")
            raise HTTPException(status_code=400, detail="测试正在运行中")
        
        # 验证脚本是否存在
        if not performance_test.k6_script or not performance_test.k6_script.strip():
            error_msg = f"性能测试脚本为空: {performance_test_id}"
            logger.error(f"[执行接口] {error_msg}")
            raise HTTPException(
                status_code=400,
                detail="测试脚本为空，无法执行。请先生成或更新测试脚本。"
            )
        
        # 检查k6执行器是否可用
        if k6_executor is None:
            error_msg = "k6执行器未初始化，请检查k6是否已安装"
            logger.error(f"[执行接口] {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        
        logger.info(f"[执行接口] k6执行器可用，路径: {k6_executor.k6_binary_path}")
        
        # 在后台任务中执行测试
        logger.info(f"[执行接口] 添加后台任务: performance_test_id={performance_test_id}")
        background_tasks.add_task(execute_performance_test_async, performance_test_id)
        
        # 立即返回，不等待测试完成
        performance_test.status = "pending"
        performance_test.start_time = datetime.utcnow()  # 使用模型中的字段名 start_time
        db.commit()
        logger.info(f"[执行接口] 测试状态已更新为pending: {performance_test_id}")
        logger.info(f"[执行接口] 开始时间: {performance_test.start_time}")
        
        result = PerformanceTestOut.model_validate(performance_test)
        logger.info(f"[执行接口] 返回结果: ID={result.id}, 状态={result.status}")
        logger.info(f"[执行接口] ===== 执行请求处理完成 =====")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[执行接口] 执行请求处理失败: performance_test_id={performance_test_id}, 错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"执行请求处理失败: {str(e)}")


@router.post("/{performance_test_id}/analyze", response_model=dict)
async def analyze_performance_test(
    performance_test_id: int,
    request: Optional[PerformanceTestAnalysisRequest] = None,
    db: Session = Depends(get_db)
):
    """分析性能测试结果"""
    performance_test = db.query(PerformanceTest).filter(
        PerformanceTest.id == performance_test_id
    ).first()
    
    if not performance_test:
        raise HTTPException(status_code=404, detail="性能测试不存在")
    
    if not performance_test.results:
        raise HTTPException(status_code=400, detail="测试结果不存在，请先执行测试")
    
    try:
        # 获取项目信息
        project = db.query(Project).filter(Project.id == performance_test.project_id).first()
        project_name = project.name if project else ""
        project_description = project.description if project else ""
        
        # 从 results 中提取 metrics 和 stdout
        results = performance_test.results if isinstance(performance_test.results, dict) else {}
        metrics = results.get("metrics", {})
        execution_result = results.get("execution_result", {})
        stdout = execution_result.get("stdout", "") if isinstance(execution_result, dict) else ""
        
        # 获取自定义提示词（如果提供）
        custom_prompt = request.prompt if request and request.prompt else None
        
        # 调用分析服务
        analysis_result = await k6_analysis_service.analyze_performance_results(
            performance_test_id=performance_test_id,
            test_name=performance_test.name or "",
            test_description=performance_test.description or "",
            test_requirement=performance_test.ai_prompt or "",
            project_name=project_name,
            project_description=project_description,
            k6_results=results,
            k6_metrics=metrics,
            k6_stdout=stdout
        )
        
        # 检查分析结果状态
        if analysis_result.get("status") == "error":
            error_msg = analysis_result.get("error", "分析失败")
            logger.error(f"[分析接口] 分析服务返回错误: {error_msg}")
            raise HTTPException(status_code=500, detail=f"分析失败: {error_msg}")
        
        # 获取分析数据
        analysis_data = analysis_result.get("analysis", {})
        
        # 保存分析结果
        performance_test.analysis = analysis_data
        performance_test.analysis_generated_at = datetime.utcnow()
        flag_modified(performance_test, "analysis")
        db.commit()
        
        logger.info(f"[分析接口] 分析完成，已保存到数据库: performance_test_id={performance_test_id}")
        
        # 返回分析结果（包含 markdown）
        return analysis_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析性能测试结果失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
