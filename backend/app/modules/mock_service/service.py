"""Helpers for turning stored mock rules into HTTP responses."""

import time
from typing import Any

from fastapi import HTTPException, Response
from sqlalchemy.orm import Session

from app.models.entities import MockRule


BLOCKED_RESPONSE_HEADERS = {"content-length", "transfer-encoding", "connection"}


def normalize_mock_path(path: str) -> str:
    """Normalize a captured mock path to the same shape stored by rules."""
    text = (path or "").strip()
    if not text.startswith("/"):
        text = f"/{text}"
    return text


def find_mock_rule(db: Session, method: str, path: str) -> MockRule:
    """Find the newest active mock rule for one method and path."""
    item = (
        db.query(MockRule)
        .filter(MockRule.is_active == True)  # noqa: E712
        .filter(MockRule.method == method.upper())
        .filter(MockRule.path == normalize_mock_path(path))
        .order_by(MockRule.id.desc())
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Mock rule not found")
    return item


def response_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    """Filter unsafe hop-by-hop headers before returning a mock response."""
    safe_headers: dict[str, str] = {}
    for key, value in (headers or {}).items():
        name = str(key).strip()
        if name and name.lower() not in BLOCKED_RESPONSE_HEADERS:
            safe_headers[name] = str(value)
    return safe_headers


def build_mock_response(rule: MockRule) -> Response:
    """Convert one mock rule row into a FastAPI response."""
    if rule.delay_ms:
        time.sleep(min(rule.delay_ms, 30000) / 1000)
    headers = response_headers(rule.response_headers)
    media_type = headers.pop("Content-Type", headers.pop("content-type", "application/json"))
    return Response(
        content=rule.response_body or "",
        status_code=rule.status_code,
        headers=headers,
        media_type=media_type,
    )
