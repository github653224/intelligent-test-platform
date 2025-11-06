from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, BackgroundTasks
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from datetime import datetime
from app.db.session import get_db
from app.models.project import TestRun, TestCase, TestSuite
from app.schemas.test_run import TestRunCreate, TestRunUpdate, TestRunOut, TestRunDetail
from app.schemas.test_verification import ManualVerificationRequest, BatchVerificationRequest, VerificationResult
from app.services.test_execution_service import TestExecutionService
from app.services.test_report_generator import TestReportGenerator
from app.services.test_scheduler import test_scheduler

router = APIRouter()


@router.options("/")
@router.options("/{test_run_id}")
async def options_handler(response: Response):
    """处理 OPTIONS 预检请求"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    return Response(status_code=200)


@router.get("/", response_model=List[TestRunOut])
def list_test_runs(
    project_id: Optional[int] = None,
    test_suite_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取测试运行列表"""
    query = db.query(TestRun)
    
    if project_id is not None:
        query = query.filter(TestRun.project_id == project_id)
    if test_suite_id is not None:
        query = query.filter(TestRun.test_suite_id == test_suite_id)
    if status:
        query = query.filter(TestRun.status == status)
    
    test_runs = query.order_by(TestRun.id.desc()).all()
    
    # 添加统计信息
    result = []
    for test_run in test_runs:
        run_dict = {
            "id": test_run.id,
            "project_id": test_run.project_id,
            "test_suite_id": test_run.test_suite_id,
            "name": test_run.name,
            "status": test_run.status,
            "start_time": test_run.start_time,
            "end_time": test_run.end_time,
            "results": test_run.results or {},
            "created_at": test_run.created_at,
            "updated_at": test_run.updated_at
        }
        
        # 添加统计信息
        if test_run.results and isinstance(test_run.results, dict):
            run_dict["total_cases"] = test_run.results.get("total_cases", 0)
            run_dict["passed_cases"] = test_run.results.get("passed_cases", 0)
            run_dict["failed_cases"] = test_run.results.get("failed_cases", 0)
            run_dict["skipped_cases"] = test_run.results.get("skipped_cases", 0)
            run_dict["duration"] = test_run.results.get("duration", 0)
        else:
            run_dict["total_cases"] = 0
            run_dict["passed_cases"] = 0
            run_dict["failed_cases"] = 0
            run_dict["skipped_cases"] = 0
            run_dict["duration"] = 0
        
        result.append(TestRunOut(**run_dict))
    
    return result


