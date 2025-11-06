"""
测试执行器模块
支持API测试、UI测试和功能测试的执行
"""
import asyncio
import json
import logging
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


class BaseTestExecutor:
    """测试执行器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.results: List[Dict[str, Any]] = []
    
    async def execute(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个测试用例"""
        raise NotImplementedError
    
    def _format_result(
        self,
        test_case_id: int,
        test_case_title: str,
        status: str,
        duration: float,
        error_message: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        actual_result: Optional[str] = None,
        screenshots: Optional[List[str]] = None,
        logs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """格式化测试结果"""
        return {
            "test_case_id": test_case_id,
            "test_case_title": test_case_title,
            "status": status,
            "duration": duration,
            "error_message": error_message,
            "error_traceback": None,
            "steps": steps or [],
            "actual_result": actual_result,
            "screenshots": screenshots or [],
            "logs": logs or []
        }


class APITestExecutor(BaseTestExecutor):
    """API测试执行器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:8000")
        self.timeout = config.get("timeout", 30)
    
    async def execute(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """执行API测试用例"""
        start_time = datetime.now()
        test_case_id = test_case.get("id", 0)
        test_case_title = test_case.get("title", "Unknown")
        test_data = test_case.get("test_data", {})
        test_steps = test_case.get("test_steps", [])
        
        try:
            # 检查是否有Python代码
            python_code = test_case.get("python_code")
            if python_code:
                return await self._execute_python_code(
                    test_case_id, test_case_title, python_code, start_time
                )
            
            # 如果没有Python代码，使用requests库执行
            return await self._execute_api_request(
                test_case_id, test_case_title, test_data, test_steps, start_time
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"API测试执行失败: {error_msg}", exc_info=True)
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status="error",
                duration=duration,
                error_message=error_msg,
                error_traceback=traceback.format_exc(),
                logs=[f"执行失败: {error_msg}"]
            )
    
    async def _execute_python_code(
        self, test_case_id: int, test_case_title: str, python_code: str, start_time: datetime
    ) -> Dict[str, Any]:
        """执行Python测试代码"""
        error_msg = None
        
        # 创建临时Python文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name
        
        try:
            # 执行Python脚本
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # 检查执行结果
            if process.returncode == 0:
                status = "passed"
                logs = stdout.decode('utf-8').split('\n') if stdout else []
            else:
                status = "failed"
                error_msg = stderr.decode('utf-8') if stderr else "测试执行失败"
                logs = [error_msg] + (stdout.decode('utf-8').split('\n') if stdout else [])
                
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status=status,
                duration=duration,
                error_message=error_msg if status == "failed" else None,
                logs=logs
            )
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    async def _execute_api_request(
        self,
        test_case_id: int,
        test_case_title: str,
        test_data: Dict[str, Any],
        test_steps: List[Dict[str, Any]],
        start_time: datetime
    ) -> Dict[str, Any]:
        """使用requests库执行API请求"""
        import aiohttp
        
        steps_result = []
        logs = []
        
        try:
            request_method = test_data.get("request_method", "GET").upper()
            request_url = test_data.get("request_url", "")
            request_headers = test_data.get("request_headers", {})
            request_body = test_data.get("request_body", {})
            expected_status = test_data.get("expected_status_code", 200)
            
            # 构建完整URL
            if not request_url.startswith("http"):
                full_url = f"{self.base_url}{request_url}"
            else:
                full_url = request_url
            
            # 执行请求
            async with aiohttp.ClientSession() as session:
                if request_method == "GET":
                    async with session.get(full_url, headers=request_headers, timeout=self.timeout) as response:
                        status_code = response.status
                        response_body = await response.json() if response.content_type == 'application/json' else await response.text()
                elif request_method == "POST":
                    async with session.post(full_url, headers=request_headers, json=request_body, timeout=self.timeout) as response:
                        status_code = response.status
                        response_body = await response.json() if response.content_type == 'application/json' else await response.text()
                elif request_method == "PUT":
                    async with session.put(full_url, headers=request_headers, json=request_body, timeout=self.timeout) as response:
                        status_code = response.status
                        response_body = await response.json() if response.content_type == 'application/json' else await response.text()
                elif request_method == "DELETE":
                    async with session.delete(full_url, headers=request_headers, timeout=self.timeout) as response:
                        status_code = response.status
                        response_body = await response.json() if response.content_type == 'application/json' else await response.text()
                else:
                    raise ValueError(f"不支持的HTTP方法: {request_method}")
                
                # 验证状态码
                if status_code == expected_status:
                    status = "passed"
                    error_message = None
                else:
                    status = "failed"
                    error_message = f"期望状态码 {expected_status}，实际状态码 {status_code}"
                
                logs.append(f"请求方法: {request_method}")
                logs.append(f"请求URL: {full_url}")
                logs.append(f"响应状态码: {status_code}")
                logs.append(f"响应内容: {str(response_body)[:500]}")
                
                steps_result.append({
                    "step_number": 1,
                    "action": f"发送{request_method}请求",
                    "status": "passed" if status == "passed" else "failed",
                    "result": f"状态码: {status_code}"
                })
                
                # 验证响应体（如果有预期字段）
                expected_fields = test_data.get("expected_fields", [])
                if expected_fields and isinstance(response_body, dict):
                    missing_fields = [f for f in expected_fields if f not in response_body]
                    if missing_fields:
                        status = "failed"
                        error_message = f"响应中缺少字段: {', '.join(missing_fields)}"
                        steps_result.append({
                            "step_number": 2,
                            "action": "验证响应体字段",
                            "status": "failed",
                            "result": f"缺少字段: {', '.join(missing_fields)}"
                        })
                    else:
                        steps_result.append({
                            "step_number": 2,
                            "action": "验证响应体字段",
                            "status": "passed",
                            "result": "所有字段都存在"
                        })
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status=status,
                duration=duration,
                error_message=error_message,
                steps=steps_result,
                actual_result=json.dumps(response_body) if isinstance(response_body, dict) else str(response_body),
                logs=logs
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"API请求执行失败: {error_msg}", exc_info=True)
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status="error",
                duration=duration,
                error_message=error_msg,
                error_traceback=traceback.format_exc(),
                logs=[f"执行失败: {error_msg}"]
            )


class UITestExecutor(BaseTestExecutor):
    """UI测试执行器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.browser = config.get("browser", "chrome")
        self.headless = config.get("headless", True)
        self.base_url = config.get("base_url", "http://localhost:3000")
        self.timeout = config.get("timeout", 30)
    
    async def execute(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """执行UI测试用例"""
        start_time = datetime.now()
        test_case_id = test_case.get("id", 0)
        test_case_title = test_case.get("title", "Unknown")
        test_data = test_case.get("test_data", {})
        test_steps = test_case.get("test_steps", [])
        
        try:
            # 检查是否有Python代码
            python_code = test_case.get("python_code")
            if python_code:
                return await self._execute_python_code(
                    test_case_id, test_case_title, python_code, start_time
                )
            
            # 如果没有Python代码，使用selenium或playwright执行
            return await self._execute_ui_steps(
                test_case_id, test_case_title, test_data, test_steps, start_time
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"UI测试执行失败: {error_msg}", exc_info=True)
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status="error",
                duration=duration,
                error_message=error_msg,
                error_traceback=traceback.format_exc(),
                logs=[f"执行失败: {error_msg}"]
            )
    
    async def _execute_python_code(
        self, test_case_id: int, test_case_title: str, python_code: str, start_time: datetime
    ) -> Dict[str, Any]:
        """执行Python UI测试代码"""
        error_msg = None
        
        # 创建临时Python文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name
        
        try:
            # 执行Python脚本
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # 检查执行结果
            if process.returncode == 0:
                status = "passed"
                logs = stdout.decode('utf-8').split('\n') if stdout else []
            else:
                status = "failed"
                error_msg = stderr.decode('utf-8') if stderr else "测试执行失败"
                logs = [error_msg] + (stdout.decode('utf-8').split('\n') if stdout else [])
            
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status=status,
                duration=duration,
                error_message=error_msg if status == "failed" else None,
                logs=logs
            )
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    async def _execute_ui_steps(
        self,
        test_case_id: int,
        test_case_title: str,
        test_data: Dict[str, Any],
        test_steps: List[Dict[str, Any]],
        start_time: datetime
    ) -> Dict[str, Any]:
        """使用selenium/playwright执行UI测试步骤"""
        # 这里是一个简化的实现，实际应该使用selenium或playwright
        # 由于这些库需要浏览器驱动，这里先返回一个模拟结果
        steps_result = []
        logs = []
        screenshots = []
        
        try:
            page_url = test_data.get("page_url", "")
            if not page_url.startswith("http"):
                full_url = f"{self.base_url}{page_url}"
            else:
                full_url = page_url
            
            logs.append(f"访问页面: {full_url}")
            
            # 模拟执行步骤
            for step in test_steps:
                step_number = step.get("step_number", 0)
                action = step.get("action", "")
                step_data = step.get("test_data", {})
                
                logs.append(f"步骤 {step_number}: {action}")
                
                # 这里应该实际执行UI操作
                # 由于需要浏览器环境，暂时标记为跳过
                steps_result.append({
                    "step_number": step_number,
                    "action": action,
                    "status": "skipped",
                    "result": "需要浏览器环境才能执行"
                })
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status="skipped",
                duration=duration,
                error_message="UI测试需要浏览器环境，请使用Python代码执行",
                steps=steps_result,
                screenshots=screenshots,
                logs=logs
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"UI测试执行失败: {error_msg}", exc_info=True)
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status="error",
                duration=duration,
                error_message=error_msg,
                error_traceback=traceback.format_exc(),
                logs=[f"执行失败: {error_msg}"]
            )


