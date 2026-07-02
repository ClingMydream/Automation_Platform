"""User management API routes for administrators."""

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

# 用户管理：管理员专属，用来维护登录账号和菜单权限。
@router.get("/menu-options")
def menu_options(_: AuthContext = Depends(verify_admin)):
    """Return menu options that administrators can assign to users."""
    return MENU_OPTIONS


@router.get("/users", response_model=list[UserRead])
def list_users(_: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    """List all login users for administrator management."""
    ensure_admin_user(db)
    users = db.query(AppUser).order_by(AppUser.is_admin.desc(), AppUser.id.desc()).all()
    return [_user_response(user) for user in users]


@router.post("/users", response_model=UserRead)
def create_user(payload: UserCreate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    """Create a non-admin login user with menu permissions."""
    username = payload.username.strip()
    # The bootstrap administrator name is reserved so a normal user cannot shadow it.
    if username == get_settings().admin_username:
        raise HTTPException(status_code=400, detail="This username is reserved")
    if db.query(AppUser).filter(AppUser.username == username).first() is not None:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = AppUser(
        username=username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        is_admin=False,
        is_active=payload.is_active,
        menu_permissions=_normalize_menu_permissions(payload.menu_permissions),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    """Update a user password, active flag, and menu permissions."""
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        # Admin permissions are fixed to the full platform and cannot be reduced from the UI.
        user.display_name = payload.display_name or user.display_name
        user.is_active = True
        user.menu_permissions = ADMIN_MENU_KEYS
    else:
        user.display_name = payload.display_name
        user.is_active = payload.is_active
        user.menu_permissions = _normalize_menu_permissions(payload.menu_permissions)
    if payload.password:
        # Password changes are optional; leaving it empty preserves the old hash.
        user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    """Delete a non-admin login user."""
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Admin user cannot be deleted")
    db.delete(user)
    db.commit()
    return {"status": "ok"}
