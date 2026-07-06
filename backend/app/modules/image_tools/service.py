"""Image tool service helpers for format validation, drawing, and serialization."""

from base64 import b64encode
from html import escape
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont


IMAGE_FORMATS = {
    "png": {"label": "PNG", "mime": "image/png", "ext": "png", "pillow": "PNG"},
    "jpeg": {"label": "JPEG", "mime": "image/jpeg", "ext": "jpg", "pillow": "JPEG"},
    "webp": {"label": "WEBP", "mime": "image/webp", "ext": "webp", "pillow": "WEBP"},
    "gif": {"label": "GIF", "mime": "image/gif", "ext": "gif", "pillow": "GIF"},
    "bmp": {"label": "BMP", "mime": "image/bmp", "ext": "bmp", "pillow": "BMP"},
    "tiff": {"label": "TIFF", "mime": "image/tiff", "ext": "tiff", "pillow": "TIFF"},
    "svg": {"label": "SVG", "mime": "image/svg+xml", "ext": "svg", "pillow": None},
}


def image_format(format_name: str) -> dict:
    """Validate and return supported image format metadata."""
    key = (format_name or "png").lower().strip()
    if key == "jpg":
        key = "jpeg"
    config = IMAGE_FORMATS.get(key)
    if config is None:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    return {**config, "key": key}


def safe_color(value: str, fallback: str) -> str:
    """Validate a hex color and fall back when it is invalid."""
    value = (value or "").strip()
    if value.startswith("#") and len(value) in {4, 7}:
        return value
    return fallback


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font for drawing image text, falling back to Pillow default."""
    # Try common Linux container fonts first, then Windows fonts for local development.
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


def draw_center_text(image: Image.Image, text: str, color: str, font_size: int) -> None:
    """Draw multi-line text centered inside an image."""
    if not text:
        return
    # Measure every line first so the whole text block can be vertically centered.
    draw = ImageDraw.Draw(image)
    selected_font = font(font_size)
    lines = text.splitlines() or [text]
    spacing = max(6, font_size // 4)
    boxes = [draw.textbbox((0, 0), line, font=selected_font) for line in lines]
    widths = [box[2] - box[0] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    total_height = sum(heights) + spacing * (len(lines) - 1)
    y = max(0, (image.height - total_height) / 2)
    for line, width, height in zip(lines, widths, heights):
        x = max(0, (image.width - width) / 2)
        draw.text((x, y), line, fill=color, font=selected_font)
        y += height + spacing


def svg_response(width: int, height: int, background: str, text: str, text_color: str, font_size: int) -> bytes:
    """Generate an SVG text image response."""
    lines = text.splitlines() or [""]
    # Build one centered text node per line instead of rasterizing text into pixels.
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


def image_as_svg(image: Image.Image, filename: str) -> bytes:
    """Wrap a raster image in an SVG response."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    data = b64encode(buffer.getvalue()).decode("ascii")
    name = escape(filename)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{image.width}" height="{image.height}" '
        f'viewBox="0 0 {image.width} {image.height}">'
        f"<title>{name}</title>"
        f'<image width="{image.width}" height="{image.height}" href="data:image/png;base64,{data}"/></svg>'
    ).encode("utf-8")


def serialize_image(image: Image.Image, format_name: str, quality: int, max_kb: int | None, filename: str) -> Response:
    """Serialize an image with requested format, quality, and size limit."""
    config = image_format(format_name)
    # SVG output wraps the raster canvas so the frontend can download a vector-compatible file.
    if config["key"] == "svg":
        payload = image_as_svg(image, filename)
    else:
        save_image = image
        # JPEG and BMP do not support alpha, so transparent pixels are flattened onto white.
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
        # JPEG/WEBP can be iteratively compressed toward a target max KB size.
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
