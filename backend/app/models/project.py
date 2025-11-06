from sqlalchemy import Column, String, Text, JSON, ForeignKey, Integer, Enum, TypeDecorator
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ProjectStatusEnum(TypeDecorator):
    """自定义类型装饰器，确保枚举值以正确的字符串形式存储到数据库"""
    impl = Enum('active', 'inactive', 'archived', name='projectstatus', native_enum=True)
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """在写入数据库前处理值"""
        if value is None:
            return None
        # 如果是枚举对象，返回其值（小写字符串）
        if isinstance(value, ProjectStatus):
            return value.value
        # 如果是字符串，确保是小写
        if isinstance(value, str):
            return value.lower()
        # 其他情况转换为小写字符串
        return str(value).lower()
    
    def process_result_value(self, value, dialect):
        """从数据库读取后处理值"""
        if value is None:
            return None
        try:
            return ProjectStatus(value.lower())
        except ValueError:
            return ProjectStatus.ACTIVE


class Project(Base):
    __tablename__ = "projects"
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    status = Column(ProjectStatusEnum(), default='active')
    config = Column(JSON, default={})
    
    # 关联关系
    requirements = relationship("Requirement", back_populates="project")
    test_cases = relationship("TestCase", back_populates="project")
    test_suites = relationship("TestSuite", back_populates="project")
    test_runs = relationship("TestRun", back_populates="project")


class Requirement(Base):
    __tablename__ = "requirements"
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    priority = Column(String(50), default="medium")
    status = Column(String(50), default="draft")
    ai_analysis = Column(JSON, default={})
    
    # 关联关系
    project = relationship("Project", back_populates="requirements")
    test_cases = relationship("TestCase", back_populates="requirement")


class TestCase(Base):
    __tablename__ = "test_cases"
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("requirements.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    test_type = Column(String(50), nullable=False)  # functional, api, ui
    priority = Column(String(50), default="medium")
    status = Column(String(50), default="draft")
    test_data = Column(JSON, default={})
    expected_result = Column(Text)
    ai_generated = Column(String(10), default="false")
    
    # 关联关系
    project = relationship("Project", back_populates="test_cases")
    requirement = relationship("Requirement", back_populates="test_cases")
    test_steps = relationship("TestStep", back_populates="test_case")


class TestStep(Base):
    __tablename__ = "test_steps"
    
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    action = Column(String(255), nullable=False)
    expected_result = Column(Text)
    test_data = Column(JSON, default={})
    
    # 关联关系
    test_case = relationship("TestCase", back_populates="test_steps")


class TestSuite(Base):
    __tablename__ = "test_suites"
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    test_cases = Column(JSON, default=[])  # 存储测试用例ID列表
    
    # 关联关系
    project = relationship("Project", back_populates="test_suites")
    test_runs = relationship("TestRun", back_populates="test_suite")


class TestRun(Base):
    __tablename__ = "test_runs"
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    test_suite_id = Column(Integer, ForeignKey("test_suites.id"))
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="running")
    start_time = Column(String(50))
    end_time = Column(String(50))
    results = Column(JSON, default={})
    
    # 关联关系
    project = relationship("Project", back_populates="test_runs")
    test_suite = relationship("TestSuite", back_populates="test_runs") 