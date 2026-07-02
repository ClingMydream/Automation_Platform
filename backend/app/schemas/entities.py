"""Pydantic request and response schemas shared by backend route modules."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request body for username and password login."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Response body returned after a successful login."""
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    """Response body describing the current logged-in user."""
    username: str
    display_name: str | None = None
    is_admin: bool
    menu_permissions: list[str]


class UserCreate(BaseModel):
    """Request body for creating a login user."""
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    is_active: bool = True
    menu_permissions: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Request body for updating a login user."""
    password: str | None = Field(default=None, min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    is_active: bool = True
    menu_permissions: list[str] = Field(default_factory=list)


class UserRead(BaseModel):
    """Response body for user rows shown in user management."""
    id: int
    username: str
    display_name: str | None
    is_admin: bool
    is_active: bool
    menu_permissions: list[str]
    created_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class ProjectCreate(BaseModel):
    """Request body for creating or updating a project."""
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class ProjectRead(ProjectCreate):
    """Response body for project rows."""
    id: int
    created_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class EnvironmentCreate(BaseModel):
    """Request body for creating an environment config."""
    project_id: int
    name: str
    base_url: str
    variables: dict[str, Any] = {}


class EnvironmentRead(EnvironmentCreate):
    """Response body for environment rows."""
    id: int

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class ApiCaseCreate(BaseModel):
    """Request body for creating or updating an API test case."""
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
    """Response body for API test case rows."""
    id: int

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class UiStep(BaseModel):
    """One low-code UI automation step."""
    action: Literal["goto", "click", "fill", "wait", "assert_text", "screenshot"]
    target: str | None = None
    value: str | None = None
    timeout_ms: int | None = Field(default=5000, ge=100, le=30000)


class UiCaseCreate(BaseModel):
    """Request body for creating or updating a UI test case."""
    project_id: int
    name: str
    steps: list[UiStep]


class UiCaseRead(BaseModel):
    """Response body for UI test case rows."""
    id: int
    project_id: int
    name: str
    steps: list[dict[str, Any]]

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class RunCreate(BaseModel):
    """Request body for creating an execution run."""
    case_type: Literal["api", "ui"]
    case_id: int


class RunRead(BaseModel):
    """Response body for execution run details."""
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
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True