@router.get("/{test_run_id}", response_model=TestRunDetail)
def get_test_run(test_run_id: int, db: Session = Depends(get_db)):
    """获取测试运行详情"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # 构建返回数据
    run_dict = {
        "id": test_run.id,
        "project_id": test_run.project_id,
        "test_suite_id": test_run.test_suite_id,
        "name": test_run.name,
        "status": test_run.status,
        "start_time": test_run.start_time,
        "end_time": test_run.end_time,
        "results": test_run.results or {},
        "created_at": test_run.created_at,
        "updated_at": test_run.updated_at,
        "test_results": []
    }
    
    # 添加统计信息
    if test_run.results and isinstance(test_run.results, dict):
        run_dict["total_cases"] = test_run.results.get("total_cases", 0)
        run_dict["passed_cases"] = test_run.results.get("passed_cases", 0)
        run_dict["failed_cases"] = test_run.results.get("failed_cases", 0)
        run_dict["skipped_cases"] = test_run.results.get("skipped_cases", 0)
        run_dict["duration"] = test_run.results.get("duration", 0)
        
        # 添加测试结果详情
        test_results = test_run.results.get("test_results", [])
        if test_results:
            from app.schemas.test_run import TestResult
            run_dict["test_results"] = [TestResult(**r) for r in test_results]
    else:
        run_dict["total_cases"] = 0
        run_dict["passed_cases"] = 0
        run_dict["failed_cases"] = 0
        run_dict["skipped_cases"] = 0
        run_dict["duration"] = 0
    
    return TestRunDetail(**run_dict)


@router.post("/", response_model=TestRunOut)
def create_test_run(
    payload: TestRunCreate,
    db: Session = Depends(get_db)
):
    """创建测试运行（不自动执行）"""
    # 验证项目是否存在
    from app.models.project import Project
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 验证测试套件（如果提供）
    if payload.test_suite_id:
        test_suite = db.query(TestSuite).filter(TestSuite.id == payload.test_suite_id).first()
        if not test_suite:
            raise HTTPException(status_code=404, detail="Test suite not found")
        # 如果未提供test_case_ids，使用测试套件中的测试用例
        if not payload.test_case_ids and test_suite.test_cases:
            test_case_ids = test_suite.test_cases
        else:
            test_case_ids = payload.test_case_ids or []
    else:
        # 如果没有测试套件，必须提供test_case_ids
        if not payload.test_case_ids:
            raise HTTPException(
                status_code=400,
                detail="Either test_suite_id or test_case_ids must be provided"
            )
        test_case_ids = payload.test_case_ids
    
    # 验证测试用例是否存在
    test_cases = db.query(TestCase).filter(TestCase.id.in_(test_case_ids)).all()
    if len(test_cases) != len(test_case_ids):
        raise HTTPException(status_code=404, detail="Some test cases not found")
    
    # 创建测试运行，保存测试用例ID和执行配置
    test_run = TestRun(
        project_id=payload.project_id,
        test_suite_id=payload.test_suite_id,
        name=payload.name,
        status="pending",
        results={
            "test_case_ids": test_case_ids,  # 保存创建时选择的测试用例ID
            "execution_config": payload.execution_config or {}  # 保存执行配置
        }
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)
    
    # 返回创建的测试运行
    run_dict = {
        "id": test_run.id,
        "project_id": test_run.project_id,
        "test_suite_id": test_run.test_suite_id,
        "name": test_run.name,
        "status": test_run.status,
        "start_time": test_run.start_time,
        "end_time": test_run.end_time,
        "results": test_run.results or {},
        "created_at": test_run.created_at,
        "updated_at": test_run.updated_at,
        "total_cases": len(test_case_ids),
        "passed_cases": 0,
        "failed_cases": 0,
        "skipped_cases": 0,
        "duration": 0
    }
    
    return TestRunOut(**run_dict)


@router.post("/{test_run_id}/execute")
async def execute_test_run(
    test_run_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """手动触发测试运行执行"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    if test_run.status == "running":
        raise HTTPException(status_code=400, detail="Test run is already running")
    
    # 获取测试用例ID和执行配置
    test_case_ids = []
    execution_config = {}
    
    # 优先从 results 中获取保存的 test_case_ids
    if test_run.results and isinstance(test_run.results, dict):
        test_case_ids = test_run.results.get("test_case_ids", [])
        execution_config = test_run.results.get("execution_config", {})
    
    # 如果没有保存的 test_case_ids，尝试从 test_suite 获取
    if not test_case_ids and test_run.test_suite_id:
        test_suite = db.query(TestSuite).filter(TestSuite.id == test_run.test_suite_id).first()
        if test_suite and test_suite.test_cases:
            test_case_ids = test_suite.test_cases
    
    # 如果还是没有，尝试从项目获取所有测试用例（兼容旧数据）
    if not test_case_ids:
        test_cases = db.query(TestCase).filter(TestCase.project_id == test_run.project_id).all()
        test_case_ids = [tc.id for tc in test_cases]
    
    if not test_case_ids:
        raise HTTPException(status_code=400, detail="No test cases to execute")
    
    # 在后台执行测试
    execution_service = TestExecutionService(db)
    background_tasks.add_task(
        execution_service.execute_test_run_async,
        test_run.id,
        test_case_ids,
        execution_config
    )
    
    return {"status": "success", "message": "Test run execution started"}


