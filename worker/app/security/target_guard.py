"""Worker-side safety guard and JSON path helper used during test execution."""

import ipaddress
import os
import socket
from typing import Any
from urllib.parse import urlparse


ALLOW_PRIVATE_TARGETS = os.getenv("ALLOW_PRIVATE_TARGETS", "false").lower() == "true"


def is_blocked_url(url: str) -> bool:
    """Return whether a target URL points to localhost, private networks, or metadata services."""
    if ALLOW_PRIVATE_TARGETS:
        return False
    parsed = urlparse(url)
    # Only HTTP and HTTPS are valid automation targets.
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return True
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        return True
    candidates: list[str] = []
    try:
        # Literal IPs can be checked directly.
        candidates.append(str(ipaddress.ip_address(host)))
    except ValueError:
        # Hostnames are resolved so private-network DNS results cannot bypass the guard.
        for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP):
            candidates.append(info[4][0])
    for candidate in candidates:
        ip = ipaddress.ip_address(candidate)
        if not ip.is_global or ip == ipaddress.ip_address("169.254.169.254"):
            return True
    return False


def json_path(data: Any, path: str | None) -> Any:
    """Read a simple JSON path from response data for assertions."""
    if not path:
        return None
    current = data
    # This intentionally supports simple object paths only, matching the low-code UI help text.
    for part in path.strip("$.").split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
