"""Request and response schemas for test datasets."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DatasetType = Literal["variables", "accounts", "data_pool"]


class TestDatasetCreate(BaseModel):
    """Request body for creating or updating reusable test data."""
    name: str = Field(min_length=1, max_length=160, description="数据集名称")
    project_id: int | None = Field(default=None, description="可选所属项目 ID")
    dataset_type: DatasetType = Field(default="variables", description="数据集类型")
    variables: dict[str, Any] = Field(default_factory=dict, description="变量字典")
    rows: list[dict[str, Any]] = Field(default_factory=list, description="参数化数据行")
    is_active: bool = Field(default=True, description="是否启用")
    description: str | None = Field(default=None, description="说明")


class TestDatasetRead(TestDatasetCreate):
    """Response body for test dataset rows."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True