@router.post("/{test_run_id}/cancel")
def cancel_test_run(test_run_id: int, db: Session = Depends(get_db)):
    """取消正在运行的测试"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    if test_run.status != "running":
        raise HTTPException(status_code=400, detail="Test run is not running")
    
    execution_service = TestExecutionService(db)
    cancelled = execution_service.cancel_test_run(test_run_id)
    
    if cancelled:
        return {"status": "success", "message": "Test run cancelled"}
    else:
        return {"status": "error", "message": "Failed to cancel test run"}


@router.put("/{test_run_id}", response_model=TestRunOut)
def update_test_run(test_run_id: int, payload: TestRunUpdate, db: Session = Depends(get_db)):
    """更新测试运行"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # 更新字段
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(test_run, field, value)
    
    db.add(test_run)
    db.commit()
    db.refresh(test_run)
    
    # 构建返回数据
    run_dict = {
        "id": test_run.id,
        "project_id": test_run.project_id,
        "test_suite_id": test_run.test_suite_id,
        "name": test_run.name,
        "status": test_run.status,
        "start_time": test_run.start_time,
        "end_time": test_run.end_time,
        "results": test_run.results or {},
        "created_at": test_run.created_at,
        "updated_at": test_run.updated_at
    }
    
    # 添加统计信息
    if test_run.results and isinstance(test_run.results, dict):
        run_dict["total_cases"] = test_run.results.get("total_cases", 0)
        run_dict["passed_cases"] = test_run.results.get("passed_cases", 0)
        run_dict["failed_cases"] = test_run.results.get("failed_cases", 0)
        run_dict["skipped_cases"] = test_run.results.get("skipped_cases", 0)
        run_dict["duration"] = test_run.results.get("duration", 0)
    else:
        run_dict["total_cases"] = 0
        run_dict["passed_cases"] = 0
        run_dict["failed_cases"] = 0
        run_dict["skipped_cases"] = 0
        run_dict["duration"] = 0
    
    return TestRunOut(**run_dict)


@router.delete("/{test_run_id}")
def delete_test_run(test_run_id: int, db: Session = Depends(get_db)):
    """删除测试运行"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # 如果正在运行，先取消
    if test_run.status == "running":
        execution_service = TestExecutionService(db)
        execution_service.cancel_test_run(test_run_id)
    
    db.delete(test_run)
    db.commit()
    return {"status": "success"}


@router.get("/{test_run_id}/report/summary")
def get_test_run_summary(test_run_id: int, db: Session = Depends(get_db)):
    """获取测试运行摘要报告"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    summary = TestReportGenerator.generate_summary_report(test_run)
    return summary


@router.get("/{test_run_id}/report/detailed")
def get_test_run_detailed_report(test_run_id: int, db: Session = Depends(get_db)):
    """获取测试运行详细报告"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # 刷新对象以确保获取最新数据
    db.refresh(test_run)
    
    report = TestReportGenerator.generate_detailed_report(test_run)
    return report


@router.get("/{test_run_id}/report/html", response_class=HTMLResponse)
def get_test_run_html_report(test_run_id: int, db: Session = Depends(get_db)):
    """获取测试运行HTML报告"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    html = TestReportGenerator.generate_html_report(test_run)
    return HTMLResponse(
        content=html,
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "X-Content-Type-Options": "nosniff"
        }
    )


@router.get("/{test_run_id}/report/json")
def get_test_run_json_report(test_run_id: int, db: Session = Depends(get_db)):
    """获取测试运行JSON报告"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    json_report = TestReportGenerator.generate_json_report(test_run)
    return Response(content=json_report, media_type="application/json")


@router.get("/{test_run_id}/report/csv")
def get_test_run_csv_report(test_run_id: int, db: Session = Depends(get_db)):
    """获取测试运行CSV报告"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    csv_report = TestReportGenerator.generate_csv_report(test_run)
    return Response(
        content=csv_report,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=test_run_{test_run_id}_report.csv"}
    )


