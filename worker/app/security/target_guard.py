import ipaddress
import os
import socket
from typing import Any
from urllib.parse import urlparse


ALLOW_PRIVATE_TARGETS = os.getenv("ALLOW_PRIVATE_TARGETS", "false").lower() == "true"


def is_blocked_url(url: str) -> bool:
    if ALLOW_PRIVATE_TARGETS:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return True
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        return True
    candidates: list[str] = []
    try:
        candidates.append(str(ipaddress.ip_address(host)))
    except ValueError:
        for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP):
            candidates.append(info[4][0])
    for candidate in candidates:
        ip = ipaddress.ip_address(candidate)
        if not ip.is_global or ip == ipaddress.ip_address("169.254.169.254"):
            return True
    return False


def json_path(data: Any, path: str | None) -> Any:
    if not path:
        return None
    current = data
    for part in path.strip("$.").split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
