"""Integration routes for webhook configuration and future notifications."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import IntegrationWebhook
from app.modules.integrations.schemas import IntegrationWebhookCreate, IntegrationWebhookRead
from app.modules.integrations.service import send_webhook_event


router = APIRouter(tags=["集成开放"])


@router.get("/v1/integrations/webhooks", response_model=list[IntegrationWebhookRead], summary="查询 Webhook 集成")
def list_webhooks(_: AuthContext = Depends(require_menu("integrations")), db: Session = Depends(get_db)):
    """List notification webhook configurations."""
    return db.query(IntegrationWebhook).order_by(IntegrationWebhook.id.desc()).all()


@router.post("/v1/integrations/webhooks", response_model=IntegrationWebhookRead, summary="新增 Webhook 集成")
def create_webhook(payload: IntegrationWebhookCreate, _: AuthContext = Depends(require_menu("integrations")), db: Session = Depends(get_db)):
    """Create a webhook integration after URL safety validation."""
    validate_public_http_url(payload.webhook_url)
    item = IntegrationWebhook(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/v1/integrations/webhooks/{webhook_id}", response_model=IntegrationWebhookRead, summary="修改 Webhook 集成")
def update_webhook(webhook_id: int, payload: IntegrationWebhookCreate, _: AuthContext = Depends(require_menu("integrations")), db: Session = Depends(get_db)):
    """Update a webhook integration after URL safety validation."""
    item = db.get(IntegrationWebhook, webhook_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    validate_public_http_url(payload.webhook_url)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/v1/integrations/webhooks/{webhook_id}", summary="删除 Webhook 集成")
def delete_webhook(webhook_id: int, _: AuthContext = Depends(require_menu("integrations")), db: Session = Depends(get_db)):
    """Delete one webhook integration."""
    item = db.get(IntegrationWebhook, webhook_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.post("/v1/integrations/webhooks/{webhook_id}/test", summary="测试 Webhook 配置")
def test_webhook(webhook_id: int, _: AuthContext = Depends(require_menu("integrations")), db: Session = Depends(get_db)):
    """Send a test event to verify the webhook can receive platform notifications."""
    item = db.get(IntegrationWebhook, webhook_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    result = send_webhook_event(
        item,
        "webhook_test",
        {"message": "Automation Platform webhook test", "webhook_id": item.id, "name": item.name},
    )
    if not result.get("sent"):
        raise HTTPException(status_code=400, detail=result.get("error") or result.get("reason") or "Webhook not sent")
    return {"status": "ok", "message": "Webhook test event sent", "result": result}
