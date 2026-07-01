from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    environments = relationship("Environment", back_populates="project", cascade="all, delete-orphan")


class Environment(Base, TimestampMixin):
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)

    project = relationship("Project", back_populates="environments")


class ApiCase(Base, TimestampMixin):
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
    __tablename__ = "ui_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    steps: Mapped[list] = mapped_column(JSON, default=list)


class TestRun(Base, TimestampMixin):
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_type: Mapped[str] = mapped_column(String(20), nullable=False)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    logs: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
