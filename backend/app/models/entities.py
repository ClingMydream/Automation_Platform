"""Minimal SQLAlchemy entities required by the efficiency toolbox."""

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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


class MiniProgramAccount(Base, TimestampMixin):
    """Link one WeChat OpenID to an app user that administrators can enable or disable."""

    __tablename__ = "mini_program_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    openid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1000))
    department: Mapped[str | None] = mapped_column(String(120))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OaAccountReviewer(Base, TimestampMixin):
    """Store the reviewers selected for each individual Mini Program account."""

    __tablename__ = "oa_account_reviewers"
    __table_args__ = (UniqueConstraint("account_id", "reviewer_account_id", name="uq_oa_account_reviewer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("mini_program_accounts.id", ondelete="CASCADE"), index=True, nullable=False)
    reviewer_account_id: Mapped[int] = mapped_column(ForeignKey("mini_program_accounts.id", ondelete="CASCADE"), index=True, nullable=False)


class OaApprovalTemplate(Base, TimestampMixin):
    """Store an administrator-managed approval form definition for the Mini Program."""

    __tablename__ = "oa_approval_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(12), default="📝", nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#f8a7be", nullable=False)
    fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OaApprovalRequest(Base, TimestampMixin):
    """Persist a submitted OA application and its immutable form payload."""

    __tablename__ = "oa_approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("oa_approval_templates.id"), index=True, nullable=False)
    requester_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True, nullable=False)
    request_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    form_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True, nullable=False)
    current_approver_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.id"), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class OaApprovalAction(Base, TimestampMixin):
    """Keep an auditable approval timeline rather than overwriting an application decision."""

    __tablename__ = "oa_approval_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("oa_approval_requests.id", ondelete="CASCADE"), index=True, nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str] = mapped_column(String(500), default="", nullable=False)


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


class TestPackage(Base, TimestampMixin):
    """Store the single latest test package behind a stable download address."""

    __tablename__ = "test_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, default="latest")
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160))
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    version: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    upload_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class CommandSnippet(Base, TimestampMixin):
    """Store built-in and personal command-line reference entries."""

    __tablename__ = "command_snippets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    usage_example: Mapped[str] = mapped_column(Text, default="", nullable=False)
    interview_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ApiRecord(Base, TimestampMixin):
    """Store personal API references with flexible user-defined fields."""

    __tablename__ = "api_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(20), default="GET", nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    custom_fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class UiAutomationFeature(Base, TimestampMixin):
    """Group Emote browser cases by user-visible product capability."""
    __tablename__ = "ui_automation_features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class UiAutomationRequirement(Base, TimestampMixin):
    """Store a natural-language test requirement draft."""
    __tablename__ = "ui_automation_requirements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_id: Mapped[int | None] = mapped_column(ForeignKey("ui_automation_features.id", ondelete="SET NULL"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)


class UiAutomationCase(Base, TimestampMixin):
    """Store one safe, structured Playwright browser flow."""
    __tablename__ = "ui_automation_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_id: Mapped[int] = mapped_column(ForeignKey("ui_automation_features.id", ondelete="CASCADE"), index=True, nullable=False)
    requirement_id: Mapped[int | None] = mapped_column(ForeignKey("ui_automation_requirements.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="P1", nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preconditions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    cleanup_note: Mapped[str] = mapped_column(Text, default="保留测试数据", nullable=False)
    steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UiAutomationDataSet(Base, TimestampMixin):
    """Store one reusable, server-encrypted set of UI automation runtime data."""
    __tablename__ = "ui_automation_data_sets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    encrypted_data: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UiAutomationRun(Base, TimestampMixin):
    """Persist a regression/smoke execution without runtime secrets."""
    __tablename__ = "ui_automation_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)
    branch: Mapped[str] = mapped_column(String(240), nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String(40))
    viewport: Mapped[str] = mapped_column(String(30), default="mobile", nullable=False)
    random_seed: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True, nullable=False)
    case_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    current_step: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class UiAutomationArtifact(Base, TimestampMixin):
    """Track authenticated video, screenshot and trace files."""
    __tablename__ = "ui_automation_artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("ui_automation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)


class WorkJournalEntry(Base, TimestampMixin):
    """Store one personal work log entry, always owned by a single platform user."""

    __tablename__ = "work_journal_entries"
    # The request id makes the create call idempotent when the browser retries or the user double-clicks.
    __table_args__ = (
        UniqueConstraint("owner_user_id", "client_request_id", name="uq_work_journal_entries_owner_request"),
        Index("ix_work_journal_entries_owner_date", "owner_user_id", "work_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), index=True, nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[str | None] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40), default="其他", nullable=False)
    progress_status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    # Null means "not recorded" and must never be treated as zero minutes.
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    outcome_markdown: Mapped[str | None] = mapped_column(Text)
    blocker_markdown: Mapped[str | None] = mapped_column(Text)
    next_step_markdown: Mapped[str | None] = mapped_column(Text)
    # 二期新增：日志末尾的选填备注。create_all 不会给已有表补列，由 main.py 的兼容迁移负责。
    remarks_markdown: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class WorkJournalReport(Base, TimestampMixin):
    """Store one daily or weekly report with its assembled source snapshots."""

    __tablename__ = "work_journal_reports"
    # One daily report per day and one weekly report per week per user; deleted rows keep the slot reserved.
    __table_args__ = (
        UniqueConstraint("owner_user_id", "report_type", "period_start", name="uq_work_journal_reports_owner_period"),
        Index("ix_work_journal_reports_owner_type_start", "owner_user_id", "report_type", "period_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), index=True, nullable=False)
    report_type: Mapped[str] = mapped_column(String(10), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    template_version: Mapped[str] = mapped_column(String(30), nullable=False)
    sections: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    assembled_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
