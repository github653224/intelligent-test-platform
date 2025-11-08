"""
性能测试数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.models.base import Base


class PerformanceTest(Base):
    """性能测试运行记录"""
    __tablename__ = "performance_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, comment="测试名称")
    description = Column(Text, comment="测试描述")
    
    # k6 脚本相关
    k6_script = Column(Text, comment="k6 测试脚本内容")
    script_generated_by_ai = Column(String(50), default="yes", comment="脚本是否由AI生成")
    ai_prompt = Column(Text, comment="AI生成脚本时的提示词")
    
    # 执行配置
    execution_config = Column(JSON, comment="执行配置（VUs、duration等）")
    
    # 执行状态
    status = Column(String(50), default="pending", comment="状态：pending, running, completed, failed, cancelled")
    start_time = Column(DateTime, comment="开始时间")
    end_time = Column(DateTime, comment="结束时间")
    duration = Column(Float, comment="执行时长（秒）")
    
    # 测试结果
    results = Column(JSON, comment="测试结果（指标、统计等）")
    
    # 分析结果
    analysis = Column(JSON, comment="AI分析结果")
    analysis_generated_at = Column(DateTime, comment="分析生成时间")
    
    # 关联关系
    project = relationship("Project", back_populates="performance_tests")
    
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

