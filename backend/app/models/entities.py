"""Minimal SQLAlchemy entities required by the efficiency toolbox."""

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TimestampMixin:
    """Add creation and update timestamps to persisted settings."""

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


class IntegrationWebhook(Base, TimestampMixin):
    """Store reusable outbound webhook configuration."""

    __tablename__ = "integration_webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(40), default="webhook", nullable=False)
    webhook_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    events: Mapped[list] = mapped_column(JSON, default=list)
    secret_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class FileTransfer(Base, TimestampMixin):
    """Store temporary file-transfer metadata and share tokens."""

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


class LearningProfile(Base, TimestampMixin):
    """Store the singleton personal learning profile and seed version."""

    __tablename__ = "learning_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seed_version: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    current_role: Mapped[str] = mapped_column(String(120), nullable=False)
    target_role: Mapped[str] = mapped_column(String(200), nullable=False)
    target_city: Mapped[str] = mapped_column(String(80), nullable=False)
    current_salary: Mapped[str] = mapped_column(String(40), nullable=False)
    target_salary: Mapped[str] = mapped_column(String(40), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_target_minutes: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    current_focus: Mapped[str] = mapped_column(String(300), nullable=False)
    strengths: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    gaps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class LearningPlan(Base, TimestampMixin):
    """Store the active learning plan and its projected date range."""

    __tablename__ = "learning_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    original_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    projected_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)


class LearningTask(Base, TimestampMixin):
    """Store one actionable learning task on the 40-day plan."""

    __tablename__ = "learning_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("learning_plans.id", ondelete="CASCADE"), index=True, nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    expected_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    original_planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class LearningCheckin(Base, TimestampMixin):
    """Store one daily study check-in and reflection."""

    __tablename__ = "learning_checkins"
    __table_args__ = (UniqueConstraint("checkin_date", name="uq_learning_checkin_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkin_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gains: Mapped[str] = mapped_column(Text, default="", nullable=False)
    blockers: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tomorrow_focus: Mapped[str] = mapped_column(Text, default="", nullable=False)


class LearningScheduleShift(Base):
    """Audit automatic schedule shifts so the projected deadline is explainable."""

    __tablename__ = "learning_schedule_shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("learning_plans.id", ondelete="CASCADE"), index=True, nullable=False)
    shifted_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    days_shifted: Mapped[int] = mapped_column(Integer, nullable=False)
    earliest_overdue_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class LearningNoteFolder(Base, TimestampMixin):
    """Store a nested personal note folder."""

    __tablename__ = "learning_note_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("learning_note_folders.id", ondelete="SET NULL"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class LearningNote(Base, TimestampMixin):
    """Store canonical Markdown notes with optional task links."""

    __tablename__ = "learning_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder_id: Mapped[int | None] = mapped_column(ForeignKey("learning_note_folders.id", ondelete="SET NULL"), index=True)
    linked_task_id: Mapped[int | None] = mapped_column(ForeignKey("learning_tasks.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    import_fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True)
    import_source_path: Mapped[str | None] = mapped_column(String(1000))


class LearningAttachment(Base, TimestampMixin):
    """Store persistent learning-note attachment metadata."""

    __tablename__ = "learning_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("learning_notes.id", ondelete="CASCADE"), index=True, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class LearningImport(Base):
    """Record a completed or failed note import for audit and feedback."""

    __tablename__ = "learning_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(40), default="youdao_zip", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    report: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
