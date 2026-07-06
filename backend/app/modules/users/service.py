"""User management service helpers used by the users router."""

from app.core.menu import ADMIN_MENU_KEYS, ALL_MENU_KEYS
from app.models.entities import AppUser


def normalize_menu_permissions(values: list[str]) -> list[str]:
    """Filter, de-duplicate, and repair menu permission keys."""
    seen = []
    # Only allow known non-admin menu keys and keep the user-provided order.
    for value in values or []:
        if value in ALL_MENU_KEYS and value != "users" and value not in seen:
            seen.append(value)
    # API/UI testing depends on projects, so grant project visibility automatically.
    if ("api" in seen or "ui" in seen) and "projects" not in seen:
        seen.insert(0, "projects")
    return seen


def user_response(user: AppUser) -> dict:
    """Convert a user model into the frontend response shape."""
    permissions = ADMIN_MENU_KEYS if user.is_admin else list(user.menu_permissions or [])
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "menu_permissions": permissions,
        "created_at": user.created_at,
    }
