"""统计信息API"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.project import Project, Requirement, TestCase, TestRun
from app.models.performance_test import PerformanceTest

router = APIRouter()


@router.get("/dashboard")
def get_dashboard_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取仪表板统计信息"""
    try:
        # 基础统计
        total_projects = db.query(func.count(Project.id)).scalar() or 0
        total_requirements = db.query(func.count(Requirement.id)).scalar() or 0
        total_test_cases = db.query(func.count(TestCase.id)).scalar() or 0
        total_test_runs = db.query(func.count(TestRun.id)).scalar() or 0
        
        # 测试运行统计
        completed_test_runs = db.query(TestRun).filter(
            TestRun.status.in_(["completed", "failed"])
        ).all()
        
        total_passed_tests = 0
        total_failed_tests = 0
        total_skipped_tests = 0
        total_error_tests = 0
        
        for test_run in completed_test_runs:
            if test_run.results and isinstance(test_run.results, dict):
                total_passed_tests += test_run.results.get("passed_cases", 0)
                total_failed_tests += test_run.results.get("failed_cases", 0)
                total_skipped_tests += test_run.results.get("skipped_cases", 0)
                total_error_tests += test_run.results.get("error_cases", 0)
        
        # 计算成功率
        total_executed_tests = total_passed_tests + total_failed_tests + total_error_tests
        success_rate = 0
        if total_executed_tests > 0:
            success_rate = round((total_passed_tests / total_executed_tests) * 100, 1)
        
        # 最近7天的测试运行统计
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_test_runs_query = db.query(TestRun)
        if hasattr(TestRun, 'created_at'):
            recent_test_runs = recent_test_runs_query.filter(
                TestRun.created_at >= seven_days_ago
            ).all()
        else:
            # 如果没有created_at字段，获取所有测试运行
            recent_test_runs = recent_test_runs_query.all()
        
        recent_runs_count = len(recent_test_runs)
        recent_passed = sum(
            tr.results.get("passed_cases", 0) 
            for tr in recent_test_runs 
            if tr.results and isinstance(tr.results, dict)
        )
        recent_failed = sum(
            tr.results.get("failed_cases", 0) 
            for tr in recent_test_runs 
            if tr.results and isinstance(tr.results, dict)
        )
        
        # 测试运行状态分布
        running_count = db.query(func.count(TestRun.id)).filter(
            TestRun.status == "running"
        ).scalar() or 0
        pending_count = db.query(func.count(TestRun.id)).filter(
            TestRun.status == "pending"
        ).scalar() or 0
        completed_count = db.query(func.count(TestRun.id)).filter(
            TestRun.status == "completed"
        ).scalar() or 0
        failed_count = db.query(func.count(TestRun.id)).filter(
            TestRun.status == "failed"
        ).scalar() or 0
        
        # 测试用例类型分布
        functional_count = db.query(func.count(TestCase.id)).filter(
            TestCase.test_type == "functional"
        ).scalar() or 0
        api_count = db.query(func.count(TestCase.id)).filter(
            TestCase.test_type == "api"
        ).scalar() or 0
        ui_count = db.query(func.count(TestCase.id)).filter(
            TestCase.test_type == "ui"
        ).scalar() or 0
        
        # 定时执行的测试运行数量
        scheduled_count = 0
        scheduled_test_runs = db.query(TestRun).all()
        for tr in scheduled_test_runs:
            if tr.results and isinstance(tr.results, dict) and tr.results.get("scheduled"):
                scheduled_count += 1
        
        # 性能测试统计
        total_performance_tests = db.query(func.count(PerformanceTest.id)).scalar() or 0
        
        # 性能测试状态分布
        performance_pending = db.query(func.count(PerformanceTest.id)).filter(
            PerformanceTest.status == "pending"
        ).scalar() or 0
        performance_running = db.query(func.count(PerformanceTest.id)).filter(
            PerformanceTest.status == "running"
        ).scalar() or 0
        performance_completed = db.query(func.count(PerformanceTest.id)).filter(
            PerformanceTest.status == "completed"
        ).scalar() or 0
        performance_failed = db.query(func.count(PerformanceTest.id)).filter(
            PerformanceTest.status == "failed"
        ).scalar() or 0
        
        # 已完成性能测试中有分析结果的数量
        performance_with_analysis = db.query(func.count(PerformanceTest.id)).filter(
            and_(
                PerformanceTest.status.in_(["completed", "failed"]),
                PerformanceTest.analysis.isnot(None)
            )
        ).scalar() or 0
        
        # 最近7天的性能测试统计
        recent_performance_tests = db.query(PerformanceTest).filter(
            PerformanceTest.created_at >= seven_days_ago
        ).all() if hasattr(PerformanceTest, 'created_at') else []
        recent_performance_count = len(recent_performance_tests)
        
        return {
            "total_projects": total_projects,
            "total_requirements": total_requirements,
            "total_test_cases": total_test_cases,
            "total_test_runs": total_test_runs,
            "total_passed_tests": total_passed_tests,
            "total_failed_tests": total_failed_tests,
            "total_skipped_tests": total_skipped_tests,
            "total_error_tests": total_error_tests,
            "success_rate": success_rate,
            "recent_runs_count": recent_runs_count,
            "recent_passed": recent_passed,
            "recent_failed": recent_failed,
            "test_run_status": {
                "running": running_count,
                "pending": pending_count,
                "completed": completed_count,
                "failed": failed_count,
            },
            "test_case_types": {
                "functional": functional_count,
                "api": api_count,
                "ui": ui_count,
            },
            "scheduled_test_runs": scheduled_count,
            "performance_tests": {
                "total": total_performance_tests,
                "status": {
                    "pending": performance_pending,
                    "running": performance_running,
                    "completed": performance_completed,
                    "failed": performance_failed,
                },
                "with_analysis": performance_with_analysis,
                "recent_count": recent_performance_count,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/test-runs/recent")
def get_recent_test_runs(limit: int = 10, db: Session = Depends(get_db)):
    """获取最近的测试运行"""
    test_runs = db.query(TestRun).order_by(
        TestRun.created_at.desc()
    ).limit(limit).all()
    
    result = []
    for tr in test_runs:
        result.append({
            "id": tr.id,
            "name": tr.name,
            "status": tr.status,
            "created_at": tr.created_at.isoformat() if tr.created_at else None,
            "total_cases": tr.results.get("total_cases", 0) if tr.results and isinstance(tr.results, dict) else 0,
            "passed_cases": tr.results.get("passed_cases", 0) if tr.results and isinstance(tr.results, dict) else 0,
            "failed_cases": tr.results.get("failed_cases", 0) if tr.results and isinstance(tr.results, dict) else 0,
        })
    
    return result

