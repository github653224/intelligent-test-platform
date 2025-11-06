from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Requirement
from app.schemas.requirement import RequirementCreate, RequirementUpdate, RequirementOut

router = APIRouter()


@router.options("/")
@router.options("/{requirement_id}")
async def options_handler(response: Response):
    """处理 OPTIONS 预检请求"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    return Response(status_code=200)


@router.get("/", response_model=List[RequirementOut])
def list_requirements(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    """获取需求列表"""
    query = db.query(Requirement)
    if project_id is not None:
        query = query.filter(Requirement.project_id == project_id)
    return query.order_by(Requirement.id.desc()).all()


@router.get("/{requirement_id}", response_model=RequirementOut)
def get_requirement(requirement_id: int, db: Session = Depends(get_db)):
    """获取需求详情"""
    requirement = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return requirement


@router.post("/", response_model=RequirementOut)
def create_requirement(payload: RequirementCreate, db: Session = Depends(get_db)):
    """创建需求"""
    requirement = Requirement(
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority or "medium",
        status=payload.status or "draft",
        ai_analysis=payload.ai_analysis or {}
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


@router.put("/{requirement_id}", response_model=RequirementOut)
def update_requirement(requirement_id: int, payload: RequirementUpdate, db: Session = Depends(get_db)):
    """更新需求"""
    requirement = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(requirement, field, value)
    
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


@router.delete("/{requirement_id}")
def delete_requirement(requirement_id: int, db: Session = Depends(get_db)):
    """删除需求"""
    requirement = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    db.delete(requirement)
    db.commit()
    return {"status": "success"}
