import httpx
import logging
from typing import Dict, Any, List, Union
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from app.utils.document_parser import DocumentParser

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
    test_scope: Union[str, Dict[str, Any]] = {}
    generate_script: bool = True  # 是否同时生成自动化测试脚本
    
    @field_validator('test_scope', mode='before')
    @classmethod
    def normalize_test_scope(cls, v):
        """将字符串转换为字典格式"""
        if isinstance(v, str):
            # 如果 test_scope 是字符串，将其包装为字典
            if v.strip():
                return {"description": v}
            return {}
        return v or {}


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
                timeout=180.0  # 增加到3分钟，因为AI生成可能需要更长时间
            )
            response.raise_for_status()
            result = response.json()
            # 确保返回格式正确
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                return {"api_tests": result, "status": "success"}
            else:
                return {"api_tests": [], "status": "success", "raw_response": str(result)}
    except httpx.TimeoutException as e:
        logger.error(f"AI引擎请求超时: {e}")
        raise HTTPException(status_code=504, detail="AI引擎请求超时，请稍后重试")
    except httpx.RequestError as e:
        logger.error(f"AI引擎请求失败: {e}")
        raise HTTPException(status_code=503, detail=f"AI引擎服务不可用: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"AI引擎响应错误: {e}, 响应内容: {e.response.text[:500]}")
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
                timeout=180.0  # 增加到3分钟，因为AI生成可能需要更长时间
            )
            response.raise_for_status()
            result = response.json()
            # 确保返回格式正确
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                return {"ui_tests": result, "status": "success"}
            else:
                return {"ui_tests": [], "status": "success", "raw_response": str(result)}
    except httpx.TimeoutException as e:
        logger.error(f"AI引擎请求超时: {e}")
        raise HTTPException(status_code=504, detail="AI引擎请求超时，请稍后重试")
    except httpx.RequestError as e:
        logger.error(f"AI引擎请求失败: {e}")
        raise HTTPException(status_code=503, detail=f"AI引擎服务不可用: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"AI引擎响应错误: {e}, 响应内容: {e.response.text[:500]}")
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
@router.post("/generate-test-cases-stream")
async def generate_test_cases_stream(request: Request):
    """流式生成测试用例（SSE透传AI引擎）"""
    try:
        body_data = await request.json()
        # 验证和规范化请求数据
        validated_request = TestCaseGenerationRequest(**body_data)
        body = validated_request.model_dump()
        async def event_generator():
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{AI_ENGINE_URL}/api/generate-test-cases-stream",
                    json=body,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        text = chunk.decode()
                        if text.strip():
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
        logger.error(f"测试用例流式响应失败: {e}", exc_info=True)
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


@router.post("/parse-document")
async def parse_document(file: UploadFile = File(...)):
    """
    解析上传的文档文件（Word、PDF、Excel、XMind）
    返回提取的文本内容，可直接用于需求分析
    """
    try:
        # 读取文件内容
        file_content = await file.read()
        
        if not file_content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        # 解析文档
        result = DocumentParser.parse(file_content, file.filename or "unknown")
        
        return {
            "success": True,
            "filename": file.filename,
            "text": result["text"],
            "metadata": result.get("metadata", {}),
            "text_length": len(result["text"])
        }
    except ValueError as e:
        logger.error(f"文档解析错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        logger.error(f"缺少依赖库: {e}")
        raise HTTPException(status_code=500, detail=f"服务器缺少必要的依赖库: {str(e)}")
    except Exception as e:
        logger.error(f"解析文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")