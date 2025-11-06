from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TestResult(BaseModel):
    """测试结果详情"""
    test_case_id: int
    test_case_title: str
    status: str  # passed, failed, skipped, error, blocked
    duration: float  # 执行时长（秒）
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    steps: List[Dict[str, Any]] = []  # 测试步骤执行结果
    actual_result: Optional[str] = None
    screenshots: List[str] = []  # 截图路径（UI测试）
    logs: List[str] = []  # 执行日志
    # 手动验证相关字段
    manually_verified: Optional[bool] = False  # 是否手动验证
    verified_by: Optional[str] = None  # 验证人
    verified_at: Optional[str] = None  # 验证时间
    verification_notes: Optional[str] = None  # 验证备注
    failure_reason: Optional[str] = None  # 失败原因
    bug_id: Optional[str] = None  # 关联的缺陷ID
    attachments: Optional[List[str]] = []  # 附件列表（截图、日志等）


class TestRunBase(BaseModel):
    project_id: Optional[int] = None
    test_suite_id: Optional[int] = None
    name: Optional[str] = None
    status: Optional[str] = None  # pending, running, completed, failed, cancelled
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


class TestRunCreate(BaseModel):
    project_id: int
    test_suite_id: Optional[int] = None
    name: str
    test_case_ids: Optional[List[int]] = None  # 要执行的测试用例ID列表
    execution_config: Optional[Dict[str, Any]] = None  # 执行配置（如环境变量、浏览器等）


class TestRunUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    end_time: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


class TestRunOut(TestRunBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 统计信息
    total_cases: Optional[int] = None
    passed_cases: Optional[int] = None
    failed_cases: Optional[int] = None
    skipped_cases: Optional[int] = None
    duration: Optional[float] = None  # 总执行时长（秒）
    
    model_config = ConfigDict(from_attributes=True)


class TestRunDetail(TestRunOut):
    """测试运行详情，包含测试结果"""
    test_results: List[TestResult] = []

