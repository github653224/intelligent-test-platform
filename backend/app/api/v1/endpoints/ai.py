from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.requirement_analyzer import requirement_analyzer

router = APIRouter()

class RequirementRequest(BaseModel):
    requirement_text: str
    project_context: str = ""
    test_focus: list = []

@router.post("/analyze-requirement-stream")
async def analyze_requirement_stream(request: RequirementRequest):
    async def generate():
        async for chunk in requirement_analyzer.analyze_stream(
            requirement_text=request.requirement_text,
            project_context=request.project_context,
            test_focus=request.test_focus
        ):
            yield f"data: {chunk}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
