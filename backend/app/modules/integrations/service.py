"""Webhook helpers for the toolbox integration settings."""

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from app.models.entities import IntegrationWebhook


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
    return {"X-Toolbox-Secret": secret}


def _message_text(event: str, payload: dict[str, Any]) -> str:
    """Build a concise text message for chat-style webhooks."""
    message = payload.get("data", {}).get("message", "Toolbox webhook connectivity test")
    return f"Toolbox {event}: {message}"


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
