"""Integration routes for webhook configuration and future notifications."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import IntegrationWebhook, UiAutomationRun
from app.modules.integrations.schemas import IntegrationWebhookCreate, IntegrationWebhookRead
from app.modules.integrations.service import send_webhook_event
from app.modules.integrations.jira import JiraCloudAdapter, jira_ready, redact_text, sync_failed_run
from app.core.config import get_settings


router = APIRouter(tags=["集成开放"])


@router.get("/v1/integrations/jira/status", summary="查询 Jira Cloud 状态")
def jira_status(_: AuthContext = Depends(require_menu("integrations"))):
    settings = get_settings()
    return {"provider": "jira", "enabled": settings.jira_enabled, "auto_create_on_failure": settings.jira_auto_create_on_failure,
            "configured": jira_ready(settings), "project_key": settings.jira_project_key or "", "issue_type": settings.jira_issue_type}


@router.post("/v1/integrations/jira/test-connection", summary="测试 Jira Cloud 连接")
def test_jira_connection(_: AuthContext = Depends(require_menu("integrations"))):
    settings = get_settings()
    if not jira_ready(settings): raise HTTPException(400, "Jira 未启用或服务器环境变量未配置完整")
    try: return {"status": "ok", **JiraCloudAdapter(settings).test_connection()}
    except Exception as exc: raise HTTPException(400, redact_text(exc)) from exc


@router.post("/v1/test-tasks/{task_id}/jira-sync", summary="补偿同步失败测试批次到 Jira")
def sync_run_to_jira(task_id: int, background_tasks: BackgroundTasks, _: AuthContext = Depends(require_menu("emote_ui_automation")), db: Session = Depends(get_db)):
    run = db.get(UiAutomationRun, task_id)
    if run is None: raise HTTPException(404, "测试批次不存在")
    if run.status != "failed": raise HTTPException(409, "只有失败测试批次可同步 Jira")
    if not jira_ready(get_settings()): raise HTTPException(400, "Jira 未启用或服务器环境变量未配置完整")
    background_tasks.add_task(sync_failed_run, run.id)
    return {"status": "queued", "run_id": run.id, "message": "Jira 同步已在后台执行，不影响测试结果"}


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
        {"message": "cling webhook connectivity test", "webhook_id": item.id, "name": item.name},
    )
    if not result.get("sent"):
        raise HTTPException(status_code=400, detail=result.get("error") or result.get("reason") or "Webhook not sent")
    return {"status": "ok", "message": "Webhook test event sent", "result": result}