@router.post("/{test_run_id}/verify", response_model=VerificationResult)
def manually_verify_test_result(
    test_run_id: int,
    payload: ManualVerificationRequest,
    db: Session = Depends(get_db)
):
    """手动验证测试结果"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    if test_run.results is None:
        test_run.results = {}
    
    # 创建新的results字典，确保SQLAlchemy能检测到变化
    results = dict(test_run.results) if test_run.results else {}
    test_results = list(results.get("test_results", []))  # 创建新列表
    
    # 查找对应的测试结果
    test_result_index = None
    for idx, tr in enumerate(test_results):
        if tr.get("test_case_id") == payload.test_case_id:
            test_result_index = idx
            break
    
    if test_result_index is None:
        raise HTTPException(status_code=404, detail="Test result not found in this test run")
    
    # 更新测试结果 - 创建新字典来确保JSON字段更新
    test_result = dict(test_results[test_result_index])  # 创建副本
    test_result["status"] = payload.status
    test_result["manually_verified"] = True
    test_result["verified_by"] = payload.verified_by or "Unknown"
    test_result["verified_at"] = datetime.now().isoformat()
    test_result["verification_notes"] = payload.verification_notes
    test_result["actual_result"] = payload.actual_result
    
    if payload.status == "failed":
        test_result["failure_reason"] = payload.failure_reason
        test_result["bug_id"] = payload.bug_id
    else:
        # 如果状态不是失败，清除失败相关字段
        test_result.pop("failure_reason", None)
        test_result.pop("bug_id", None)
    
    # 更新回列表（创建新列表）
    test_results[test_result_index] = test_result
    results["test_results"] = test_results
    
    if payload.step_results:
        # 更新步骤级别的结果
        for step_result in payload.step_results:
            step_number = step_result.get("step_number")
            if step_number:
                for step in test_result.get("steps", []):
                    if step.get("step_number") == step_number:
                        step.update({
                            "status": step_result.get("status", step.get("status")),
                            "result": step_result.get("result", step.get("result")),
                            "notes": step_result.get("notes")
                        })
                        break
    
    # 更新统计信息
    passed_count = sum(1 for tr in test_results if tr.get("status") == "passed")
    failed_count = sum(1 for tr in test_results if tr.get("status") == "failed")
    skipped_count = sum(1 for tr in test_results if tr.get("status") in ["skipped", "blocked"])
    error_count = sum(1 for tr in test_results if tr.get("status") == "error")
    
    results["passed_cases"] = passed_count
    results["failed_cases"] = failed_count
    results["skipped_cases"] = skipped_count
    results["error_cases"] = error_count
    
    # 更新测试运行状态
    if failed_count > 0 or error_count > 0:
        test_run.status = "failed"
    elif all(tr.get("status") in ["passed", "skipped"] for tr in test_results):
        test_run.status = "completed"
    
    # 确保 results 字典被正确更新
    # 对于JSON字段，需要显式标记为已修改
    test_run.results = results
    flag_modified(test_run, "results")  # 标记JSON字段已修改
    db.add(test_run)  # 显式标记为已修改
    db.commit()
    db.refresh(test_run)  # 刷新对象以获取最新数据
    
    return VerificationResult(
        success=True,
        message="测试结果验证成功",
        updated_test_result=test_result
    )


@router.post("/{test_run_id}/verify/batch", response_model=List[VerificationResult])
def batch_verify_test_results(
    test_run_id: int,
    payload: BatchVerificationRequest,
    db: Session = Depends(get_db)
):
    """批量验证测试结果"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    if test_run.results is None:
        test_run.results = {}
    
    # 创建新的results字典，确保SQLAlchemy能检测到变化
    results = dict(test_run.results) if test_run.results else {}
    test_results = list(results.get("test_results", []))  # 创建新列表
    verification_results = []
    
    for verification in payload.verifications:
        try:
            # 查找对应的测试结果
            test_result_index = None
            for idx, tr in enumerate(test_results):
                if tr.get("test_case_id") == verification.test_case_id:
                    test_result_index = idx
                    break
            
            if test_result_index is None:
                verification_results.append(
                    VerificationResult(
                        success=False,
                        message=f"测试用例 {verification.test_case_id} 未找到",
                        updated_test_result=None
                    )
                )
                continue
            
            # 更新测试结果（复用手动验证的逻辑）- 创建副本确保JSON字段更新
            test_result = dict(test_results[test_result_index])  # 创建副本
            test_result["status"] = verification.status
            test_result["manually_verified"] = True
            test_result["verified_by"] = verification.verified_by or "Unknown"
            test_result["verified_at"] = datetime.now().isoformat()
            test_result["verification_notes"] = verification.verification_notes
            test_result["actual_result"] = verification.actual_result
            
            if verification.status == "failed":
                test_result["failure_reason"] = verification.failure_reason
                test_result["bug_id"] = verification.bug_id
            else:
                # 如果状态不是失败，清除失败相关字段
                test_result.pop("failure_reason", None)
                test_result.pop("bug_id", None)
            
            # 更新回列表（创建新列表）
            test_results[test_result_index] = test_result
            
            if verification.step_results:
                for step_result in verification.step_results:
                    step_number = step_result.get("step_number")
                    if step_number:
                        for step in test_result.get("steps", []):
                            if step.get("step_number") == step_number:
                                step.update({
                                    "status": step_result.get("status", step.get("status")),
                                    "result": step_result.get("result", step.get("result")),
                                    "notes": step_result.get("notes")
                                })
                                break
            
            verification_results.append(
                VerificationResult(
                    success=True,
                    message="验证成功",
                    updated_test_result=test_result
                )
            )
        except Exception as e:
            verification_results.append(
                VerificationResult(
                    success=False,
                    message=f"验证失败: {str(e)}",
                    updated_test_result=None
                )
            )
    
    # 更新统计信息
    passed_count = sum(1 for tr in test_results if tr.get("status") == "passed")
    failed_count = sum(1 for tr in test_results if tr.get("status") == "failed")
    skipped_count = sum(1 for tr in test_results if tr.get("status") in ["skipped", "blocked"])
    error_count = sum(1 for tr in test_results if tr.get("status") == "error")
    
    # 更新统计信息
    results["passed_cases"] = passed_count
    results["failed_cases"] = failed_count
    results["skipped_cases"] = skipped_count
    results["error_cases"] = error_count
    results["test_results"] = test_results  # 确保更新后的列表被保存
    
    # 更新测试运行状态
    if failed_count > 0 or error_count > 0:
        test_run.status = "failed"
    elif all(tr.get("status") in ["passed", "skipped"] for tr in test_results):
        test_run.status = "completed"
    
    # 确保 results 字典被正确更新 - 创建新字典对象
    test_run.results = results
    flag_modified(test_run, "results")  # 标记JSON字段已修改
    db.add(test_run)
    db.commit()
    db.refresh(test_run)
    
    return verification_results


