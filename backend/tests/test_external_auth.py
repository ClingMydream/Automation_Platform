"""Tests for shared external automation token validation."""

from fastapi import HTTPException
import pytest

from app.core.external_auth import ensure_external_trigger_token


def test_external_token_accepts_matching_value():
    """Matching token values should allow CI or JMeter callbacks."""
    ensure_external_trigger_token("secret-token", configured_token="secret-token")


def test_external_token_rejects_missing_configuration():
    """Missing server-side token configuration should fail closed."""
    with pytest.raises(HTTPException) as exc:
        ensure_external_trigger_token("secret-token", configured_token="")

    assert exc.value.status_code == 503


def test_external_token_rejects_wrong_value():
    """Wrong callback token should be rejected as unauthorized."""
    with pytest.raises(HTTPException) as exc:
        ensure_external_trigger_token("wrong", configured_token="secret-token")

    assert exc.value.status_code == 401
