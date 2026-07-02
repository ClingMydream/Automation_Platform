"""Backend URL safety guard that blocks localhost, private networks, and metadata services."""

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

from app.core.config import get_settings


BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}
BLOCKED_IPS = {ipaddress.ip_address("169.254.169.254")}


def _is_blocked_ip(value: str) -> bool:
    """Check whether an IP address belongs to blocked network ranges."""
    ip = ipaddress.ip_address(value)
    # The cloud metadata IP is blocked explicitly because it can leak server credentials.
    if ip in BLOCKED_IPS:
        return True
    # ip.is_global keeps private, loopback, link-local, multicast, and reserved networks out.
    return not ip.is_global


def validate_public_http_url(url: str) -> None:
    """Allow only public HTTP or HTTPS target URLs."""
    settings = get_settings()
    parsed = urlparse(url)
    # The platform only executes browser/API tests against HTTP(S) targets.
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL must be http or https")
    if settings.allow_private_targets:
        return
    hostname = parsed.hostname.strip().lower()
    # Block obvious localhost names before doing DNS resolution.
    if hostname in BLOCKED_HOSTS:
        raise HTTPException(status_code=400, detail="Private or local targets are not allowed")
    try:
        # Literal IP targets can be checked without DNS.
        if _is_blocked_ip(hostname):
            raise HTTPException(status_code=400, detail="Private or local targets are not allowed")
        return
    except ValueError:
        pass
    try:
        # Hostnames are resolved and every returned IP is checked to prevent DNS-based bypasses.
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="Target hostname cannot be resolved") from exc
    for info in infos:
        address = info[4][0]
        if _is_blocked_ip(address):
            raise HTTPException(status_code=400, detail="Private or local targets are not allowed")
