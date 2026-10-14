"""Request and response schemas for the work journal module."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# 工作类型与进展状态是受控枚举，前端选择器与后端校验共用同一份定义。
CATEGORIES = ("测试执行", "缺陷跟进", "自动化开发", "需求评审", "学习成长", "会议沟通", "其他")
PROGRESS_STATUSES = ("in_progress", "completed", "blocked")
REPORT_TYPES = ("daily", "weekly")
REPORT_STATUSES = ("draft", "completed")

# 模板版本写入报告，便于将来兼容旧结构而不覆盖历史正文。
# 二期把「事项内容 / 状态 / 进度百分比」作为当前模板，一期结构保留为可读的旧模板。
DAILY_TEMPLATE_VERSION = "daily_v2"
WEEKLY_TEMPLATE_VERSION = "weekly_pro_v2"
V1_TEMPLATE_VERSIONS = ("daily_v1", "weekly_pro_v1")
LEGACY_TEMPLATE_VERSIONS = ("daily_legacy_v1", "weekly_legacy_v1")

# 进度只允许 0/10/…/100，后端保存数字而不是「60%」字符串。
PROGRESS_OPTIONS = tuple(range(0, 101, 10))
MAX_CONTENT_LENGTH = 5000
MAX_REMARKS_LENGTH = 10000

MAX_TAGS = 10
MAX_TAG_LENGTH = 24
MAX_BODY_LENGTH = 20000
MAX_TITLE_LENGTH = 120
MAX_PROJECT_LENGTH = 80
MAX_DURATION_MINUTES = 1440


def _clean_text(value: str | None, *, field: str, max_length: int, required: bool) -> str | None:
    """Trim text and reject blank-only values so empty strings never reach the database."""
    if value is None:
        if required:
            raise ValueError(f"{field}不能为空")
        return None
    text = value.strip()
    if not text:
        if required:
            raise ValueError(f"{field}不能为空")
        return None
    if len(text) > max_length:
        raise ValueError(f"{field}不能超过 {max_length} 字")
    return text


def _clean_tags(value: list[str] | None) -> list[str]:
    """Normalize tags: trim, drop blanks, de-duplicate while keeping the first order."""
    tags: list[str] = []
    for raw in value or []:
        tag = (raw or "").strip()
        if not tag:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise ValueError(f"标签不能超过 {MAX_TAG_LENGTH} 字")
        if tag not in tags:
            tags.append(tag)
    if len(tags) > MAX_TAGS:
        raise ValueError(f"标签最多 {MAX_TAGS} 个")
    return tags


def clean_remarks(value: Any) -> str:
    """Normalize the optional remarks field; empty stays empty and never blocks saving."""
    text = str(value or "").strip()
    if len(text) > MAX_REMARKS_LENGTH:
        raise ValueError(f"备注不能超过 {MAX_REMARKS_LENGTH} 字")
    return text


def summary_line(content: Any, limit: int = 40) -> str:
    """Use the first line of an item as its title summary, keeping the full text in 进展."""
    text = str(content or "").strip()
    if not text:
        return ""
    first = text.splitlines()[0].strip()
    return first if len(first) <= limit else f"{first[:limit]}…"


def normalize_progress(value: Any) -> int | None:
    """Validate a progress value; booleans and strings are rejected so the API stays type-safe."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("进度必须是整数百分比")
    if value not in PROGRESS_OPTIONS:
        raise ValueError("进度必须是 0 到 100 之间 10 的倍数")
    return value


def normalize_status(value: Any) -> str:
    """Validate the status enum."""
    if value not in PROGRESS_STATUSES:
        raise ValueError("状态必须是 in_progress、completed 或 blocked")
    return value


def normalize_item(item: Any, *, require_progress: bool) -> dict[str, Any]:
    """Normalize one item and keep status/percentage consistent.

    已完成必须是 100%，100% 必须对应已完成；其余状态只允许 0–90%。
    草稿允许进度为空（历史数据里进行中事项的百分比本来就未知）。
    """
    if not isinstance(item, dict):
        raise ValueError("事项必须是对象")
    content = _clean_text(item.get("content"), field="事项内容", max_length=MAX_CONTENT_LENGTH, required=True)
    status = normalize_status(item.get("status"))
    percent = normalize_progress(item.get("progress_percent"))
    if percent is None:
        if require_progress:
            raise ValueError("请为每个事项选择进度")
    elif status == "completed" and percent != 100:
        raise ValueError("已完成事项的进度必须是 100%")
    elif status != "completed" and percent == 100:
        raise ValueError("进度 100% 必须对应已完成状态")
    return {"content": content, "status": status, "progress_percent": percent}


