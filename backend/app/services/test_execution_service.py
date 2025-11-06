"""
测试执行服务
管理测试运行的创建、执行、状态更新等
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.project import TestRun, TestCase, TestSuite
from app.services.test_executor import TestExecutorFactory
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class TestExecutionService:
    """测试执行服务"""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.running_tasks: Dict[int, asyncio.Task] = {}  # 存储正在运行的测试任务
    
    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self.db:
            return self.db
        return SessionLocal()
    
    async def execute_test_run(
        self,
        test_run_id: int,
        test_case_ids: List[int],
        execution_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行测试运行"""
        db = self._get_db()
        try:
            test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
            if not test_run:
                raise ValueError(f"测试运行 {test_run_id} 不存在")
            
            # 更新状态为运行中
            test_run.status = "running"
            test_run.start_time = datetime.now().isoformat()
            db.commit()
            
            # 获取测试用例
            test_cases = db.query(TestCase).filter(TestCase.id.in_(test_case_ids)).all()
            
            if not test_cases:
                test_run.status = "failed"
                test_run.end_time = datetime.now().isoformat()
                test_run.results = {
                    "total_cases": 0,
                    "passed_cases": 0,
                    "failed_cases": 0,
                    "skipped_cases": 0,
                    "error_cases": 0,
                    "test_results": [],
                    "error": "没有找到要执行的测试用例"
                }
                db.commit()
                return test_run.results
            
            # 按测试类型分组
            test_cases_by_type: Dict[str, List[TestCase]] = {}
            for test_case in test_cases:
                test_type = test_case.test_type
                if test_type not in test_cases_by_type:
                    test_cases_by_type[test_type] = []
                test_cases_by_type[test_type].append(test_case)
            
            # 执行所有测试用例
            all_results = []
            total_cases = len(test_cases)
            passed_cases = 0
            failed_cases = 0
            skipped_cases = 0
            error_cases = 0
            
            for test_type, cases in test_cases_by_type.items():
                # 创建对应的执行器
                executor = TestExecutorFactory.create_executor(test_type, execution_config)
                
                # 执行每个测试用例
                for test_case in cases:
                    try:
                        # 将SQLAlchemy对象转换为字典
                        # 获取测试步骤
                        test_steps_list = []
                        if hasattr(test_case, 'test_steps') and test_case.test_steps:
                            for step in test_case.test_steps:
                                test_steps_list.append({
                                    "step_number": step.step_number,
                                    "action": step.action,
                                    "expected_result": step.expected_result,
                                    "test_data": step.test_data or {}
                                })
                        
                        test_case_dict = {
                            "id": test_case.id,
                            "title": test_case.title,
                            "description": test_case.description,
                            "test_type": test_case.test_type,
                            "test_data": test_case.test_data or {},
                            "test_steps": test_steps_list,
                            "expected_result": test_case.expected_result
                        }
                        
                        # 如果有python_code，添加到字典中
                        if test_case.test_data and isinstance(test_case.test_data, dict):
                            if "python_code" in test_case.test_data:
                                test_case_dict["python_code"] = test_case.test_data["python_code"]
                        
                        # 执行测试
                        result = await executor.execute(test_case_dict)
                        all_results.append(result)
                        
                        # 统计结果
                        if result["status"] == "passed":
                            passed_cases += 1
                        elif result["status"] == "failed":
                            failed_cases += 1
                        elif result["status"] == "skipped":
                            skipped_cases += 1
                        else:
                            error_cases += 1
                            
                    except Exception as e:
                        logger.error(f"执行测试用例 {test_case.id} 失败: {e}", exc_info=True)
                        error_cases += 1
                        all_results.append({
                            "test_case_id": test_case.id,
                            "test_case_title": test_case.title,
                            "status": "error",
                            "duration": 0,
                            "error_message": str(e),
                            "steps": [],
                            "logs": [f"执行异常: {str(e)}"]
                        })
            
            # 计算总执行时长
            total_duration = sum(r.get("duration", 0) for r in all_results)
            
            # 更新测试运行结果
            test_run.status = "completed" if failed_cases == 0 and error_cases == 0 else "failed"
            test_run.end_time = datetime.now().isoformat()
            test_run.results = {
                "total_cases": total_cases,
                "passed_cases": passed_cases,
                "failed_cases": failed_cases,
                "skipped_cases": skipped_cases,
                "error_cases": error_cases,
                "duration": total_duration,
                "test_results": all_results
            }
            db.commit()
            
            logger.info(
                f"测试运行 {test_run_id} 执行完成: "
                f"总计 {total_cases}, 通过 {passed_cases}, 失败 {failed_cases}, "
                f"跳过 {skipped_cases}, 错误 {error_cases}"
            )
            
            return test_run.results
        finally:
            if not self.db:  # 如果创建了新会话，需要关闭
                db.close()
    
    async def execute_test_run_async(
        self,
        test_run_id: int,
        test_case_ids: List[int],
        execution_config: Optional[Dict[str, Any]] = None
    ):
        """异步执行测试运行（不阻塞）"""
        task = asyncio.create_task(
            self.execute_test_run(test_run_id, test_case_ids, execution_config)
        )
        self.running_tasks[test_run_id] = task
        
        try:
            await task
        finally:
            if test_run_id in self.running_tasks:
                del self.running_tasks[test_run_id]
    
    def cancel_test_run(self, test_run_id: int) -> bool:
        """取消正在运行的测试"""
        if test_run_id in self.running_tasks:
            task = self.running_tasks[test_run_id]
            task.cancel()
            del self.running_tasks[test_run_id]
            
            # 更新数据库状态
            db = self._get_db()
            try:
                test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
                if test_run:
                    test_run.status = "cancelled"
                    test_run.end_time = datetime.now().isoformat()
                    db.commit()
            finally:
                if not self.db:
                    db.close()
            
            return True
        return False
    
    def is_test_run_running(self, test_run_id: int) -> bool:
        """检查测试运行是否正在执行"""
        return test_run_id in self.running_tasks

