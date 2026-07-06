"""Schemas for problem diagnosis records and generated investigation advice."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Severity = Literal["low", "medium", "high", "critical"]
FindingStatus = Literal["open", "investigating", "fixed", "ignored"]


class ProblemFindingCreate(BaseModel):
    """Request body for creating or updating one diagnosis record."""
    result_id: int | None = Field(default=None, description="关联的测试结果 ID")
    batch_id: int | None = Field(default=None, description="关联的执行批次 ID")
    test_object_id: int | None = Field(default=None, description="关联的测试对象 ID")
    title: str = Field(min_length=1, max_length=200, description="问题标题")
    severity: Severity = Field(default="medium", description="严重级别")
    status: FindingStatus = Field(default="open", description="处理状态")
    failure_category: str | None = Field(default=None, max_length=80, description="失败分类")
    root_cause: str | None = Field(default=None, description="根因分析")
    reproduce_steps: str | None = Field(default=None, description="复现步骤")
    evidence: dict[str, Any] = Field(default_factory=dict, description="定位证据 JSON")
    owner: str | None = Field(default=None, max_length=120, description="责任人")
    suggestion: str | None = Field(default=None, description="处理建议")
    source: str = Field(default="manual", max_length=40, description="来源：manual 或 generated")

    @field_validator("title", "failure_category", "root_cause", "reproduce_steps", "owner", "suggestion", "source", mode="before")
    @classmethod
    def trim_text(cls, value):
        """Trim optional text input before it is stored."""
        if isinstance(value, str):
            return value.strip()
        return value


class ProblemFindingRead(ProblemFindingCreate):
    """Response body for diagnosis records."""
    id: int
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read values from SQLAlchemy models."""
        from_attributes = True
