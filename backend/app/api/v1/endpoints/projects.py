from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter()


@router.options("/")
@router.options("/{project_id}")
async def options_handler(response: Response):
    """处理 OPTIONS 预检请求"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    return Response(status_code=200)


@router.get("/", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    """获取项目列表"""
    return db.query(Project).order_by(Project.id.desc()).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """获取项目详情"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """创建项目"""
    try:
        # 确保状态值是小写的，匹配枚举类型
        status_value = (payload.status or "active").lower()
        if status_value not in ["active", "inactive", "archived"]:
            status_value = "active"
        
        # 直接使用字符串值
        project = Project(
            name=payload.name,
            description=payload.description,
            status=status_value,  # 直接使用字符串值
            config=payload.config or {}
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
    except Exception as e:
        db.rollback()
        print(f"创建项目失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    """更新项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = payload.dict(exclude_unset=True)
    # 如果更新状态，确保是小写字符串
    if "status" in update_data and update_data["status"]:
        status_value = str(update_data["status"]).lower()
        if status_value not in ["active", "inactive", "archived"]:
            status_value = "active"
        update_data["status"] = status_value
    
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """删除项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"status": "success"}
