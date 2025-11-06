"""
快速检查数据库连接和表是否存在
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine, SessionLocal
from app.models.base import Base
from app.models.project import Project, Requirement, TestCase, TestStep, TestSuite, TestRun
from sqlalchemy import inspect

def check_database():
    """检查数据库连接和表"""
    try:
        # 测试连接
        with engine.connect() as conn:
            print("✅ 数据库连接成功")
        
        # 检查表是否存在
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n📊 数据库中的表: {tables}")
        
        required_tables = ['projects', 'requirements', 'test_cases', 'test_steps', 'test_suites', 'test_runs']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"\n❌ 缺少表: {missing_tables}")
            print("请运行: cd backend && alembic upgrade head")
            print("或者运行: cd backend && python init_db.py")
            return False
        else:
            print("\n✅ 所有必需的表都存在")
            
            # 检查是否有数据
            db = SessionLocal()
            try:
                project_count = db.query(Project).count()
                print(f"📦 项目数量: {project_count}")
            finally:
                db.close()
            
            return True
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n请确保:")
        print("1. PostgreSQL 服务正在运行")
        print("2. 数据库 'ai_test_platform' 已创建")
        print("3. 数据库连接配置正确")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_database()

