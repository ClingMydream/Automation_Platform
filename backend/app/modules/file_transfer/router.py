"""Temporary file transfer routes for desktop upload and mobile token access."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import FileTransfer
from app.modules.file_transfer.service import (
    cleanup_expired,
    create_transfer,
    file_response,
    transfer_dir,
)


router = APIRouter(tags=["文件快传"])

# 文件快传：后台上传文件生成二维码，公开 token 页面用于手机下载/回传。
@router.get(
    "/file-transfers",
    summary="查询临时文件列表",
    description="登录用户查看未过期的临时文件，接口会顺便清理已经过期的文件记录。",
)
def list_file_transfers(_: AuthContext = Depends(require_menu("files")), db: Session = Depends(get_db)):
    """List non-expired temporary file transfers."""
    # Cleanup runs opportunistically so expired files disappear without a separate scheduler.
    cleanup_expired(db)
    items = db.query(FileTransfer).order_by(FileTransfer.id.desc()).limit(100).all()
    return [file_response(item) for item in items]


@router.post(
    "/file-transfers",
    summary="上传临时文件",
    description=(
        "从电脑端上传临时文件并生成公开 token，手机扫码后可下载。"
        "请控制文件大小和上传频率，避免占满服务器磁盘。"
    ),
)
def upload_file_transfer(
    file: UploadFile = File(...),
    expires_hours: int = Query(default=24, ge=1, le=168),
    _: AuthContext = Depends(require_menu("files")),
    db: Session = Depends(get_db),
):
    """Upload a temporary file from the admin console."""
    cleanup_expired(db)
    item = create_transfer(
        db,
        file,
        source="admin",
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )
    return file_response(item)


@router.delete(
    "/file-transfers/{transfer_id}",
    summary="删除临时文件",
    description="删除临时文件的数据库记录和服务器磁盘文件。",
)
def delete_file_transfer(transfer_id: int, _: AuthContext = Depends(require_menu("files")), db: Session = Depends(get_db)):
    """Delete a temporary transfer file and database record."""
    item = db.get(FileTransfer, transfer_id)
    if item is None:
        raise HTTPException(status_code=404, detail="File not found")
    # Remove the physical file before deleting the metadata row.
    path = transfer_dir() / item.stored_name
    if path.exists():
        path.unlink()
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.get(
    "/file-transfers/public/{token}",
    summary="公开查询临时文件信息",
    description="手机扫码后无需登录，通过公开 token 查询临时文件名称、大小、类型和下载地址。",
)
def get_public_file_transfer(token: str, db: Session = Depends(get_db)):
    """Read temporary file metadata by public token."""
    cleanup_expired(db)
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    return file_response(item)


@router.get(
    "/file-transfers/public/{token}/download",
    summary="公开下载临时文件",
    description="手机端无需登录，通过 token 下载文件；压测时应限制文件大小和并发，防止占满带宽。",
)
def download_public_file_transfer(token: str, db: Session = Depends(get_db)):
    """Download a temporary file by public token."""
    cleanup_expired(db)
    # Public token endpoints intentionally skip login so phones can scan and download directly.
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    path = transfer_dir() / item.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return FileResponse(
        path=path,
        media_type=item.content_type or "application/octet-stream",
        filename=item.original_name,
    )


@router.get(
    "/file-transfers/public/{token}/preview",
    summary="公开预览图片或视频",
    description="手机端无需登录预览图片或视频类型文件，非图片/视频会返回 415。",
)
def preview_public_file_transfer(token: str, db: Session = Depends(get_db)):
    """Preview an image or video transfer by public token."""
    cleanup_expired(db)
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    content_type = item.content_type or "application/octet-stream"
    # Inline preview is limited to browser-safe image and video content.
    if not (content_type.startswith("image/") or content_type.startswith("video/")):
        raise HTTPException(status_code=415, detail="Preview only supports images and videos")
    path = transfer_dir() / item.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return FileResponse(
        path=path,
        media_type=content_type,
        filename=item.original_name,
        content_disposition_type="inline",
    )


@router.post(
    "/file-transfers/public/{token}/upload",
    summary="手机端回传文件",
    description="手机扫码进入公开页面后上传文件回传到平台，生成同一过期时间下的新临时文件。",
)
def upload_public_file_transfer(token: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a return file from the public mobile page."""
    cleanup_expired(db)
    parent = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if parent is None:
        raise HTTPException(status_code=404, detail="Transfer link not found or expired")
    item = create_transfer(
        db,
        file,
        source="public",
        parent_token=token,
        expires_at=parent.expires_at,
    )
    return file_response(item)
