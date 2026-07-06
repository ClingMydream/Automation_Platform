"""SQLAlchemy ORM entities used by backend routes and worker execution records."""

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


class TestObject(Base, TimestampMixin):
    """Store platform-level test objects that describe what should be tested."""
    __tablename__ = "test_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    object_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    business_module: Mapped[str | None] = mapped_column(String(120))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class TestTask(Base, TimestampMixin):
    """Store reusable execution tasks that can be triggered manually, by CI, or by schedule."""
    __tablename__ = "test_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    task_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    environment_id: Mapped[int | None] = mapped_column(ForeignKey("environments.id"))
    test_object_id: Mapped[int | None] = mapped_column(ForeignKey("test_objects.id"))
    trigger_type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    runner_type: Mapped[str] = mapped_column(String(40), default="platform", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(120))
    owner: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str | None] = mapped_column(Text)
    last_status: Mapped[str | None] = mapped_column(String(30))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)


class ExecutionBatch(Base, TimestampMixin):
    """Store one independent execution batch for traceable task runs."""
    __tablename__ = "execution_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_no: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("test_tasks.id"))
    trigger_type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    environment_id: Mapped[int | None] = mapped_column(ForeignKey("environments.id"))
    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)


class TestResult(Base, TimestampMixin):
    """Store detailed test evidence collected from platform runs or external scripts."""
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("execution_batches.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("test_tasks.id"), index=True)
    test_object_id: Mapped[int | None] = mapped_column(ForeignKey("test_objects.id"), index=True)
    case_type: Mapped[str | None] = mapped_column(String(40), index=True)
    case_id: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str] = mapped_column(String(40), default="api", nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    request_data: Mapped[dict] = mapped_column(JSON, default=dict)
    response_data: Mapped[dict] = mapped_column(JSON, default=dict)
    assertions: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    logs: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    failure_category: Mapped[str | None] = mapped_column(String(80), index=True)
    environment_id: Mapped[int | None] = mapped_column(ForeignKey("environments.id"))
    device_info: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class TestAttachment(Base, TimestampMixin):
    """Store uploaded screenshots, recordings, logs, HAR files, and report attachments."""
    __tablename__ = "test_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    result_id: Mapped[int | None] = mapped_column(ForeignKey("test_results.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("execution_batches.id"), index=True)
    attachment_type: Mapped[str] = mapped_column(String(40), default="log", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)


class TestDataset(Base, TimestampMixin):
    """Store parameterized test data, accounts, and reusable data pools."""
    __tablename__ = "test_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    dataset_type: Mapped[str] = mapped_column(String(40), default="variables", nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    rows: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class IntegrationWebhook(Base, TimestampMixin):
    """Store outbound webhook integration configuration for future notifications."""
    __tablename__ = "integration_webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(40), default="webhook", nullable=False)
    webhook_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    events: Mapped[list] = mapped_column(JSON, default=list)
    secret_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


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
