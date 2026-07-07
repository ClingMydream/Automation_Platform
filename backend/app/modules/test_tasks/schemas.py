"""Request and response schemas for test task and execution batch APIs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


TaskType = Literal["api", "ui", "performance", "compatibility", "script", "mixed"]
TriggerType = Literal["manual", "schedule", "ci", "api"]


class TestTaskCreate(BaseModel):
    """Request body for creating or updating a test task."""
    code: str = Field(min_length=2, max_length=80, description="任务唯一编号", examples=["TASK-SMOKE-001"])
    name: str = Field(min_length=1, max_length=160, description="任务名称", examples=["冒烟自动化任务"])
    task_type: TaskType = Field(default="api", description="任务类型")
    project_id: int | None = Field(default=None, description="可选所属项目 ID")
    environment_id: int | None = Field(default=None, description="可选执行环境 ID")
    test_object_id: int | None = Field(default=None, description="可选关联测试对象 ID")
    trigger_type: TriggerType = Field(default="manual", description="默认触发方式")
    runner_type: str = Field(default="platform", max_length=40, description="执行来源：platform、pytest、playwright、jmeter、ci 等")
    retry_count: int = Field(default=0, ge=0, le=10, description="失败重试次数")
    schedule_cron: str | None = Field(default=None, max_length=120, description="定时任务 cron 表达式，worker 支持基础 5 段 cron 调度")
    owner: str | None = Field(default=None, max_length=120, description="负责人")
    is_active: bool = Field(default=True, description="是否启用")
    config: dict[str, Any] = Field(default_factory=dict, description="任务配置 JSON，例如用例集合、JMeter 参数、脚本路径")
    description: str | None = Field(default=None, description="任务说明")

    @field_validator("code", "name", "runner_type", "schedule_cron", "owner", "description", mode="before")
    @classmethod
    def trim_text(cls, value):
        """Trim text fields before validation and persistence."""
        if isinstance(value, str):
            return value.strip()
        return value


class TestTaskRead(TestTaskCreate):
    """Response body for test task rows."""
    id: int
    last_status: str | None = None
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class TaskRunRequest(BaseModel):
    """Request body for starting one execution batch from a task."""
    trigger_type: TriggerType = Field(default="manual", description="本次触发方式")
    environment_id: int | None = Field(default=None, description="本次执行环境 ID；为空则使用任务默认环境")
    summary: dict[str, Any] = Field(default_factory=dict, description="执行批次附加说明")


class ExecutionBatchRead(BaseModel):
    """Response body for execution batch details."""
    id: int
    batch_no: str
    task_id: int | None
    trigger_type: str
    environment_id: int | None
    status: str
    total_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    duration_ms: int | None
    started_at: datetime | None
    finished_at: datetime | None
    summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True
