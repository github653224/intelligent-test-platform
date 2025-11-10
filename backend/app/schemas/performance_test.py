"""
性能测试 Pydantic 模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class PerformanceTestBase(BaseModel):
    """性能测试基础模型"""
    name: str = Field(..., description="测试名称")
    description: Optional[str] = Field(None, description="测试描述")
    project_id: int = Field(..., description="项目ID")


class PerformanceTestCreate(PerformanceTestBase):
    """创建性能测试请求"""
    test_description: str = Field(..., description="测试描述（一句话描述性能测试需求）")
    target_url: Optional[str] = Field(None, description="目标URL")
    load_config: Optional[Dict[str, Any]] = Field(None, description="负载配置（VUs、duration等）")
    generation_mode: str = Field("regex", description="生成模式：'ai' 或 'regex'，ai=AI直接生成，regex=正则匹配生成")
    k6_script: Optional[str] = Field(None, description="已生成的k6脚本（如果提供，则直接使用，不再生成）")


class PerformanceTestUpdate(BaseModel):
    """更新性能测试请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    k6_script: Optional[str] = None
    execution_config: Optional[Dict[str, Any]] = None


class PerformanceTestOut(PerformanceTestBase):
    """性能测试输出模型"""
    id: int
    k6_script: Optional[str] = None
    script_generated_by_ai: Optional[str] = "yes"
    ai_prompt: Optional[str] = None
    execution_config: Optional[Dict[str, Any]] = None
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    results: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    analysis_generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PerformanceTestDetail(PerformanceTestOut):
    """性能测试详情模型"""
    ai_prompt: Optional[str] = None


class K6ScriptGenerateRequest(BaseModel):
    """k6 脚本生成请求"""
    test_description: str = Field(..., description="测试描述（一句话描述性能测试需求）")
    target_url: Optional[str] = Field(None, description="目标URL")
    load_config: Optional[Dict[str, Any]] = Field(None, description="负载配置")
    generation_mode: str = Field("regex", description="生成模式：'ai' 或 'regex'，ai=AI直接生成，regex=正则匹配生成")


class K6ScriptGenerateResponse(BaseModel):
    """k6 脚本生成响应"""
    status: str
    script: Optional[str] = None
    test_description: str
    error: Optional[str] = None


class PerformanceTestExecuteRequest(BaseModel):
    """性能测试执行请求"""
    performance_test_id: Optional[int] = Field(None, description="性能测试ID（路径参数中已包含，此处可选）")
    additional_args: Optional[List[str]] = Field(None, description="额外的k6命令行参数")


class PerformanceTestAnalysisRequest(BaseModel):
    """性能测试分析请求"""
    prompt: Optional[str] = None  # 可选的自定义分析提示词

