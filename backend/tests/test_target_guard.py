"""Tests for blocking unsafe private or local automation targets."""

import pytest
from fastapi import HTTPException

from app.core.target_guard import validate_public_http_url


@pytest.mark.parametrize("url", ["http://127.0.0.1", "http://localhost", "http://169.254.169.254/latest/meta-data"])
def test_blocks_private_targets(url):
    """Verify that unsafe local and metadata URLs are rejected."""
    with pytest.raises(HTTPException):
        validate_public_http_url(url)
