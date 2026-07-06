"""File transfer service helpers for temporary uploads, cleanup, and response shaping."""

import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import FileTransfer


def transfer_dir() -> Path:
    """Return and create the directory used for temporary transfer files."""
    settings = get_settings()
    path = Path(settings.file_transfer_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_filename(name: str) -> str:
    """Sanitize uploaded file names before storing them."""
    cleaned = Path(name or "file").name.strip().replace("\x00", "")
    return cleaned[:255] or "file"


def file_response(item: FileTransfer) -> dict:
    """Convert a file transfer model into frontend URLs and metadata."""
    settings = get_settings()
    base_url = settings.public_base_url.rstrip("/")
    return {
        "id": item.id,
        "token": item.token,
        "original_name": item.original_name,
        "content_type": item.content_type,
        "size_bytes": item.size_bytes,
        "source": item.source,
        "parent_token": item.parent_token,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "expires_at": item.expires_at,
        "download_url": f"{base_url}/api/file-transfers/public/{item.token}/download",
        "preview_url": f"{base_url}/api/file-transfers/public/{item.token}/preview",
        "share_url": f"{base_url}/?transferToken={item.token}",
    }


def cleanup_expired(db: Session) -> None:
    """Delete expired transfer files and records."""
    now = datetime.utcnow()
    expired = db.query(FileTransfer).filter(FileTransfer.expires_at <= now).all()
    if not expired:
        return
    directory = transfer_dir()
    # File and database cleanup happen together so stale tokens cannot point to removed files.
    for item in expired:
        path = directory / item.stored_name
        if path.exists():
            path.unlink()
        db.delete(item)
    db.commit()


def save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> int:
    """Save an uploaded file while enforcing the maximum size."""
    size = 0
    with destination.open("wb") as output:
        while True:
            # Stream in 1 MB chunks so large files do not sit fully in memory.
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File is too large")
            output.write(chunk)
    return size


def create_transfer(
    db: Session,
    upload: UploadFile,
    *,
    source: str,
    parent_token: str | None = None,
    expires_at: datetime | None = None,
) -> FileTransfer:
    """Create a temporary file transfer record and store its upload."""
    settings = get_settings()
    # A random token is used both in the stored filename and the public share URL.
    max_bytes = settings.file_transfer_max_mb * 1024 * 1024
    token = secrets.token_urlsafe(24)
    original_name = clean_filename(upload.filename or "file")
    stored_name = f"{token}-{original_name}"
    destination = transfer_dir() / stored_name
    size = save_upload(upload, destination, max_bytes)
    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="File is empty")
    item = FileTransfer(
        token=token,
        original_name=original_name,
        stored_name=stored_name,
        content_type=upload.content_type,
        size_bytes=size,
        source=source,
        parent_token=parent_token,
        expires_at=expires_at or (datetime.utcnow() + timedelta(hours=settings.file_transfer_default_hours)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
