"""Image tool request schemas."""

from pydantic import BaseModel, Field


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
