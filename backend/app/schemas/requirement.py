from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RequirementBase(BaseModel):
    project_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None


class RequirementCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    status: Optional[str] = "draft"
    ai_analysis: Optional[Dict[str, Any]] = None


class RequirementUpdate(RequirementBase):
    pass


class RequirementOut(RequirementBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

