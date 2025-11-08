from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 增加连接池大小，避免后台任务阻塞其他请求
# pool_size: 连接池中保持的连接数
# max_overflow: 连接池可以超过pool_size的连接数
# pool_timeout: 获取连接的超时时间（秒）
# pool_pre_ping: 每次使用前检查连接是否有效
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=20,  # 增加连接池大小
    max_overflow=40,  # 允许超过pool_size的连接数
    pool_timeout=30  # 获取连接的超时时间
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


