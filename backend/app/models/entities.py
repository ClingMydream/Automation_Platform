from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    """Add created_at and updated_at columns to database models."""
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppUser(Base, TimestampMixin):
    """Store login users, password hashes, roles, and menu permissions."""
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    menu_permissions: Mapped[list] = mapped_column(JSON, default=list)


class Project(Base, TimestampMixin):
    """Store project records that group test cases."""
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    environments = relationship("Environment", back_populates="project", cascade="all, delete-orphan")


class Environment(Base, TimestampMixin):
    """Store project environment configuration."""
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)

    project = relationship("Project", back_populates="environments")


class ApiCase(Base, TimestampMixin):
    """Store API test request and assertion settings."""
    __tablename__ = "api_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    method: Mapped[str] = mapped_column(String(12), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    headers: Mapped[dict] = mapped_column(JSON, default=dict)
    body: Mapped[str | None] = mapped_column(Text)
    assert_status: Mapped[int | None] = mapped_column(Integer)
    assert_text: Mapped[str | None] = mapped_column(Text)
    assert_json_path: Mapped[str | None] = mapped_column(String(300))
    assert_json_value: Mapped[str | None] = mapped_column(String(500))


class UiCase(Base, TimestampMixin):
    """Store low-code UI automation steps."""
    __tablename__ = "ui_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    steps: Mapped[list] = mapped_column(JSON, default=list)


class TestRun(Base, TimestampMixin):
    """Store one execution task, status, logs, report, and errors."""
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_type: Mapped[str] = mapped_column(String(20), nullable=False)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    logs: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    report: Mapped[dict] = mapped_column(JSON, default=dict)


class FileTransfer(Base, TimestampMixin):
    """Store temporary file transfer metadata and share tokens."""
    __tablename__ = "file_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="admin", nullable=False)
    parent_token: Mapped[str | None] = mapped_column(String(80))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
