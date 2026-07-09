"""Tests for public mock response service helpers."""

from app.models.entities import MockRule
from app.modules.mock_service.service import build_mock_response, normalize_mock_path, response_headers


def test_normalize_mock_path_adds_leading_slash():
    """Mock paths should match stored slash-prefixed rule paths."""
    assert normalize_mock_path("api/demo") == "/api/demo"
    assert normalize_mock_path("/api/demo") == "/api/demo"


def test_response_headers_filters_hop_by_hop_headers():
    """Unsafe transport headers should not be returned from mock rules."""
    headers = response_headers({"Content-Type": "text/plain", "Connection": "close", "X-Demo": 123})

    assert headers == {"Content-Type": "text/plain", "X-Demo": "123"}


def test_build_mock_response_uses_rule_body_status_and_headers():
    """A mock rule should become a normal HTTP response."""
    rule = MockRule(
        method="GET",
        path="/api/demo",
        status_code=201,
        response_headers={"Content-Type": "text/plain", "X-Mock": "yes"},
        response_body="hello",
        delay_ms=0,
        is_active=True,
    )

    response = build_mock_response(rule)

    assert response.status_code == 201
    assert response.body == b"hello"
    assert response.media_type == "text/plain"
    assert response.headers["x-mock"] == "yes"
