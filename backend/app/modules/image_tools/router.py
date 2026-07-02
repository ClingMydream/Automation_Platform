"""Image generation, crop, resize, annotation, and format-conversion routes."""

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

# 图片工具：后端负责真实图片处理，前端只负责收集参数和下载结果。
@router.get("/image-tools/formats")
def list_image_formats(_: AuthContext = Depends(require_menu("images"))):
    """Return image formats supported by the platform."""
    return [
        {
            "value": key,
            "label": value["label"],
            "mime": value["mime"],
            "extension": value["ext"],
        }
        for key, value in IMAGE_FORMATS.items()
    ]


@router.post("/image-tools/generate")
def generate_image(payload: ImageGenerateRequest, _: AuthContext = Depends(require_menu("images"))):
    """Generate an image from size, color, text, and format settings."""
    config = _image_format(payload.format)
    # Colors are sanitized so invalid form values cannot break Pillow or SVG generation.
    background = _safe_color(payload.background_color, "#ffffff")
    text_color = _safe_color(payload.text_color, "#17202a")
    filename = f"generated-{payload.width}x{payload.height}"
    if config["key"] == "svg":
        # SVG generation stays text-based instead of creating a raster image first.
        svg = _svg_response(payload.width, payload.height, background, payload.text, text_color, payload.font_size)
        return Response(
            content=svg,
            media_type=config["mime"],
            headers={"Content-Disposition": f'attachment; filename="{filename}.{config["ext"]}"'},
        )
    image = Image.new("RGB", (payload.width, payload.height), background)
    _draw_center_text(image, payload.text, text_color, payload.font_size)
    return _serialize_image(image, payload.format, payload.quality, payload.max_kb, filename)


@router.post("/image-tools/process")
def process_image(
    file: UploadFile = File(...),
    crop_x: int = Form(default=0, ge=0),
    crop_y: int = Form(default=0, ge=0),
    crop_width: int | None = Form(default=None, ge=1),
    crop_height: int | None = Form(default=None, ge=1),
    output_width: int | None = Form(default=None, ge=32, le=8192),
    output_height: int | None = Form(default=None, ge=32, le=8192),
    text: str = Form(default=""),
    text_color: str = Form(default="#17202a"),
    font_size: int = Form(default=48, ge=8, le=512),
    format: str = Form(default="png"),
    quality: int = Form(default=92, ge=1, le=100),
    max_kb: int | None = Form(default=None, ge=10, le=1024 * 20),
    _: AuthContext = Depends(require_menu("images")),
):
    """Crop, resize, annotate, and convert an uploaded image."""
    settings = get_settings()
    # Reuse the file-transfer size setting so image uploads share the same server limit.
    max_bytes = settings.file_transfer_max_mb * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Image is too large")
    if not content:
        raise HTTPException(status_code=400, detail="Image is empty")
    try:
        # exif_transpose fixes phone photos that store rotation in EXIF metadata.
        with Image.open(BytesIO(content)) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGBA")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unsupported or broken image file") from exc

    # Clamp crop coordinates inside the actual image before cropping.
    left = min(crop_x, image.width - 1)
    top = min(crop_y, image.height - 1)
    right = min(image.width, left + (crop_width or image.width - left))
    bottom = min(image.height, top + (crop_height or image.height - top))
    if right <= left or bottom <= top:
        raise HTTPException(status_code=400, detail="Invalid crop area")
    image = image.crop((left, top, right, bottom))

    if output_width or output_height:
        # Preserve aspect ratio when only one output dimension is provided.
        width = output_width or round(image.width * (output_height / image.height))
        height = output_height or round(image.height * (output_width / image.width))
        image = image.resize((width, height), Image.Resampling.LANCZOS)

    _draw_center_text(image, text, _safe_color(text_color, "#17202a"), font_size)
    original_name = Path(file.filename or "image").stem[:80] or "image"
    filename = f"{original_name}-processed"
    return _serialize_image(image, format, quality, max_kb, filename)
