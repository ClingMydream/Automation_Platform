"""User management API routes for administrators."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, ensure_admin_user, hash_password, verify_admin
from app.core.config import get_settings
from app.core.menu import ADMIN_MENU_KEYS, MENU_OPTIONS
from app.db import get_db
from app.models.entities import AppUser
from app.modules.users.service import normalize_menu_permissions, user_response
from app.schemas.entities import (
    UserCreate,
    UserRead,
    UserUpdate,
)


router = APIRouter(tags=["用户管理"])

# 用户管理：管理员专属，用来维护登录账号和菜单权限。
@router.get(
    "/menu-options",
    summary="查询可配置菜单权限",
    description="管理员打开用户管理页时读取菜单权限清单，用于控制普通用户能看到哪些功能模块。",
)
def menu_options(_: AuthContext = Depends(verify_admin)):
    """Return menu options that administrators can assign to users."""
    return MENU_OPTIONS


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="查询登录用户列表",
    description="管理员查看所有平台登录账号，返回账号状态、管理员标记和菜单权限。",
)
def list_users(_: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    """List all login users for administrator management."""
    ensure_admin_user(db)
    users = db.query(AppUser).order_by(AppUser.is_admin.desc(), AppUser.id.desc()).all()
    return [user_response(user) for user in users]


@router.post(
    "/users",
    response_model=UserRead,
    summary="新增普通登录用户",
    description="管理员创建非管理员账号，并配置该用户可访问的菜单权限。",
)
def create_user(payload: UserCreate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    """Create a non-admin login user with menu permissions."""
    username = payload.username.strip()
    # The bootstrap administrator name is reserved so a normal user cannot shadow it.
    if username == get_settings().admin_username:
        raise HTTPException(status_code=400, detail="This username is reserved")
    if db.query(AppUser).filter(AppUser.username == username).first() is not None:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = AppUser(
        username=username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        is_admin=False,
        is_active=payload.is_active,
        menu_permissions=normalize_menu_permissions(payload.menu_permissions),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_response(user)


@router.put(
    "/users/{user_id}",
    response_model=UserRead,
    summary="修改登录用户",
    description="管理员修改用户显示名、启用状态、菜单权限和可选的新密码。",
)
def update_user(user_id: int, payload: UserUpdate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    """Update a user password, active flag, and menu permissions."""
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        # Admin permissions are fixed to the full platform and cannot be reduced from the UI.
        user.display_name = payload.display_name or user.display_name
        user.is_active = True
        user.menu_permissions = ADMIN_MENU_KEYS
    else:
        user.display_name = payload.display_name
        user.is_active = payload.is_active
        user.menu_permissions = normalize_menu_permissions(payload.menu_permissions)
    if payload.password:
        # Password changes are optional; leaving it empty preserves the old hash.
        user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return user_response(user)


@router.delete(
    "/users/{user_id}",
    summary="删除普通登录用户",
    description="删除一个非管理员账号；管理员账号不能从接口删除。",
)
def delete_user(user_id: int, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    """Delete a non-admin login user."""
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Admin user cannot be deleted")
    db.delete(user)
    db.commit()
    return {"status": "ok"}
