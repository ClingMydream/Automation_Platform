"""Authentication API routes for login, logout, and current-user profile."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, create_access_token, ensure_admin_user, get_current_user, verify_password
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import AppUser
from app.schemas.entities import (
    LoginRequest,
    MeResponse,
    TokenResponse,
)


router = APIRouter()

# 登录认证：只负责登录、退出、当前用户信息，不放业务功能。
@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Validate credentials and return an access token."""
    settings = get_settings()
    # The configured bootstrap admin can log in even before the database row exists.
    if payload.username == settings.admin_username and payload.password == settings.admin_password:
        admin = ensure_admin_user(db)
        return TokenResponse(access_token=create_access_token(admin.username, is_admin=True))
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()
    # Disabled users and wrong passwords intentionally share the same error message.
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user.username, is_admin=user.is_admin))


@router.post("/auth/logout")
def logout(_: AuthContext = Depends(get_current_user)):
    """Provide a logout endpoint; the frontend clears local token state."""
    return {"status": "ok"}


@router.get("/auth/me", response_model=MeResponse)
def me(current_user: AuthContext = Depends(get_current_user)):
    """Return current user profile and menu permissions."""
    return {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "is_admin": current_user.is_admin,
        "menu_permissions": current_user.menu_permissions,
    }
