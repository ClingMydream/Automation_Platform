import secrets
import shutil
from base64 import b64encode
from datetime import datetime, timedelta
from html import escape
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.menu import ADMIN_MENU_KEYS, ALL_MENU_KEYS
from app.models.entities import ApiCase, AppUser, FileTransfer, TestRun, UiCase


IMAGE_FORMATS = {
    "png": {"label": "PNG", "mime": "image/png", "ext": "png", "pillow": "PNG"},
    "jpeg": {"label": "JPEG", "mime": "image/jpeg", "ext": "jpg", "pillow": "JPEG"},
    "webp": {"label": "WEBP", "mime": "image/webp", "ext": "webp", "pillow": "WEBP"},
    "gif": {"label": "GIF", "mime": "image/gif", "ext": "gif", "pillow": "GIF"},
    "bmp": {"label": "BMP", "mime": "image/bmp", "ext": "bmp", "pillow": "BMP"},
    "tiff": {"label": "TIFF", "mime": "image/tiff", "ext": "tiff", "pillow": "TIFF"},
    "svg": {"label": "SVG", "mime": "image/svg+xml", "ext": "svg", "pillow": None},
}


class ImageGenerateRequest(BaseModel):
    """Define request fields for generated images."""
    width: int = Field(default=1080, ge=32, le=8192)
    height: int = Field(default=1080, ge=32, le=8192)
    background_color: str = "#ffffff"
    text: str = ""
    text_color: str = "#17202a"
    font_size: int = Field(default=72, ge=8, le=512)
    format: str = "png"
    quality: int = Field(default=92, ge=1, le=100)
    max_kb: int | None = Field(default=None, ge=10, le=1024 * 20)


def _transfer_dir() -> Path:
    """Return and create the directory used for temporary transfer files."""
    settings = get_settings()
    path = Path(settings.file_transfer_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clean_filename(name: str) -> str:
    """Sanitize uploaded file names before storing them."""
    cleaned = Path(name or "file").name.strip().replace("\x00", "")
    return cleaned[:255] or "file"


def _normalize_menu_permissions(values: list[str]) -> list[str]:
    """Filter and de-duplicate menu permission keys."""
    seen = []
    for value in values or []:
        if value in ALL_MENU_KEYS and value != "users" and value not in seen:
            seen.append(value)
    if ("api" in seen or "ui" in seen) and "projects" not in seen:
        seen.insert(0, "projects")
    return seen


def _user_response(user: AppUser) -> dict:
    """Convert a user model into the frontend response shape."""
    permissions = ADMIN_MENU_KEYS if user.is_admin else list(user.menu_permissions or [])
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "menu_permissions": permissions,
        "created_at": user.created_at,
    }


def _case_name_for_run(db: Session, run: TestRun) -> str:
    """Resolve the display case name for a run."""
    model = ApiCase if run.case_type == "api" else UiCase
    case = db.get(model, run.case_id)
    return case.name if case else f"已删除用例 #{run.case_id}"


def _report_summary(run: TestRun, case_name: str) -> dict:
    """Convert a run into a report-list summary object."""
    report = run.report or {}
    checks = report.get("checks") or []
    events = report.get("events") or []
    screenshots = report.get("screenshots") or []
    return {
        "id": run.id,
        "case_type": run.case_type,
        "case_id": run.case_id,
        "case_name": case_name,
        "status": run.status,
        "passed": report.get("passed") if report else run.status == "passed",
        "duration_ms": run.duration_ms,
        "logs": run.logs,
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "check_count": len(checks),
        "event_count": len(events),
        "screenshot_count": len(screenshots),
        "summary": {
            "request": report.get("request"),
            "response_status": (report.get("response") or {}).get("status_code"),
            "current_step": report.get("current_step"),
            "total_steps": report.get("total_steps"),
        },
        "report": report,
    }


def _image_format(format_name: str) -> dict:
    """Validate and return supported image format metadata."""
    key = (format_name or "png").lower().strip()
    if key == "jpg":
        key = "jpeg"
    config = IMAGE_FORMATS.get(key)
    if config is None:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    return {**config, "key": key}