@router.post("/{test_run_id}/schedule")
def set_test_run_schedule(
    test_run_id: int,
    schedule_config: dict,
    db: Session = Depends(get_db)
):
    """设置测试运行的定时执行计划"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # 验证调度配置
    schedule_type = schedule_config.get("type")
    if schedule_type not in ["cron", "interval", "once"]:
        raise HTTPException(status_code=400, detail="Invalid schedule type. Must be 'cron', 'interval', or 'once'")
    
    # 保存调度配置到 results
    if test_run.results is None:
        test_run.results = {}
    
    results = dict(test_run.results)
    results["schedule_config"] = schedule_config
    results["scheduled"] = True
    test_run.results = results
    flag_modified(test_run, "results")
    db.commit()
    
    # 添加到调度器
    try:
        job_id = test_scheduler.add_scheduled_test_run(test_run_id, schedule_config)
        return {
            "status": "success",
            "message": "定时任务已设置",
            "job_id": job_id,
            "schedule_config": schedule_config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置定时任务失败: {str(e)}")


@router.delete("/{test_run_id}/schedule")
def remove_test_run_schedule(
    test_run_id: int,
    db: Session = Depends(get_db)
):
    """移除测试运行的定时执行计划"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # 从调度器移除
    removed = test_scheduler.remove_scheduled_test_run(test_run_id)
    
    # 更新数据库中的调度配置
    if test_run.results and isinstance(test_run.results, dict):
        results = dict(test_run.results)
        results.pop("schedule_config", None)
        results["scheduled"] = False
        test_run.results = results
        flag_modified(test_run, "results")
        db.commit()
    
    if removed:
        return {"status": "success", "message": "定时任务已移除"}
    else:
        return {"status": "warning", "message": "未找到定时任务"}


@router.get("/{test_run_id}/schedule")
def get_test_run_schedule(
    test_run_id: int,
    db: Session = Depends(get_db)
):
    """获取测试运行的定时执行计划"""
    test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # 从数据库获取配置
    schedule_config = None
    if test_run.results and isinstance(test_run.results, dict):
        schedule_config = test_run.results.get("schedule_config")
    
    # 从调度器获取任务信息
    job_info = test_scheduler.get_scheduled_test_run(test_run_id)
    
    return {
        "scheduled": bool(schedule_config),
        "schedule_config": schedule_config,
        "job_info": job_info
    }

