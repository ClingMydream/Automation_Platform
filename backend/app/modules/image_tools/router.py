"""Image generation, crop, resize, annotation, and format-conversion routes."""

from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps

from app.core.auth import AuthContext, require_menu
from app.core.config import get_settings
from app.modules.image_tools.schemas import ImageGenerateRequest
from app.modules.image_tools.service import (
    IMAGE_FORMATS,
    draw_center_text,
    image_format,
    safe_color,
    serialize_image,
    svg_response,
)


router = APIRouter(tags=["图片工具"])

# 图片工具：后端负责真实图片处理，前端只负责收集参数和下载结果。
@router.get(
    "/image-tools/formats",
    summary="查询支持的图片格式",
    description="返回平台支持生成和转换的常用图片格式，前端用它渲染格式选项。",
)
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


@router.post(
    "/image-tools/generate",
    summary="自定义生成图片",
    description="根据宽高、背景色、文案、字体大小、输出格式和压缩大小生成图片文件。",
)
def generate_image(payload: ImageGenerateRequest, _: AuthContext = Depends(require_menu("images"))):
    """Generate an image from size, color, text, and format settings."""
    config = image_format(payload.format)
    # Colors are sanitized so invalid form values cannot break Pillow or SVG generation.
    background = safe_color(payload.background_color, "#ffffff")
    text_color = safe_color(payload.text_color, "#17202a")
    filename = f"generated-{payload.width}x{payload.height}"
    if config["key"] == "svg":
        # SVG generation stays text-based instead of creating a raster image first.
        svg = svg_response(payload.width, payload.height, background, payload.text, text_color, payload.font_size)
        return Response(
            content=svg,
            media_type=config["mime"],
            headers={"Content-Disposition": f'attachment; filename="{filename}.{config["ext"]}"'},
        )
    image = Image.new("RGB", (payload.width, payload.height), background)
    draw_center_text(image, payload.text, text_color, payload.font_size)
    return serialize_image(image, payload.format, payload.quality, payload.max_kb, filename)


@router.post(
    "/image-tools/process",
    summary="处理上传图片",
    description="上传图片后进行裁剪、缩放、文案叠加、格式转换和可选压缩。",
)
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

    draw_center_text(image, text, safe_color(text_color, "#17202a"), font_size)
    original_name = Path(file.filename or "image").stem[:80] or "image"
    filename = f"{original_name}-processed"
    return serialize_image(image, format, quality, max_kb, filename)
