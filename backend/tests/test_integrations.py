"""Tests for webhook integration notification helpers."""

from app.models.entities import IntegrationWebhook as WebhookModel
from app.modules.integrations import service


def test_webhook_accepts_empty_event_list_as_all_events():
    """Empty event subscriptions should receive all supported notification events."""
    webhook = WebhookModel(name="all", webhook_url="https://example.com/hook", events=[], is_active=True)

    assert service.webhook_accepts_event(webhook, "batch_finished") is True


def test_webhook_test_event_bypasses_subscription_filter(monkeypatch):
    """The manual test event should verify delivery even if normal events are limited."""
    webhook = WebhookModel(
        name="limited",
        integration_type="webhook",
        webhook_url="https://example.com/hook",
        events=["batch_finished"],
        is_active=True,
    )

    monkeypatch.setattr(service, "_post_webhook", lambda *_: {"status_code": 200, "ok": True})

    result = service.send_webhook_event(webhook, "webhook_test", {"message": "hello"})

    assert result["sent"] is True
    assert result["ok"] is True


def test_dingtalk_payload_format_is_text_message():
    """DingTalk style integrations should receive the text-message shape."""
    webhook = WebhookModel(name="ding", integration_type="dingtalk", webhook_url="https://example.com/hook")
    payload = {"event": "batch_finished", "data": {"batch_no": "BT-1", "status": "passed", "failed_count": 0, "total_count": 2}}

    formatted = service._format_payload_for_integration(webhook, payload)

    assert formatted["msgtype"] == "text"
    assert "BT-1" in formatted["text"]["content"]
