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

# 测试报告：从执行记录中汇总报告字段，供页面查看和导出。
@router.get("/reports")
def list_reports(_: AuthContext = Depends(require_menu("reports")), db: Session = Depends(get_db)):
    runs = db.query(TestRun).order_by(TestRun.id.desc()).limit(200).all()
    return [_report_summary(run, _case_name_for_run(db, run)) for run in runs]


@router.get("/reports/{run_id}")
def get_report(run_id: int, _: AuthContext = Depends(require_menu("reports")), db: Session = Depends(get_db)):
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_summary(run, _case_name_for_run(db, run))
