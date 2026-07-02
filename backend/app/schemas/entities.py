from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


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
    id: int
    username: str
    display_name: str | None
    is_admin: bool
    is_active: bool
    menu_permissions: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class ProjectRead(ProjectCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EnvironmentCreate(BaseModel):
    project_id: int
    name: str
    base_url: str
    variables: dict[str, Any] = {}


class EnvironmentRead(EnvironmentCreate):
    id: int

    class Config:
        from_attributes = True


class ApiCaseCreate(BaseModel):
    project_id: int
    name: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    url: str
    headers: dict[str, str] = {}
    body: str | None = None
    assert_status: int | None = 200
    assert_text: str | None = None
    assert_json_path: str | None = None
    assert_json_value: str | None = None


class ApiCaseRead(ApiCaseCreate):
    id: int

    class Config:
        from_attributes = True


class UiStep(BaseModel):
    action: Literal["goto", "click", "fill", "wait", "assert_text", "screenshot"]
    target: str | None = None
    value: str | None = None
    timeout_ms: int | None = Field(default=5000, ge=100, le=30000)


class UiCaseCreate(BaseModel):
    project_id: int
    name: str
    steps: list[UiStep]


class UiCaseRead(BaseModel):
    id: int
    project_id: int
    name: str
    steps: list[dict[str, Any]]

    class Config:
        from_attributes = True


class RunCreate(BaseModel):
    case_type: Literal["api", "ui"]
    case_id: int


class RunRead(BaseModel):
    id: int
    case_type: str
    case_id: int
    status: str
    duration_ms: int | None
    logs: str | None
    error: str | None
    report: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
