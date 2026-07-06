"""Project and environment API routes used by test case modules."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import ApiCase, Environment, Project, TestRun, UiCase
from app.schemas.entities import (
    EnvironmentCreate,
    EnvironmentRead,
    ProjectCreate,
    ProjectRead,
)


router = APIRouter()

# 项目与环境：接口用例和 UI 用例都依赖项目，所以权限归到 projects。
@router.get("/projects", response_model=list[ProjectRead])
def list_projects(_: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    """List projects."""
    return db.query(Project).order_by(Project.id.desc()).all()


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    """Create a project."""
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    """Update a project."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    # Copy validated request fields onto the ORM model so SQLAlchemy can persist the change.
    for key, value in payload.model_dump().items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    """Delete a project and its related cases and runs."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    # Remove dependent cases and execution history first to avoid orphaned run records.
    api_ids = [row[0] for row in db.query(ApiCase.id).filter(ApiCase.project_id == project_id).all()]
    ui_ids = [row[0] for row in db.query(UiCase.id).filter(UiCase.project_id == project_id).all()]
    if api_ids:
        db.query(TestRun).filter(TestRun.case_type == "api", TestRun.case_id.in_(api_ids)).delete(synchronize_session=False)
        db.query(ApiCase).filter(ApiCase.id.in_(api_ids)).delete(synchronize_session=False)
    if ui_ids:
        db.query(TestRun).filter(TestRun.case_type == "ui", TestRun.case_id.in_(ui_ids)).delete(synchronize_session=False)
        db.query(UiCase).filter(UiCase.id.in_(ui_ids)).delete(synchronize_session=False)
    db.delete(project)
    db.commit()
    return {"status": "ok"}


@router.get("/environments", response_model=list[EnvironmentRead])
def list_environments(_: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    """List environment records."""
    return db.query(Environment).order_by(Environment.id.desc()).all()


@router.post("/environments", response_model=EnvironmentRead)
def create_environment(payload: EnvironmentCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    """Create an environment record."""
    # Environment base URLs are also guarded because later tests may use them as targets.
    validate_public_http_url(payload.base_url)
    environment = Environment(**payload.model_dump())
    db.add(environment)
    db.commit()
    db.refresh(environment)
    return environment
