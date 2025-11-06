from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import TestCase
from app.schemas.test_case import TestCaseCreate, TestCaseUpdate, TestCaseOut

router = APIRouter()


@router.options("/")
@router.options("/{test_case_id}")
async def options_handler(response: Response):
    """处理 OPTIONS 预检请求"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    return Response(status_code=200)


@router.get("/", response_model=List[TestCaseOut])
def list_test_cases(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(TestCase)
    if project_id is not None:
        query = query.filter(TestCase.project_id == project_id)
    return query.order_by(TestCase.id.desc()).all()


@router.get("/{test_case_id}", response_model=TestCaseOut)
def get_test_case(test_case_id: int, db: Session = Depends(get_db)):
    obj = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Test case not found")
    return obj


@router.post("/", response_model=TestCaseOut)
def create_test_case(payload: TestCaseCreate, db: Session = Depends(get_db)):
    obj = TestCase(
        project_id=payload.project_id,
        requirement_id=payload.requirement_id,
        title=payload.title,
        description=payload.description,
        test_type=payload.test_type,
        priority=payload.priority or "medium",
        status=payload.status or "draft",
        test_data=payload.test_data or {},
        expected_result=payload.expected_result,
        ai_generated="true" if payload.ai_generated else "false",
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{test_case_id}", response_model=TestCaseOut)
def update_test_case(test_case_id: int, payload: TestCaseUpdate, db: Session = Depends(get_db)):
    obj = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Test case not found")
    for field, value in payload.dict(exclude_unset=True).items():
        if field == "ai_generated" and value is not None:
            setattr(obj, "ai_generated", "true" if value else "false")
        else:
            setattr(obj, field, value)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{test_case_id}")
def delete_test_case(test_case_id: int, db: Session = Depends(get_db)):
    obj = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Test case not found")
    db.delete(obj)
    db.commit()
    return {"status": "success"}
