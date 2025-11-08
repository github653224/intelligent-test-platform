"""
数据库初始化脚本
如果 Alembic 无法运行，可以使用此脚本直接创建表
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine
from app.models.base import Base
from app.models.project import Project, Requirement, TestCase, TestStep, TestSuite, TestRun
from app.models.performance_test import PerformanceTest

def init_db():
    """创建所有数据库表"""
    print("正在创建数据库表...")
    try:
        # 导入所有模型以确保它们被注册到 Base.metadata
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功！")
        print("\n已创建的表：")
        print("  - projects")
        print("  - requirements")
        print("  - test_cases")
        print("  - test_steps")
        print("  - test_suites")
        print("  - test_runs")
        print("  - performance_tests")
    except Exception as e:
        print(f"❌ 创建数据库表失败: {e}")
        print("\n请确保：")
        print("  1. PostgreSQL 数据库服务正在运行")
        print("  2. 数据库连接配置正确（检查 app/core/config.py）")
        print("  3. 数据库 'ai_test_platform' 已创建")
        sys.exit(1)

if __name__ == "__main__":
    init_db()

