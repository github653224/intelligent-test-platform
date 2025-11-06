import asyncio
import logging
from typing import Dict, Any, List, Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from ai_engine.models.ai_client import AIClient
from ai_engine.processors.requirement_analyzer import RequirementAnalyzer
from ai_engine.processors.test_case_generator import TestCaseGenerator
from ai_engine.processors.api_test_generator import APITestGenerator
from ai_engine.processors.ui_test_generator import UITestGenerator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI测试引擎", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化AI客户端
ai_client = AIClient()

# 初始化处理器
requirement_analyzer = RequirementAnalyzer(ai_client)
test_case_generator = TestCaseGenerator(ai_client)
api_test_generator = APITestGenerator(ai_client)
ui_test_generator = UITestGenerator(ai_client)


class RequirementRequest(BaseModel):
    requirement_text: str
    project_context: str = ""
    test_focus: List[str] = []


class TestCaseRequest(BaseModel):
    requirement_id: int | None = None
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


class APITestRequest(BaseModel):
    api_documentation: str
    base_url: str
    test_scenarios: List[str] = []


class UITestRequest(BaseModel):
    page_url: str
    user_actions: List[str]
    test_scenarios: List[str] = []


class ModelSwitchRequest(BaseModel):
    model_type: str


@app.post("/analyze_requirement")
async def analyze_requirement(request: RequirementRequest):
    """分析需求并生成测试要点"""
    try:
        analysis = await requirement_analyzer.analyze(
            request.requirement_text,
            request.project_context,
            request.test_focus
        )
        return {
            "status": "success",
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"需求分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_test_cases")
async def generate_test_cases(request: TestCaseRequest):
    """基于需求生成测试用例"""
    try:
        test_cases = await test_case_generator.generate(
            request.requirement_text,
            request.test_type,
            request.test_scope,
            request.generate_script
        )
        return {
            "status": "success",
            "test_cases": test_cases
        }
    except Exception as e:
        logger.error(f"测试用例生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_api_tests")
async def generate_api_tests(request: APITestRequest):
    """生成API测试脚本"""
    try:
        api_tests = await api_test_generator.generate(
            request.api_documentation,
            request.base_url,
            request.test_scenarios
        )
        return {
            "status": "success",
            "api_tests": api_tests
        }
    except Exception as e:
        logger.error(f"API测试生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_ui_tests")
async def generate_ui_tests(request: UITestRequest):
    """生成UI自动化测试脚本"""
    try:
        ui_tests = await ui_test_generator.generate(
            request.page_url,
            request.user_actions,
            request.test_scenarios
        )
        return {
            "status": "success",
            "ui_tests": ui_tests
        }
    except Exception as e:
        logger.error(f"UI测试生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze-requirement-stream")
async def analyze_requirement_stream(request: RequirementRequest):
    """流式分析需求并生成测试要点"""
    async def generate():
        async for chunk in requirement_analyzer.analyze_stream(
            requirement_text=request.requirement_text,
            project_context=request.project_context,
            test_focus=request.test_focus
        ):
            # 确保每个chunk都是SSE格式
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
@app.post("/api/generate-test-cases-stream")
async def generate_test_cases_stream(request: TestCaseRequest):
    """流式生成测试用例"""
    async def generate():
        async for chunk in test_case_generator.generate_stream(
            requirement_text=request.requirement_text,
            test_type=request.test_type,
            test_scope=request.test_scope,
            generate_script=request.generate_script
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/switch-model")
async def switch_model(request: ModelSwitchRequest):
    """切换AI模型"""
    success = await ai_client.switch_model(request.model_type)
    if success:
        return {"status": "success", "message": f"已切换到{request.model_type}模型"}
    else:
        raise HTTPException(status_code=400, detail=f"切换到{request.model_type}模型失败")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "ai_engine": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)