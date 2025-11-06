from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import os
import traceback

from app.api.v1.api import api_router
from app.core.config import settings
from app.services.test_scheduler import test_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    if not test_scheduler.scheduler.running:
        test_scheduler.scheduler.start()
        print("测试调度器已启动")
    yield
    # 关闭时
    if test_scheduler.scheduler.running:
        test_scheduler.scheduler.shutdown()
        print("测试调度器已停止")


app = FastAPI(
    title="AI智能自动化测试平台",
    description="基于AI的智能自动化测试平台，支持需求分析、测试用例生成、接口测试和UI自动化测试",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# 修改CORS配置
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # 预检请求缓存时间
)

# 全局异常处理器，确保错误响应也包含 CORS 头
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，确保所有错误响应都包含 CORS 头"""
    error_detail = str(exc)
    if isinstance(exc, SQLAlchemyError):
        error_detail = "数据库操作失败，请检查数据库连接"
        print(f"数据库错误: {exc}")
        traceback.print_exc()
    elif isinstance(exc, RequestValidationError):
        error_detail = "请求参数验证失败"
    
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": error_detail}
    )
    # 添加 CORS 头
    origin = request.headers.get("origin")
    if origin in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# 挂载静态文件
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static"
)

@app.get("/")
async def root():
    return {"message": "AI智能自动化测试平台 API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}