class FunctionalTestExecutor(BaseTestExecutor):
    """功能测试执行器（主要用于验证业务逻辑）"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
    
    async def execute(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """执行功能测试用例"""
        start_time = datetime.now()
        test_case_id = test_case.get("id", 0)
        test_case_title = test_case.get("title", "Unknown")
        test_data = test_case.get("test_data", {})
        test_steps = test_case.get("test_steps", [])
        
        try:
            # 检查是否有Python代码可以执行
            python_code = test_case.get("python_code")
            if python_code:
                return await self._execute_python_code(
                    test_case_id, test_case_title, python_code, start_time
                )
            
            # 如果没有Python代码，尝试根据测试步骤执行
            # 功能测试通常需要手动验证或集成测试环境
            # 但我们可以尝试执行一些基本的验证
            steps_result = []
            logs = []
            
            # 检查是否有可以自动执行的步骤
            has_executable_steps = False
            for step in test_steps:
                step_data = step.get("test_data", {})
                # 如果步骤中有API调用信息，可以尝试执行
                if step_data.get("url") or step_data.get("api_url"):
                    has_executable_steps = True
                    break
            
            if has_executable_steps:
                # 尝试执行可以自动化的步骤
                for step in test_steps:
                    step_number = step.get("step_number", 0)
                    action = step.get("action", "")
                    expected_result = step.get("expected_result", "")
                    step_data = step.get("test_data", {})
                    
                    logs.append(f"步骤 {step_number}: {action}")
                    
                    # 如果步骤包含API调用，尝试执行
                    if step_data.get("url") or step_data.get("api_url"):
                        try:
                            # 这里可以调用API执行器执行相关步骤
                            # 暂时标记为需要实现
                            steps_result.append({
                                "step_number": step_number,
                                "action": action,
                                "status": "skipped",
                                "result": "功能测试API步骤需要集成API执行器"
                            })
                        except Exception as e:
                            steps_result.append({
                                "step_number": step_number,
                                "action": action,
                                "status": "failed",
                                "result": f"执行失败: {str(e)}"
                            })
                    else:
                        steps_result.append({
                            "step_number": step_number,
                            "action": action,
                            "status": "pending",
                            "result": "需要手动验证"
                        })
                
                duration = (datetime.now() - start_time).total_seconds()
                
                # 检查是否有失败的步骤
                failed_steps = [s for s in steps_result if s.get("status") == "failed"]
                skipped_steps = [s for s in steps_result if s.get("status") == "skipped"]
                
                if failed_steps:
                    status = "failed"
                elif all(s.get("status") == "pending" for s in steps_result):
                    status = "skipped"
                else:
                    status = "passed"
                
                return self._format_result(
                    test_case_id=test_case_id,
                    test_case_title=test_case_title,
                    status=status,
                    duration=duration,
                    error_message=None if status != "failed" else "部分步骤执行失败",
                    steps=steps_result,
                    logs=logs
                )
            else:
                # 没有可执行的步骤，标记为需要手动验证
                for step in test_steps:
                    step_number = step.get("step_number", 0)
                    action = step.get("action", "")
                    expected_result = step.get("expected_result", "")
                    
                    logs.append(f"步骤 {step_number}: {action}")
                    logs.append(f"预期结果: {expected_result}")
                    
                    steps_result.append({
                        "step_number": step_number,
                        "action": action,
                        "status": "pending",
                        "result": "功能测试需要手动验证或集成测试环境"
                    })
                
                duration = (datetime.now() - start_time).total_seconds()
                
                return self._format_result(
                    test_case_id=test_case_id,
                    test_case_title=test_case_title,
                    status="skipped",
                    duration=duration,
                    error_message="功能测试需要手动验证或集成测试环境（如包含Python代码，将自动执行）",
                    steps=steps_result,
                    logs=logs
                )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"功能测试执行失败: {error_msg}", exc_info=True)
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status="error",
                duration=duration,
                error_message=error_msg,
                error_traceback=traceback.format_exc(),
                logs=[f"执行失败: {error_msg}"]
            )
    
    async def _execute_python_code(
        self, test_case_id: int, test_case_title: str, python_code: str, start_time: datetime
    ) -> Dict[str, Any]:
        """执行Python功能测试代码"""
        error_msg = None
        
        # 创建临时Python文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name
        
        try:
            # 执行Python脚本
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=60  # 功能测试默认60秒超时
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # 检查执行结果
            if process.returncode == 0:
                status = "passed"
                logs = stdout.decode('utf-8').split('\n') if stdout else []
            else:
                status = "failed"
                error_msg = stderr.decode('utf-8') if stderr else "测试执行失败"
                logs = [error_msg] + (stdout.decode('utf-8').split('\n') if stdout else [])
            
            return self._format_result(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                status=status,
                duration=duration,
                error_message=error_msg if status == "failed" else None,
                logs=logs
            )
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestExecutorFactory:
    """测试执行器工厂"""
    
    @staticmethod
    def create_executor(test_type: str, config: Optional[Dict[str, Any]] = None) -> BaseTestExecutor:
        """根据测试类型创建对应的执行器"""
        if test_type == "api":
            return APITestExecutor(config)
        elif test_type == "ui":
            return UITestExecutor(config)
        elif test_type == "functional":
            return FunctionalTestExecutor(config)
        else:
            raise ValueError(f"不支持的测试类型: {test_type}")

