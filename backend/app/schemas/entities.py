"""Pydantic request and response schemas shared by backend route modules."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request body for username and password login."""
    username: str = Field(description="登录用户名", examples=["admin"])
    password: str = Field(description="登录密码", examples=["请填写服务器 .env 中的 ADMIN_PASSWORD"])


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
    username: str = Field(min_length=2, max_length=80, description="新用户登录名", examples=["tester01"])
    password: str = Field(min_length=6, max_length=128, description="新用户登录密码", examples=["Test@123456"])
    display_name: str | None = Field(default=None, max_length=120, description="页面展示名称", examples=["测试同学"])
    is_active: bool = Field(default=True, description="是否启用该账号")
    menu_permissions: list[str] = Field(default_factory=list, description="允许访问的菜单 key", examples=[["projects", "api", "runs"]])


class UserUpdate(BaseModel):
    """Request body for updating a login user."""
    password: str | None = Field(default=None, min_length=6, max_length=128, description="可选新密码，留空表示不修改")
    display_name: str | None = Field(default=None, max_length=120, description="页面展示名称")
    is_active: bool = Field(default=True, description="是否启用该账号")
    menu_permissions: list[str] = Field(default_factory=list, description="允许访问的菜单 key")


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
    name: str = Field(min_length=1, max_length=120, description="项目名称", examples=["演示项目"])
    description: str | None = Field(default=None, description="项目说明", examples=["用于接口和 UI 自动化演示"])


class ProjectRead(ProjectCreate):
    """Response body for project rows."""
    id: int
    created_at: datetime

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class EnvironmentCreate(BaseModel):
    """Request body for creating an environment config."""
    project_id: int = Field(description="所属项目 ID", examples=[1])
    name: str = Field(description="环境名称", examples=["测试环境"])
    base_url: str = Field(description="环境基础地址，只允许公网 HTTP/HTTPS", examples=["https://example.com"])
    variables: dict[str, Any] = Field(default_factory=dict, description="环境变量 JSON，例如 token、租户 ID 等")


class EnvironmentRead(EnvironmentCreate):
    """Response body for environment rows."""
    id: int

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class ApiCaseCreate(BaseModel):
    """Request body for creating or updating an API test case."""
    project_id: int = Field(description="所属项目 ID", examples=[1])
    environment_id: int | None = Field(default=None, description="?????? ID???? URL ???? /path ????", examples=[1])
    name: str = Field(description="接口用例名称", examples=["查询示例接口"])
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(description="HTTP 请求方法", examples=["GET"])
    url: str = Field(description="完整请求地址，只允许公网 HTTP/HTTPS", examples=["https://httpbin.org/get"])
    headers: dict[str, str] = Field(default_factory=dict, description="请求头 JSON", examples=[{"Accept": "application/json"}])
    body: str | None = Field(default=None, description="请求体文本，JSON 接口可填写 JSON 字符串", examples=['{"name":"demo"}'])
    assert_status: int | None = Field(default=200, description="期望 HTTP 状态码", examples=[200])
    assert_text: str | None = Field(default=None, description="期望响应文本包含的内容", examples=["origin"])
    assert_json_path: str | None = Field(default=None, description="期望校验的 JSON 路径", examples=["$.headers.Host"])
    assert_json_value: str | None = Field(default=None, description="JSON 路径对应的期望值", examples=["httpbin.org"])


class ApiCaseRead(ApiCaseCreate):
    """Response body for API test case rows."""
    id: int

    class Config:
        """Allow Pydantic to read fields from SQLAlchemy models."""
        from_attributes = True


class UiStep(BaseModel):
    """One low-code UI automation step."""
    action: Literal["goto", "click", "fill", "wait", "assert_text", "screenshot"] = Field(description="UI 自动化动作")
    target: str | None = Field(default=None, description="元素定位表达式或断言文本", examples=["input[name='q']"])
    value: str | None = Field(default=None, description="打开地址或输入内容", examples=["https://example.com"])
    timeout_ms: int | None = Field(default=5000, ge=100, le=30000, description="单步骤等待超时时间，单位毫秒")


class UiCaseCreate(BaseModel):
    """Request body for creating or updating a UI test case."""
    project_id: int = Field(description="所属项目 ID", examples=[1])
    name: str = Field(description="UI 用例名称", examples=["打开首页并截图"])
    steps: list[UiStep] = Field(description="低代码 UI 自动化步骤")


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
    case_type: Literal["api", "ui"] = Field(description="用例类型：api 表示接口用例，ui 表示 UI 用例", examples=["api"])
    case_id: int = Field(description="要执行的用例 ID", examples=[1])


class RunRead(BaseModel):
    """Response body for execution run details."""
    id: int
    batch_id: int | None = None
    task_id: int | None = None
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
