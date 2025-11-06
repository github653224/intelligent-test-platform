from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TestCaseBase(BaseModel):
    project_id: Optional[int] = None
    requirement_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    test_type: Optional[str] = None  # functional, api, ui
    priority: Optional[str] = None
    status: Optional[str] = None
    test_data: Optional[Dict[str, Any]] = None
    expected_result: Optional[str] = None
    ai_generated: Optional[bool] = None


class TestCaseCreate(BaseModel):
    project_id: int
    requirement_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    test_type: str
    priority: Optional[str] = "medium"
    status: Optional[str] = "draft"
    test_data: Optional[Dict[str, Any]] = None
    expected_result: Optional[str] = None
    ai_generated: Optional[bool] = False


class TestCaseUpdate(TestCaseBase):
    pass


class TestCaseOut(TestCaseBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


