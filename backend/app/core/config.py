from typing import List, Optional, Union
# from pydantic import AnyHttpUrl, BaseSettings, validator
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "change-this-secret-key-in-production"  # 应该从环境变量读取
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # 更新CORS配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    # 端口相关配置
    BACKEND_PORT: str = "8000"
    AI_ENGINE_PORT: str = "8001"
    FRONTEND_PORT: str = "3000"
    OLLAMA_PORT: str = "11434"

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 数据库配置
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"  # 默认密码，可通过环境变量覆盖
    POSTGRES_DB: str = "ai_test_platform"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        password = values.get('POSTGRES_PASSWORD') or 'password'
        return f"postgresql://{values.get('POSTGRES_USER')}:{password}@{values.get('POSTGRES_SERVER')}/{values.get('POSTGRES_DB')}"

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI模型配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    DEEPSEEK_API_KEY: Optional[str] = None  # 应该从环境变量读取
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"  # 设置为你想使用的 Deepseek 模型
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"
    DEFAULT_AI_MODEL: str = "ollama"  # 设置默认使用 ollama
    
    # 测试配置
    SELENIUM_WEBDRIVER_PATH: Optional[str] = None
    PLAYWRIGHT_BROWSERS_PATH: Optional[str] = None
    K6_BINARY_PATH: Optional[str] = None  # k6二进制文件路径，如果为None则自动查找
    
    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    class Config:
        case_sensitive = True
        env_file = [".env", "../.env"]  # 尝试从当前目录和父目录读取 .env 文件


settings = Settings()

# 你可以在此文件中添加中文注释或文档说明，代码本身无需修改。