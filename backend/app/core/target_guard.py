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
    if ip in BLOCKED_IPS:
        return True
    return not ip.is_global


def validate_public_http_url(url: str) -> None:
    """Allow only public HTTP or HTTPS target URLs."""
    settings = get_settings()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL must be http or https")
    if settings.allow_private_targets:
        return
    hostname = parsed.hostname.strip().lower()
    if hostname in BLOCKED_HOSTS:
        raise HTTPException(status_code=400, detail="Private or local targets are not allowed")
    try:
        if _is_blocked_ip(hostname):
            raise HTTPException(status_code=400, detail="Private or local targets are not allowed")
        return
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="Target hostname cannot be resolved") from exc
    for info in infos:
        address = info[4][0]
        if _is_blocked_ip(address):
            raise HTTPException(status_code=400, detail="Private or local targets are not allowed")
