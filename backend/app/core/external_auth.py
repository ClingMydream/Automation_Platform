"""Shared token validation for CI, JMeter, and external automation callbacks."""

from fastapi import HTTPException

from app.core.config import get_settings


def ensure_external_trigger_token(x_automation_token: str | None, configured_token: str | None = None) -> None:
    """Validate the shared external automation token without logging or returning it."""
    expected_token = configured_token if configured_token is not None else get_settings().external_trigger_token
    if not expected_token:
        raise HTTPException(status_code=503, detail="External trigger token is not configured")
    if not x_automation_token or x_automation_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid trigger token")
