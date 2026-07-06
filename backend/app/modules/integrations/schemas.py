"""Request and response schemas for integration APIs."""

from datetime import datetime

from pydantic import BaseModel, Field


class IntegrationWebhookCreate(BaseModel):
    """Request body for creating or updating a webhook integration."""
    name: str = Field(min_length=1, max_length=160, description="集成名称")
    integration_type: str = Field(default="webhook", max_length=40, description="集成类型，例如 dingtalk、wechat、feishu、webhook")
    webhook_url: str = Field(max_length=1000, description="Webhook 地址")
    events: list[str] = Field(default_factory=list, description="订阅事件，例如 task_failed、batch_finished")
    secret_name: str | None = Field(default=None, max_length=120, description="服务器环境变量中的密钥名称，不直接保存密钥明文")
    is_active: bool = Field(default=True, description="是否启用")
    description: str | None = Field(default=None, description="说明")


class IntegrationWebhookRead(IntegrationWebhookCreate):
    """Response body for integration rows."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True
