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

# 文件快传：后台上传文件生成二维码，公开 token 页面用于手机下载/回传。
@router.get("/file-transfers")
def list_file_transfers(_: AuthContext = Depends(require_menu("files")), db: Session = Depends(get_db)):
    """List non-expired temporary file transfers."""
    _cleanup_expired(db)
    items = db.query(FileTransfer).order_by(FileTransfer.id.desc()).limit(100).all()
    return [_file_response(item) for item in items]


@router.post("/file-transfers")
def upload_file_transfer(
    file: UploadFile = File(...),
    expires_hours: int = Query(default=24, ge=1, le=168),
    _: AuthContext = Depends(require_menu("files")),
    db: Session = Depends(get_db),
):
    """Upload a temporary file from the admin console."""
    _cleanup_expired(db)
    item = _create_transfer(
        db,
        file,
        source="admin",
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )
    return _file_response(item)


@router.delete("/file-transfers/{transfer_id}")
def delete_file_transfer(transfer_id: int, _: AuthContext = Depends(require_menu("files")), db: Session = Depends(get_db)):
    """Delete a temporary transfer file and database record."""
    item = db.get(FileTransfer, transfer_id)
    if item is None:
        raise HTTPException(status_code=404, detail="File not found")
    path = _transfer_dir() / item.stored_name
    if path.exists():
        path.unlink()
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.get("/file-transfers/public/{token}")
def get_public_file_transfer(token: str, db: Session = Depends(get_db)):
    """Read temporary file metadata by public token."""
    _cleanup_expired(db)
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    return _file_response(item)


@router.get("/file-transfers/public/{token}/download")
def download_public_file_transfer(token: str, db: Session = Depends(get_db)):
    """Download a temporary file by public token."""
    _cleanup_expired(db)
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    path = _transfer_dir() / item.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return FileResponse(
        path=path,
        media_type=item.content_type or "application/octet-stream",
        filename=item.original_name,
    )


@router.get("/file-transfers/public/{token}/preview")
def preview_public_file_transfer(token: str, db: Session = Depends(get_db)):
    """Preview an image or video transfer by public token."""
    _cleanup_expired(db)
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    content_type = item.content_type or "application/octet-stream"
    if not (content_type.startswith("image/") or content_type.startswith("video/")):
        raise HTTPException(status_code=415, detail="Preview only supports images and videos")
    path = _transfer_dir() / item.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return FileResponse(
        path=path,
        media_type=content_type,
        filename=item.original_name,
        content_disposition_type="inline",
    )


@router.post("/file-transfers/public/{token}/upload")
def upload_public_file_transfer(token: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a return file from the public mobile page."""
    _cleanup_expired(db)
    parent = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if parent is None:
        raise HTTPException(status_code=404, detail="Transfer link not found or expired")
    item = _create_transfer(
        db,
        file,
        source="public",
        parent_token=token,
        expires_at=parent.expires_at,
    )
    return _file_response(item)
