"""Image tool request schemas."""

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """Define request fields for generated images."""
    width: int = Field(default=1080, ge=32, le=8192, description="生成图片宽度，单位像素")
    height: int = Field(default=1080, ge=32, le=8192, description="生成图片高度，单位像素")
    background_color: str = Field(default="#ffffff", description="背景色，支持 #RRGGBB")
    text: str = Field(default="", description="居中文案")
    text_color: str = Field(default="#17202a", description="文案颜色，支持 #RRGGBB")
    font_size: int = Field(default=72, ge=8, le=512, description="文案字号")
    format: str = Field(default="png", description="输出格式，例如 png、jpg、webp、bmp、gif、tiff、svg")
    quality: int = Field(default=92, ge=1, le=100, description="有损格式质量")
    max_kb: int | None = Field(default=None, ge=10, le=1024 * 20, description="可选目标大小上限，单位 KB")
