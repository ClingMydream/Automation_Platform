from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, create_access_token, ensure_admin_user, get_current_user, hash_password, require_menu, verify_admin, verify_password
from app.core.config import get_settings
from app.core.menu import ADMIN_MENU, ADMIN_MENU_KEYS, MENU_OPTIONS
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import ApiCase, AppUser, Environment, FileTransfer, Project, TestRun, UiCase
from app.modules.common import (
    IMAGE_FORMATS,
    ImageGenerateRequest,
    _case_name_for_run,
    _cleanup_expired,
    _create_transfer,
    _file_response,
    _image_format,
    _normalize_menu_permissions,
    _report_summary,
    _safe_color,
    _serialize_image,
    _svg_response,
    _transfer_dir,
    _user_response,
    _draw_center_text,
)
from app.schemas.entities import (
    ApiCaseCreate,
    ApiCaseRead,
    EnvironmentCreate,
    EnvironmentRead,
    LoginRequest,
    MeResponse,
    ProjectCreate,
    ProjectRead,
    RunCreate,
    RunRead,
    TokenResponse,
    UiCaseCreate,
    UiCaseRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.queue import enqueue_run


router = APIRouter()

# 项目与环境：接口用例和 UI 用例都依赖项目，所以权限归到 projects。
@router.get("/projects", response_model=list[ProjectRead])
def list_projects(_: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id.desc()).all()


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in payload.model_dump().items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
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
    return db.query(Environment).order_by(Environment.id.desc()).all()


@router.post("/environments", response_model=EnvironmentRead)
def create_environment(payload: EnvironmentCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    validate_public_http_url(payload.base_url)
    environment = Environment(**payload.model_dump())
    db.add(environment)
    db.commit()
    db.refresh(environment)
    return environment
