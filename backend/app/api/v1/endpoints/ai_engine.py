import httpx
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# AI引擎服务地址
AI_ENGINE_URL = "http://localhost:8001"


class RequirementAnalysisRequest(BaseModel):
    requirement_text: str
    project_context: str = ""
    test_focus: List[str] = []


class TestCaseGenerationRequest(BaseModel):
    requirement_text: str
    test_type: str  # functional, api, ui
    test_scope: Dict[str, Any] = {}


class APITestGenerationRequest(BaseModel):
    api_documentation: str
    base_url: str
    test_scenarios: List[str] = []


class UITestGenerationRequest(BaseModel):
    page_url: str
    user_actions: List[str]
    test_scenarios: List[str] = []


@router.post("/analyze-requirement")
async def analyze_requirement(request: RequirementAnalysisRequest):
    """分析需求并生成测试要点"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/analyze_requirement",
                json={
                    "requirement_text": request.requirement_text,
                    "project_context": request.project_context,
                    "test_focus": request.test_focus
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"AI引擎请求失败: {e}")
        raise HTTPException(status_code=503, detail="AI引擎服务不可用")
    except httpx.HTTPStatusError as e:
        logger.error(f"AI引擎响应错误: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.post("/generate-test-cases")
async def generate_test_cases(request: TestCaseGenerationRequest):
    """基于需求生成测试用例"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/generate_test_cases",
                json={
                    "requirement_text": request.requirement_text,
                    "test_type": request.test_type,
                    "test_scope": request.test_scope
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"AI引擎请求失败: {e}")
        raise HTTPException(status_code=503, detail="AI引擎服务不可用")
    except httpx.HTTPStatusError as e:
        logger.error(f"AI引擎响应错误: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.post("/generate-api-tests")
async def generate_api_tests(request: APITestGenerationRequest):
    """生成API测试脚本"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/generate_api_tests",
                json={
                    "api_documentation": request.api_documentation,
                    "base_url": request.base_url,
                    "test_scenarios": request.test_scenarios
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"AI引擎请求失败: {e}")
        raise HTTPException(status_code=503, detail="AI引擎服务不可用")
    except httpx.HTTPStatusError as e:
        logger.error(f"AI引擎响应错误: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.post("/generate-ui-tests")
async def generate_ui_tests(request: UITestGenerationRequest):
    """生成UI自动化测试脚本"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/generate_ui_tests",
                json={
                    "page_url": request.page_url,
                    "user_actions": request.user_actions,
                    "test_scenarios": request.test_scenarios
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"AI引擎请求失败: {e}")
        raise HTTPException(status_code=503, detail="AI引擎服务不可用")
    except httpx.HTTPStatusError as e:
        logger.error(f"AI引擎响应错误: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/health")
async def ai_engine_health():
    """检查AI引擎健康状态"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AI_ENGINE_URL}/health", timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"AI引擎健康检查失败: {e}")
        return {"status": "unhealthy", "error": str(e)}
    except httpx.HTTPStatusError as e:
        logger.error(f"AI引擎健康检查错误: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.post("/analyze-requirement-stream")
async def analyze_requirement_stream(request: Request):
    """流式分析需求并生成测试要点"""
    try:
        body = await request.json()
        logger.info(f"收到流式分析请求，AI引擎URL: {AI_ENGINE_URL}")
        
        async def event_generator():
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{AI_ENGINE_URL}/api/analyze-requirement-stream",
                    json=body,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response.raise_for_status()
                    logger.info(f"AI引擎响应状态码: {response.status_code}")
                    current_chunk = ""
                    
                    async for chunk in response.aiter_bytes():
                        text = chunk.decode()
                        if text.strip():
                            # 清理SSE格式，只保留实际内容
                            content = text.replace('data:', '').strip()
                            if content:
                                yield f"data: {content}\n\n"
                    
                    yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        logger.error(f"流式响应失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch-model")
async def switch_model(request: Request):
    """切换AI模型"""
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_ENGINE_URL}/api/switch-model",
                json=body,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"切换模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))