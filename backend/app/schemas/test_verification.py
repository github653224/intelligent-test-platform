from typing import Optional, List
from pydantic import BaseModel


class ManualVerificationRequest(BaseModel):
    """手动验证请求"""
    test_run_id: int
    test_case_id: int
    status: str  # passed, failed, blocked, skipped
    actual_result: Optional[str] = None  # 实际结果
    verification_notes: Optional[str] = None  # 验证备注
    failure_reason: Optional[str] = None  # 失败原因（如果失败）
    bug_id: Optional[str] = None  # 关联的缺陷ID
    verified_by: Optional[str] = None  # 验证人
    step_results: Optional[List[dict]] = None  # 步骤级别的验证结果


class BatchVerificationRequest(BaseModel):
    """批量验证请求"""
    test_run_id: int
    verifications: List[ManualVerificationRequest]  # 多个测试用例的验证结果


class VerificationResult(BaseModel):
    """验证结果响应"""
    success: bool
    message: str
    updated_test_result: Optional[dict] = None