class EntryPayload(BaseModel):
    """Shared editable fields for creating and updating one work log entry."""

    work_date: date
    title: str
    body_markdown: str
    project: str | None = None
    category: str = "其他"
    progress_status: str = "in_progress"
    duration_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    outcome_markdown: str | None = None
    blocker_markdown: str | None = None
    next_step_markdown: str | None = None
    remarks_markdown: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _check_title(cls, value: Any) -> Any:
        return _clean_text(value if isinstance(value, str) else None, field="标题", max_length=MAX_TITLE_LENGTH, required=True)

    @field_validator("body_markdown", mode="before")
    @classmethod
    def _check_body(cls, value: Any) -> Any:
        return _clean_text(value if isinstance(value, str) else None, field="内容", max_length=MAX_BODY_LENGTH, required=True)

    @field_validator("project", mode="before")
    @classmethod
    def _check_project(cls, value: Any) -> Any:
        return _clean_text(value if isinstance(value, str) else None, field="项目", max_length=MAX_PROJECT_LENGTH, required=False)

    @field_validator("outcome_markdown", "blocker_markdown", "next_step_markdown", mode="before")
    @classmethod
    def _check_optional_markdown(cls, value: Any) -> Any:
        return _clean_text(value if isinstance(value, str) else None, field="补充内容", max_length=MAX_BODY_LENGTH, required=False)

    @field_validator("remarks_markdown", mode="before")
    @classmethod
    def _check_remarks(cls, value: Any) -> Any:
        text = clean_remarks(value)
        return text or None

    @field_validator("category")
    @classmethod
    def _check_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError(f"工作类型必须是 {'、'.join(CATEGORIES)} 之一")
        return value

    @field_validator("progress_status")
    @classmethod
    def _check_progress(cls, value: str) -> str:
        if value not in PROGRESS_STATUSES:
            raise ValueError("进展状态必须是 in_progress、completed 或 blocked")
        return value

    @field_validator("duration_minutes")
    @classmethod
    def _check_duration(cls, value: int | None) -> int | None:
        # 留空表示未记录，必须与 0 分钟区分开。
        if value is None:
            return None
        if value < 0 or value > MAX_DURATION_MINUTES:
            raise ValueError(f"工时必须在 0 到 {MAX_DURATION_MINUTES} 分钟之间")
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def _check_tags(cls, value: Any) -> Any:
        return _clean_tags(value if isinstance(value, list) else [])


class EntryCreate(EntryPayload):
    """Create one entry; client_request_id keeps retries idempotent."""

    client_request_id: str = Field(min_length=8, max_length=36)


class EntryUpdate(EntryPayload):
    """Update one entry with the revision the client last read."""

    revision: int = Field(ge=1)


class EntryRead(BaseModel):
    """Serialize one entry back to the client."""

    id: int
    work_date: date
    title: str
    body_markdown: str
    project: str | None
    category: str
    progress_status: str
    duration_minutes: int | None
    tags: list[str]
    outcome_markdown: str | None
    blocker_markdown: str | None
    next_step_markdown: str | None
    remarks_markdown: str | None = None
    revision: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class EntryPage(BaseModel):
    """Paged entry list matching the platform list contract."""

    items: list[EntryRead]
    total: int
    page: int
    page_size: int


class ReportCreate(BaseModel):
    """Create one empty daily or weekly report slot."""

    report_type: str
    period_start: date
    title: str | None = None

    @field_validator("report_type")
    @classmethod
    def _check_type(cls, value: str) -> str:
        if value not in REPORT_TYPES:
            raise ValueError("报告类型必须是 daily 或 weekly")
        return value


class ReportUpdate(BaseModel):
    """Save report body, status stays untouched."""

    title: str
    sections: dict[str, Any]
    revision: int = Field(ge=1)

    @field_validator("title", mode="before")
    @classmethod
    def _check_title(cls, value: Any) -> Any:
        return _clean_text(value if isinstance(value, str) else None, field="标题", max_length=200, required=True)


class ReportRead(BaseModel):
    """Serialize one report including its source snapshots."""

    id: int
    report_type: str
    period_start: date
    period_end: date
    title: str
    template_version: str
    sections: dict[str, Any]
    status: str
    source_refs: list[Any]
    assembled_at: datetime | None
    completed_at: datetime | None
    revision: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportPage(BaseModel):
    """Paged report list matching the platform list contract."""

    items: list[ReportRead]
    total: int
    page: int
    page_size: int


class RevisionInput(BaseModel):
    """Carry the expected revision for complete/reopen style transitions."""

    revision: int = Field(ge=1)


class AssemblePreviewRequest(BaseModel):
    """Ask the backend to build a candidate report body without writing to the database."""

    report_type: str
    period_start: date
    include_draft_reports: bool = False
    report_id: int | None = None

    @field_validator("report_type")
    @classmethod
    def _check_type(cls, value: str) -> str:
        if value not in REPORT_TYPES:
            raise ValueError("报告类型必须是 daily 或 weekly")
        return value


class AssemblePreviewRead(BaseModel):
    """Return the candidate body plus the source coverage the client must display."""

    report_type: str
    period_start: date
    period_end: date
    template_version: str
    sections: dict[str, Any]
    source_refs: list[Any]
    source_count: int
    missing_dates: list[str]
    warnings: list[str]
    totals: dict[str, Any]
    already_referenced: list[Any] = Field(default_factory=list)
    as_of: str | None = None
    generated_at: datetime
