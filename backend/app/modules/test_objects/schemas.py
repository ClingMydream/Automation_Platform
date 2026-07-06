"""Request and response schemas for the test object module."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


TestObjectType = Literal["api", "page", "app", "mini_program", "script", "performance", "device", "environment"]


class TestObjectCreate(BaseModel):
    """Request body for creating or updating a platform test object."""
    code: str = Field(min_length=2, max_length=80, description="测试对象唯一编号", examples=["API-LOGIN-001"])
    name: str = Field(min_length=1, max_length=160, description="测试对象名称", examples=["登录接口"])
    object_type: TestObjectType = Field(description="测试对象类型", examples=["api"])
    project_id: int | None = Field(default=None, description="可选所属项目 ID", examples=[1])
    business_module: str | None = Field(default=None, max_length=120, description="所属业务模块", examples=["用户中心"])
    tags: list[str] = Field(default_factory=list, description="标签列表", examples=[["登录", "冒烟", "核心链路"]])
    is_active: bool = Field(default=True, description="是否启用该测试对象")
    description: str | None = Field(default=None, description="对象说明、测试范围或注意事项")

    @field_validator("code", "name", "business_module", "description", mode="before")
    @classmethod
    def trim_text(cls, value):
        """Trim text input so list filters and unique checks stay predictable."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value):
        """Accept list or comma-separated text and return clean unique tags."""
        if value is None:
            return []
        if isinstance(value, str):
            value = value.replace("，", ",").split(",")
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned


class TestObjectRead(TestObjectCreate):
    """Response body for test object rows."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True
