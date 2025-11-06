from fastapi import APIRouter

from app.api.v1.endpoints import projects, requirements, test_cases, test_runs, ai_engine, statistics, test_analysis

api_router = APIRouter()

# 包含各个模块的路由
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(requirements.router, prefix="/requirements", tags=["requirements"])
api_router.include_router(test_cases.router, prefix="/test-cases", tags=["test-cases"])
api_router.include_router(test_runs.router, prefix="/test-runs", tags=["test-runs"])
api_router.include_router(ai_engine.router, prefix="/ai", tags=["ai-engine"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["statistics"])
api_router.include_router(test_analysis.router, prefix="/analysis", tags=["test-analysis"])