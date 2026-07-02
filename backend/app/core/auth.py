import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.menu import ADMIN_MENU_KEYS
from app.db import get_db
from app.models.entities import AppUser


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    """Carry the authenticated user identity and menu permissions through a request."""
    username: str
    display_name: str | None
    is_admin: bool
    menu_permissions: list[str]


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2 before storing it."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Compare a plain password with the stored PBKDF2 hash."""
    try:
        algorithm, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
    return hmac.compare_digest(candidate, digest)


def create_access_token(subject: str, *, is_admin: bool = False) -> str:
    """Create a JWT access token for a logged-in user."""
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "is_admin": is_admin, "exp": expires_at}
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def _decode_subject(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Decode the bearer token and extract the username subject."""
    settings = get_settings()
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = jwt.decode(credentials.credentials, settings.app_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return subject


def ensure_admin_user(db: Session) -> AppUser:
    """Create or repair the configured administrator account."""
    settings = get_settings()
    user = db.query(AppUser).filter(AppUser.username == settings.admin_username).first()
    if user is None:
        user = AppUser(
            username=settings.admin_username,
            display_name="系统管理员",
            password_hash=hash_password(settings.admin_password),
            is_admin=True,
            is_active=True,
            menu_permissions=ADMIN_MENU_KEYS,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_admin:
        user.is_admin = True
        user.is_active = True
        user.menu_permissions = ADMIN_MENU_KEYS
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Load the current active user from the bearer token."""
    subject = _decode_subject(credentials)
    user = db.query(AppUser).filter(AppUser.username == subject).first()
    if user is None:
        settings = get_settings()
        if subject == settings.admin_username:
            user = ensure_admin_user(db)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
    permissions = ADMIN_MENU_KEYS if user.is_admin else list(user.menu_permissions or [])
    return AuthContext(
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin,
        menu_permissions=permissions,
    )


def verify_admin(current_user: AuthContext = Depends(get_current_user)) -> AuthContext:
    """Require the current user to be an administrator."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return current_user


def require_menu(menu_key: str):
    """Build a FastAPI dependency that requires access to one menu key."""
    def dependency(current_user: AuthContext = Depends(get_current_user)) -> AuthContext:
        """Validate that the current user can access the configured menu key."""
        if current_user.is_admin or menu_key in current_user.menu_permissions:
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Menu permission required")

    return dependency
