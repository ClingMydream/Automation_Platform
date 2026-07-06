"""Request and response schemas for result center APIs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ResultStatus = Literal["passed", "failed", "error", "skipped"]


class TestResultCreate(BaseModel):
    """One result item uploaded by platform automation or external scripts."""
    test_object_id: int | None = Field(default=None, description="关联测试对象 ID")
    case_type: str | None = Field(default=None, description="旧用例类型，例如 api 或 ui")
    case_id: int | None = Field(default=None, description="旧用例 ID")
    result_type: str = Field(default="api", description="结果类型：api、ui、performance、compatibility、script")
    status: ResultStatus = Field(description="执行结果")
    duration_ms: int | None = Field(default=None, ge=0, description="耗时，单位毫秒")
    request_data: dict[str, Any] = Field(default_factory=dict, description="请求内容或执行输入")
    response_data: dict[str, Any] = Field(default_factory=dict, description="响应内容或执行输出")
    assertions: list[dict[str, Any]] = Field(default_factory=list, description="断言明细")
    metrics: dict[str, Any] = Field(default_factory=dict, description="性能指标，例如 avg、p95、p99、error_rate")
    logs: str | None = Field(default=None, description="执行日志")
    error: str | None = Field(default=None, description="错误信息")
    failure_category: str | None = Field(default=None, description="失败分类，例如 assertion、timeout、environment")
    environment_id: int | None = Field(default=None, description="执行环境 ID")
    device_info: dict[str, Any] = Field(default_factory=dict, description="设备信息")
    started_at: datetime | None = Field(default=None, description="开始时间")
    finished_at: datetime | None = Field(default=None, description="结束时间")


class ResultBatchUpload(BaseModel):
    """Batch result upload request used by CI, pytest, Playwright, or JMeter adapters."""
    batch_no: str | None = Field(default=None, description="已有执行批次号；为空时自动创建")
    trigger_type: str = Field(default="api", description="触发方式")
    environment_id: int | None = Field(default=None, description="执行环境 ID")
    summary: dict[str, Any] = Field(default_factory=dict, description="批次摘要")
    results: list[TestResultCreate] = Field(default_factory=list, description="结果列表")


class TestResultRead(TestResultCreate):
    """Response body for result center rows."""
    id: int
    batch_id: int | None
    task_id: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class AttachmentRead(BaseModel):
    """Response body for uploaded result attachments."""
    id: int
    result_id: int | None
    batch_id: int | None
    attachment_type: str
    original_name: str
    stored_name: str
    content_type: str | None
    size_bytes: int
    created_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True
