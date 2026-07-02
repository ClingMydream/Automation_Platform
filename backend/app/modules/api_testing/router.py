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

# 接口测试用例：这里只保存用例配置，真正执行由 worker 完成。
@router.get("/api-cases", response_model=list[ApiCaseRead])
def list_api_cases(_: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """List API test cases."""
    return db.query(ApiCase).order_by(ApiCase.id.desc()).all()


@router.post("/api-cases", response_model=ApiCaseRead)
def create_api_case(payload: ApiCaseCreate, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Create an API test case after validating the target URL."""
    validate_public_http_url(payload.url)
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    case = ApiCase(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.put("/api-cases/{case_id}", response_model=ApiCaseRead)
def update_api_case(case_id: int, payload: ApiCaseCreate, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Update an API test case after validating the target URL."""
    validate_public_http_url(payload.url)
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    for key, value in payload.model_dump().items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/api-cases/{case_id}")
def delete_api_case(case_id: int, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Delete an API test case and its run history."""
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    db.query(TestRun).filter(TestRun.case_type == "api", TestRun.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"status": "ok"}