def _safe_color(value: str, fallback: str) -> str:
    """Validate a hex color and fall back when it is invalid."""
    value = (value or "").strip()
    if value.startswith("#") and len(value) in {4, 7}:
        return value
    return fallback


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font for drawing image text, falling back to Pillow default."""
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default(size=size)


def _draw_center_text(image: Image.Image, text: str, color: str, font_size: int) -> None:
    """Draw multi-line text centered inside an image."""
    if not text:
        return
    draw = ImageDraw.Draw(image)
    font = _font(font_size)
    lines = text.splitlines() or [text]
    spacing = max(6, font_size // 4)
    boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    widths = [box[2] - box[0] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    total_height = sum(heights) + spacing * (len(lines) - 1)
    y = max(0, (image.height - total_height) / 2)
    for line, width, height in zip(lines, widths, heights):
        x = max(0, (image.width - width) / 2)
        draw.text((x, y), line, fill=color, font=font)
        y += height + spacing


def _svg_response(width: int, height: int, background: str, text: str, text_color: str, font_size: int) -> bytes:
    """Generate an SVG text image response."""
    lines = text.splitlines() or [""]
    spacing = max(8, font_size // 3)
    total_height = font_size * len(lines) + spacing * (len(lines) - 1)
    first_y = height / 2 - total_height / 2 + font_size
    text_nodes = []
    for index, line in enumerate(lines):
        y = first_y + index * (font_size + spacing)
        text_nodes.append(
            f'<text x="50%" y="{y:.1f}" text-anchor="middle" font-family="Arial, Noto Sans CJK SC, sans-serif" '
            f'font-size="{font_size}" fill="{escape(text_color)}">{escape(line)}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="{escape(background)}"/>'
        f'{"".join(text_nodes)}</svg>'
    )
    return svg.encode("utf-8")


def _image_as_svg(image: Image.Image, filename: str) -> bytes:
    """Wrap a raster image in an SVG response."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    data = b64encode(buffer.getvalue()).decode("ascii")
    name = escape(filename)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{image.width}" height="{image.height}" '
        f'viewBox="0 0 {image.width} {image.height}">'
        f'<title>{name}</title>'
        f'<image width="{image.width}" height="{image.height}" href="data:image/png;base64,{data}"/></svg>'
    ).encode("utf-8")


def _serialize_image(image: Image.Image, format_name: str, quality: int, max_kb: int | None, filename: str) -> Response:
    """Serialize an image with requested format, quality, and size limit."""
    config = _image_format(format_name)
    if config["key"] == "svg":
        payload = _image_as_svg(image, filename)
    else:
        save_image = image
        if config["key"] in {"jpeg", "bmp"} and save_image.mode in {"RGBA", "LA", "P"}:
            background = Image.new("RGB", save_image.size, "#ffffff")
            if save_image.mode == "P":
                save_image = save_image.convert("RGBA")
            background.paste(save_image, mask=save_image.split()[-1] if save_image.mode in {"RGBA", "LA"} else None)
            save_image = background
        elif config["key"] == "gif":
            save_image = save_image.convert("P", palette=Image.Palette.ADAPTIVE)
        elif save_image.mode not in {"RGB", "RGBA"}:
            save_image = save_image.convert("RGBA")

        payload = b""
        quality_values = [quality]
        if max_kb and config["key"] in {"jpeg", "webp"}:
            quality_values = list(range(quality, 19, -8))
        for current_quality in quality_values:
            buffer = BytesIO()
            kwargs = {"format": config["pillow"]}
            if config["key"] in {"jpeg", "webp"}:
                kwargs.update({"quality": current_quality, "optimize": True})
            elif config["key"] == "png":
                kwargs.update({"optimize": True})
            save_image.save(buffer, **kwargs)
            payload = buffer.getvalue()
            if not max_kb or len(payload) <= max_kb * 1024:
                break

    headers = {"Content-Disposition": f'attachment; filename="{filename}.{config["ext"]}"'}
    return Response(content=payload, media_type=config["mime"], headers=headers)


def _file_response(item: FileTransfer) -> dict:
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


def _cleanup_expired(db: Session) -> None:
    """Delete expired transfer files and records."""
    now = datetime.utcnow()
    expired = db.query(FileTransfer).filter(FileTransfer.expires_at <= now).all()
    if not expired:
        return
    directory = _transfer_dir()
    for item in expired:
        path = directory / item.stored_name
        if path.exists():
            path.unlink()
        db.delete(item)
    db.commit()


def _save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> int:
    """Save an uploaded file while enforcing the maximum size."""
    size = 0
    with destination.open("wb") as output:
        while True:
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


def _create_transfer(
    db: Session,
    upload: UploadFile,
    *,
    source: str,
    parent_token: str | None = None,
    expires_at: datetime | None = None,
) -> FileTransfer:
    """Create a temporary file transfer record and store its upload."""
    settings = get_settings()
    max_bytes = settings.file_transfer_max_mb * 1024 * 1024
    token = secrets.token_urlsafe(24)
    original_name = _clean_filename(upload.filename or "file")
    stored_name = f"{token}-{original_name}"
    destination = _transfer_dir() / stored_name
    size = _save_upload(upload, destination, max_bytes)
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
