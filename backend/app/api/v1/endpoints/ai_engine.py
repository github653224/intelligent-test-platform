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
    parsed_doc: Dict[str, Any] = None  # 解析后的API文档结构（可选）


class UITestGenerationRequest(BaseModel):
    page_url: str
    user_actions: Union[str, List[str]]  # 支持字符串（业务需求描述）或列表（操作步骤）
    test_scenarios: List[str] = []
    page_info: Dict[str, Any] = None  # 页面分析结果（可选）


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
    """生成API测试脚本（工程化结构）"""
    try:
        async with httpx.AsyncClient() as client:
            request_data = {
                "api_documentation": request.api_documentation,
                "base_url": request.base_url,
                "test_scenarios": request.test_scenarios
            }
            
            # 如果提供了parsed_doc，添加到请求中
            if request.parsed_doc:
                request_data["parsed_doc"] = request.parsed_doc
            
            response = await client.post(
                f"{AI_ENGINE_URL}/generate_api_tests",
                json=request_data,
                timeout=300.0  # 增加到5分钟，因为生成所有接口的测试代码需要更长时间
            )
            response.raise_for_status()
            result = response.json()
            # 直接返回结果（已经是工程化结构）
            return result
    except httpx.TimeoutException as e:
        logger.error(f"AI引擎请求超时: {e}")
        raise HTTPException(status_code=504, detail="AI引擎请求超时，请稍后重试")
    except httpx.RequestError as e:
        logger.error(f"AI引擎请求失败: {e}")
        raise HTTPException(status_code=503, detail=f"AI引擎服务不可用: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"AI引擎响应错误: {e}, 响应内容: {e.response.text[:500]}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.post("/analyze-page")
async def analyze_page(request: Dict[str, Any]):
    """
    分析页面结构
    使用Playwright自动访问URL并提取页面元素信息
    """
    try:
        from app.services.page_analyzer import PageAnalyzer
        
        page_url = request.get("url")
        if not page_url:
            raise HTTPException(status_code=400, detail="缺少URL参数")
        
        wait_time = request.get("wait_time", 2000)
        
        # 分析页面
        analyzer = PageAnalyzer()
        page_info = analyzer.analyze(page_url, wait_time)
        
        # 生成页面摘要
        summary = analyzer.generate_page_summary(page_info)
        
        return {
            "success": True,
            "page_info": page_info,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"页面分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"页面分析失败: {str(e)}")


@router.post("/generate-ui-tests")
async def generate_ui_tests(request: UITestGenerationRequest):
    """生成UI自动化测试脚本"""
    try:
        async with httpx.AsyncClient() as client:
            request_data = {
                "page_url": request.page_url,
                "user_actions": request.user_actions,
                "test_scenarios": request.test_scenarios
            }
            
            # 如果提供了page_info，添加到请求中
            if request.page_info:
                request_data["page_info"] = request.page_info
            
            response = await client.post(
                f"{AI_ENGINE_URL}/generate_ui_tests",
                json=request_data,
                timeout=300.0  # 增加到5分钟，因为页面分析和AI生成需要更长时间
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


@router.post("/parse-api-document")
async def parse_api_document(file: UploadFile = File(...)):
    """
    解析上传的API文档文件（OpenAPI/Swagger JSON/YAML、Postman Collection）
    返回解析后的API文档结构
    """
    try:
        from app.utils.api_doc_parser import APIDocParser
        
        # 读取文件内容
        file_content = await file.read()
        
        if not file_content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        # 解析API文档
        parsed_doc = APIDocParser.parse(file_content, file.filename or "unknown")
        
        # 提取摘要用于AI生成
        summary = APIDocParser.extract_endpoints_summary(parsed_doc)
        
        return {
            "success": True,
            "filename": file.filename,
            "parsed_doc": parsed_doc,
            "summary": summary,
            "endpoints_count": len(parsed_doc.get("endpoints", [])),
            "base_url": parsed_doc.get("base_url", "")
        }
    except ValueError as e:
        logger.error(f"API文档解析错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        logger.error(f"缺少依赖库: {e}")
        raise HTTPException(status_code=500, detail=f"服务器缺少必要的依赖库: {str(e)}")
    except Exception as e:
        logger.error(f"解析API文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"API文档解析失败: {str(e)}")