"""Schemas for API scenarios, mock rules, performance scenarios, and runners."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class ApiScenarioCreate(BaseModel):
    """Request body for API scenario orchestration."""
    code: str = Field(min_length=2, max_length=80, description="场景唯一编号")
    name: str = Field(min_length=1, max_length=160, description="场景名称")
    project_id: int | None = None
    environment_id: int | None = None
    variables: dict[str, Any] = Field(default_factory=dict, description="场景变量")
    api_case_ids: list[int] = Field(default_factory=list, description="按顺序执行的接口用例 ID")
    assertions: list[dict[str, Any]] = Field(default_factory=list, description="场景级断言")
    pre_script: str | None = Field(default=None, description="前置脚本说明或安全 DSL，当前版本只保存不执行")
    post_script: str | None = Field(default=None, description="后置脚本说明或安全 DSL，当前版本只保存不执行")
    is_active: bool = True
    description: str | None = None


class ApiScenarioRead(ApiScenarioCreate):
    """Response body for API scenarios."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read SQLAlchemy models."""
        from_attributes = True


class MockRuleCreate(BaseModel):
    """Request body for mock response rules."""
    name: str = Field(min_length=1, max_length=160)
    project_id: int | None = None
    method: HttpMethod = "GET"
    path: str = Field(min_length=1, max_length=500, examples=["/api/demo"])
    status_code: int = Field(default=200, ge=100, le=599)
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: str | None = Field(default='{"message":"mock ok"}')
    delay_ms: int = Field(default=0, ge=0, le=30000)
    is_active: bool = True
    description: str | None = None

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        """Ensure mock paths are path-only values and not full URLs."""
        text = value.strip()
        if not text.startswith("/"):
            text = f"/{text}"
        if "://" in text:
            raise ValueError("Mock path must not be a full URL")
        return text


class MockRuleRead(MockRuleCreate):
    """Response body for mock rules."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read SQLAlchemy models."""
        from_attributes = True


class PerformanceScenarioCreate(BaseModel):
    """Request body for performance scenario configuration."""
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    project_id: int | None = None
    target_url: str = Field(description="被压测目标公网 URL")
    method: HttpMethod = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    concurrency: int = Field(default=10, ge=1, le=10000)
    duration_seconds: int = Field(default=60, ge=1, le=86400)
    ramp_up_seconds: int = Field(default=10, ge=0, le=86400)
    threshold_p95_ms: int | None = Field(default=None, ge=1)
    threshold_error_rate: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    is_active: bool = True
    description: str | None = None


class PerformanceScenarioRead(PerformanceScenarioCreate):
    """Response body for performance scenarios."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read SQLAlchemy models."""
        from_attributes = True


class RunnerAgentCreate(BaseModel):
    """Request body for runner metadata."""
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    runner_type: str = Field(default="platform", max_length=40)
    status: str = Field(default="offline", max_length=30)
    base_url: str | None = Field(default=None, max_length=1000)
    capabilities: list[str] = Field(default_factory=list)
    is_active: bool = True
    description: str | None = None


class RunnerAgentRead(RunnerAgentCreate):
    """Response body for runner agents."""
    id: int
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read SQLAlchemy models."""
        from_attributes = True
