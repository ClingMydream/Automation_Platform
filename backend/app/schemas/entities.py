"""Authentication and user-management schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(description="登录用户名", examples=["admin"])
    password: str = Field(description="登录密码")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    username: str
    display_name: str | None = None
    is_admin: bool
    menu_permissions: list[str]


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    is_active: bool = True
    menu_permissions: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    is_active: bool = True
    menu_permissions: list[str] = Field(default_factory=list)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None
    is_admin: bool
    is_active: bool
    menu_permissions: list[str]
    created_at: datetime
