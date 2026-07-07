"""Webhook notification helpers for integration and result events."""

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.entities import ExecutionBatch, IntegrationWebhook


def webhook_accepts_event(webhook: IntegrationWebhook, event: str) -> bool:
    """Return whether a webhook subscribes to an event; empty events means all events."""
    events = webhook.events or []
    return not events or event in events


def _secret_headers(secret_name: str | None) -> dict[str, str]:
    """Build optional headers from a server environment variable without exposing the value elsewhere."""
    if not secret_name:
        return {}
    secret = os.getenv(secret_name)
    if not secret:
        return {}
    return {"X-Automation-Secret": secret}


def _message_text(event: str, payload: dict[str, Any]) -> str:
    """Build a concise text message for chat-style webhooks."""
    data = payload.get("data", payload)
    status = data.get("status", "-")
    batch_no = data.get("batch_no") or data.get("message") or "-"
    failed = data.get("failed_count", 0)
    total = data.get("total_count", 0)
    return f"Automation Platform {event}: {batch_no}, status={status}, failed={failed}, total={total}"


def _format_payload_for_integration(webhook: IntegrationWebhook, payload: dict[str, Any]) -> dict[str, Any]:
    """Adapt the generic event payload to common webhook message formats."""
    integration_type = (webhook.integration_type or "webhook").lower()
    text = _message_text(payload["event"], payload)
    if integration_type in {"dingtalk", "wechat"}:
        return {"msgtype": "text", "text": {"content": text}}
    if integration_type == "feishu":
        return {"msg_type": "text", "content": {"text": text}}
    return payload


def _post_webhook(webhook: IntegrationWebhook, payload: dict[str, Any]) -> dict[str, Any]:
    """Send one webhook request with a short timeout so notifications never block the platform."""
    headers = {"Content-Type": "application/json", **_secret_headers(webhook.secret_name)}
    body = _format_payload_for_integration(webhook, payload)
    with httpx.Client(timeout=5.0, follow_redirects=False) as client:
        response = client.post(webhook.webhook_url, json=body, headers=headers)
        return {"status_code": response.status_code, "ok": response.status_code < 400}


def send_webhook_event(webhook: IntegrationWebhook, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send one event to one active webhook when the event is subscribed."""
    if not webhook.is_active:
        return {"sent": False, "reason": "inactive"}
    if event != "webhook_test" and not webhook_accepts_event(webhook, event):
        return {"sent": False, "reason": "not_subscribed"}
    event_payload = {
        "event": event,
        "integration_type": webhook.integration_type,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    try:
        result = _post_webhook(webhook, event_payload)
        return {"sent": True, **result}
    except httpx.HTTPError as exc:
        return {"sent": False, "error": str(exc)}


def batch_notification_payload(batch: ExecutionBatch) -> dict[str, Any]:
    """Build a safe notification payload for an execution batch."""
    settings = get_settings()
    return {
        "batch_id": batch.id,
        "batch_no": batch.batch_no,
        "task_id": batch.task_id,
        "trigger_type": batch.trigger_type,
        "environment_id": batch.environment_id,
        "status": batch.status,
        "total_count": batch.total_count,
        "passed_count": batch.passed_count,
        "failed_count": batch.failed_count,
        "skipped_count": batch.skipped_count,
        "duration_ms": batch.duration_ms,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "finished_at": batch.finished_at.isoformat() if batch.finished_at else None,
        "report_url": f"{settings.public_base_url.rstrip('/')}/api/reports/batches/{batch.id}" if batch.id else None,
    }


def notify_batch_finished(db, batch: ExecutionBatch) -> dict[str, int]:
    """Notify active webhooks when a batch reaches a final status."""
    if batch.status not in {"passed", "failed", "error"}:
        return {"matched": 0, "sent": 0, "failed": 0}
    payload = batch_notification_payload(batch)
    events = ["batch_finished"]
    if batch.status in {"failed", "error"} or batch.failed_count:
        events.extend(["task_failed", "quality_risk"])
    webhooks = db.query(IntegrationWebhook).filter(IntegrationWebhook.is_active == True).all()  # noqa: E712
    stats = {"matched": 0, "sent": 0, "failed": 0}
    for webhook in webhooks:
        for event in events:
            if not webhook_accepts_event(webhook, event):
                continue
            stats["matched"] += 1
            result = send_webhook_event(webhook, event, payload)
            if result.get("sent") and result.get("ok", True):
                stats["sent"] += 1
            else:
                stats["failed"] += 1
    return stats
