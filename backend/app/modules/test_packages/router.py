"""Upload the latest test package and expose a stable public download channel."""

import secrets
from hmac import compare_digest
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import TestPackage
from app.modules.file_transfer.service import clean_filename, save_upload

router = APIRouter(tags=["测试包安装"])
ALLOWED_EXTENSIONS = {".apk", ".ipa", ".zip", ".aab"}


def package_dir() -> Path:
    path = Path(get_settings().test_package_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def package_data(item: TestPackage) -> dict:
    base = get_settings().public_base_url.rstrip("/")
    return {
        "id": item.id,
        "channel": item.channel,
        "original_name": item.original_name,
        "content_type": item.content_type,
        "size_bytes": item.size_bytes,
        "version": item.version,
        "notes": item.notes,
        "upload_count": item.upload_count,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "share_url": f"{base}/?testPackage=latest",
        "download_url": f"{base}/api/test-packages/public/latest/download",
    }


def save_latest(file: UploadFile, version: str, notes: str, db: Session) -> dict:
    """Store one package and atomically make it the stable latest download."""
    original_name = clean_filename(file.filename or "package")
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "只允许上传 APK、IPA、AAB 或 ZIP 测试包")
    stored_name = f"{secrets.token_urlsafe(18)}{extension}"
    destination = package_dir() / stored_name
    size = save_upload(file, destination, get_settings().test_package_max_mb * 1024 * 1024)
    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(400, "测试包不能为空")
    item = db.query(TestPackage).filter(TestPackage.channel == "latest").first()
    old_name = item.stored_name if item else None
    try:
        if item is None:
            item = TestPackage(channel="latest", original_name=original_name, stored_name=stored_name,
                content_type=file.content_type, size_bytes=size, version=version.strip() or None,
                notes=notes.strip() or None, upload_count=1)
            db.add(item)
        else:
            item.original_name = original_name
            item.stored_name = stored_name
            item.content_type = file.content_type
            item.size_bytes = size
            item.version = version.strip() or None
            item.notes = notes.strip() or None
            item.upload_count += 1
        db.commit(); db.refresh(item)
    except Exception:
        db.rollback(); destination.unlink(missing_ok=True); raise
    if old_name and old_name != stored_name:
        (package_dir() / old_name).unlink(missing_ok=True)
    return package_data(item)


@router.get("/test-packages/latest")
def latest_package(_: AuthContext = Depends(require_menu("test_packages")), db: Session = Depends(get_db)):
    item = db.query(TestPackage).filter(TestPackage.channel == "latest").first()
    return package_data(item) if item else None


@router.post("/test-packages/latest")
def upload_latest_package(
    file: UploadFile = File(...),
    version: str = Form(default=""),
    notes: str = Form(default=""),
    _: AuthContext = Depends(require_menu("test_packages")),
    db: Session = Depends(get_db),
):
    return save_latest(file, version, notes, db)


@router.post("/test-packages/internal/jenkins/latest")
def publish_from_jenkins(
    file: UploadFile = File(...),
    version: str = Form(default=""),
    notes: str = Form(default=""),
    x_jenkins_token: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Accept an APK only from Jenkins using a dedicated server-side token."""
    expected = get_settings().jenkins_publish_token or ""
    if not expected or not compare_digest(x_jenkins_token, expected):
        raise HTTPException(403, "Jenkins 发布凭证无效")
    return save_latest(file, version, notes, db)


@router.get("/test-packages/public/latest")
def public_latest_package(db: Session = Depends(get_db)):
    item = db.query(TestPackage).filter(TestPackage.channel == "latest").first()
    if item is None:
        raise HTTPException(404, "当前还没有可下载的测试包")
    return package_data(item)


@router.get("/test-packages/public/latest/download")
def download_latest_package(db: Session = Depends(get_db)):
    item = db.query(TestPackage).filter(TestPackage.channel == "latest").first()
    if item is None:
        raise HTTPException(404, "当前还没有可下载的测试包")
    path = package_dir() / item.stored_name
    if not path.exists():
        raise HTTPException(404, "测试包文件不存在")
    return FileResponse(path, media_type="application/octet-stream", filename=item.original_name,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "X-Content-Type-Options": "nosniff"})
