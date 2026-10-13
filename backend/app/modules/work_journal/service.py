"""Business logic for the work journal module.

设计要点：
- 归属只从认证上下文推导：AuthContext 只带 username，owner_user_id 一律由后端查询，绝不采信前端传值。
- 所有读写都带 owner_user_id 条件，管理员在本模块同样只能看到自己的记录。
- 更新使用带 owner/id/revision 条件的原子 UPDATE 并 revision+1，不做"先读再无条件写"。
- 删除是软删除；日报/周报唯一键不含删除状态，因此删除后同日再次创建应引导恢复。
"""

from datetime import date, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.core.auth import AuthContext
from app.models.entities import AppUser, WorkJournalEntry, WorkJournalReport
from app.modules.work_journal import assemble
from app.modules.work_journal.dates import (
    date_range,
    month_bounds,
    now_utc,
    today_shanghai,
    week_range,
)
from app.modules.work_journal.schemas import (
    DAILY_TEMPLATE_VERSION,
    LEGACY_TEMPLATE_VERSIONS,
    REPORT_TYPES,
    WEEKLY_TEMPLATE_VERSION,
    AssemblePreviewRequest,
    EntryCreate,
    EntryUpdate,
    ReportCreate,
    ReportUpdate,
)

PROGRESS_LABELS = {"in_progress": "进行中", "completed": "已完成", "blocked": "受阻"}
STATUS_LABELS = {"draft": "草稿", "completed": "已完成"}
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


# --------------------------------------------------------------------------------------
# 归属与通用工具
# --------------------------------------------------------------------------------------
def resolve_owner(db: Session, current_user: AuthContext) -> AppUser:
    """Resolve the persisted user row for the authenticated identity."""
    user = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="登录用户不存在")
    return user


def _paginate(page: int, page_size: int) -> tuple[int, int]:
    """Clamp paging input to the platform contract."""
    safe_page = max(1, page or 1)
    safe_size = min(MAX_PAGE_SIZE, max(1, page_size or DEFAULT_PAGE_SIZE))
    return safe_page, safe_size


def _atomic_update(
    db: Session,
    model: Any,
    *,
    owner_id: int,
    record_id: int,
    revision: int | None,
    values: dict[str, Any],
    require_status: str | None = None,
) -> None:
    """Run a conditional atomic UPDATE and translate a zero row count into 404/409."""
    query = db.query(model).filter(
        model.id == record_id,
        model.owner_user_id == owner_id,
        model.deleted_at.is_(None),
    )
    if require_status is not None:
        query = query.filter(model.status == require_status)
    if revision is not None:
        query = query.filter(model.revision == revision)
    updated = query.update(
        {**values, "revision": model.revision + 1, "updated_at": now_utc()},
        synchronize_session=False,
    )
    if updated:
        db.commit()
        return
    db.rollback()
    exists = (
        db.query(model.id)
        .filter(model.id == record_id, model.owner_user_id == owner_id, model.deleted_at.is_(None))
        .first()
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    # 记录存在但条件未命中：revision 过期或当前状态不允许该操作。
    raise HTTPException(status_code=409, detail="记录已被修改，请刷新后重试")


def _require_owned(db: Session, model: Any, owner_id: int, record_id: int, *, include_deleted: bool = False) -> Any:
    """Load one record that must belong to the owner, otherwise behave as 404."""
    query = db.query(model).filter(model.id == record_id, model.owner_user_id == owner_id)
    if not include_deleted:
        query = query.filter(model.deleted_at.is_(None))
    record = query.first()
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


# --------------------------------------------------------------------------------------
# 工作日志
# --------------------------------------------------------------------------------------
def _entry_values(payload: EntryCreate | EntryUpdate) -> dict[str, Any]:
    """Convert a validated payload into column values."""
    return {
        "work_date": payload.work_date,
        "title": payload.title,
        "body_markdown": payload.body_markdown,
        "project": payload.project,
        "category": payload.category,
        "progress_status": payload.progress_status,
        "duration_minutes": payload.duration_minutes,
        "tags": list(payload.tags),
        "outcome_markdown": payload.outcome_markdown,
        "blocker_markdown": payload.blocker_markdown,
        "next_step_markdown": payload.next_step_markdown,
    }


def _reject_future_date(work_date: date) -> None:
    """First release disallows future work dates so reports never point at unworked days."""
    if work_date > today_shanghai():
        raise HTTPException(status_code=422, detail="工作日期不能晚于今天（北京时间）")


def create_entry(db: Session, owner: AppUser, payload: EntryCreate) -> WorkJournalEntry:
    """Create one entry; retries with the same client_request_id return the existing row."""
    existing = (
        db.query(WorkJournalEntry)
        .filter(
            WorkJournalEntry.owner_user_id == owner.id,
            WorkJournalEntry.client_request_id == payload.client_request_id,
        )
        .first()
    )
    if existing is not None:
        return existing
    _reject_future_date(payload.work_date)
    entry = WorkJournalEntry(owner_user_id=owner.id, client_request_id=payload.client_request_id, revision=1, **_entry_values(payload))
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_entries(
    db: Session,
    owner: AppUser,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    project: str | None = None,
    tag: str | None = None,
    progress_status: str | None = None,
    category: str | None = None,
    deleted: bool = False,
) -> dict[str, Any]:
    """List the owner's entries with server-side filtering so filters never only trim one page."""
    safe_page, safe_size = _paginate(page, page_size)
    query = db.query(WorkJournalEntry).filter(WorkJournalEntry.owner_user_id == owner.id)
    query = query.filter(WorkJournalEntry.deleted_at.isnot(None) if deleted else WorkJournalEntry.deleted_at.is_(None))
    if date_from is not None:
        query = query.filter(WorkJournalEntry.work_date >= date_from)
    if date_to is not None:
        query = query.filter(WorkJournalEntry.work_date <= date_to)
    if project:
        query = query.filter(WorkJournalEntry.project == project)
    if progress_status:
        query = query.filter(WorkJournalEntry.progress_status == progress_status)
    if category:
        query = query.filter(WorkJournalEntry.category == category)
    if tag:
        # 标签存 JSON 数组；用 cast 成文本做包含匹配，兼容 SQLite 与 MySQL。
        query = query.filter(cast(WorkJournalEntry.tags, String).like(f'%"{tag}"%'))
    if q:
        keyword = f"%{q.strip()}%"
        query = query.filter(or_(WorkJournalEntry.title.like(keyword), WorkJournalEntry.body_markdown.like(keyword)))
    total = query.count()
    items = (
        query.order_by(WorkJournalEntry.work_date.desc(), WorkJournalEntry.created_at.desc(), WorkJournalEntry.id.desc())
        .offset((safe_page - 1) * safe_size)
        .limit(safe_size)
        .all()
    )
    return {"items": items, "total": total, "page": safe_page, "page_size": safe_size}


def get_entry(db: Session, owner: AppUser, entry_id: int) -> WorkJournalEntry:
    """Load one entry owned by the caller."""
    return _require_owned(db, WorkJournalEntry, owner.id, entry_id)


def update_entry(db: Session, owner: AppUser, entry_id: int, payload: EntryUpdate) -> WorkJournalEntry:
    """Update an entry with an optimistic revision check."""
    _reject_future_date(payload.work_date)
    _atomic_update(db, WorkJournalEntry, owner_id=owner.id, record_id=entry_id, revision=payload.revision, values=_entry_values(payload))
    return get_entry(db, owner, entry_id)


def delete_entry(db: Session, owner: AppUser, entry_id: int, revision: int) -> None:
    """Soft delete one entry after checking the revision."""
    _atomic_update(db, WorkJournalEntry, owner_id=owner.id, record_id=entry_id, revision=revision, values={"deleted_at": now_utc()})


def restore_entry(db: Session, owner: AppUser, entry_id: int) -> WorkJournalEntry:
    """Restore a soft-deleted entry, keeping version checks honest."""
    record = _require_owned(db, WorkJournalEntry, owner.id, entry_id, include_deleted=True)
    if record.deleted_at is None:
        return record
    record.deleted_at = None
    record.revision += 1
    record.updated_at = now_utc()
    db.commit()
    db.refresh(record)
    return record


# --------------------------------------------------------------------------------------
# 日报 / 周报
# --------------------------------------------------------------------------------------
def _period_bounds(report_type: str, period_start: date) -> tuple[date, date]:
    """Normalize the period for a report type and validate the weekday rule."""
    if report_type == "daily":
        return period_start, period_start
    monday, sunday = week_range(period_start)
    if monday != period_start:
        raise HTTPException(status_code=422, detail="周报的 period_start 必须是周一")
    return monday, sunday


def default_report_title(report_type: str, period_start: date, period_end: date) -> str:
    """Build the default report title."""
    if report_type == "daily":
        return f"{period_start.isoformat()} 工作日报"
    return f"{period_start.isoformat()} ～ {period_end.isoformat()} 工作周报"


def empty_sections(report_type: str) -> dict[str, Any]:
    """Return the empty body for a report type."""
    if report_type == "daily":
        return {"items": [], "quality": "", "blockers": [], "next_plan": [], "reflection": ""}
    return {"p_items": [], "r_items": [], "o_items": []}


def template_version_for(report_type: str) -> str:
    """Return the current template version for a report type."""
    return DAILY_TEMPLATE_VERSION if report_type == "daily" else WEEKLY_TEMPLATE_VERSION


def create_report(db: Session, owner: AppUser, payload: ReportCreate) -> WorkJournalReport:
    """Create one report slot; an existing slot (even deleted) yields 409 with its id."""
    period_start, period_end = _period_bounds(payload.report_type, payload.period_start)
    existing = (
        db.query(WorkJournalReport)
        .filter(
            WorkJournalReport.owner_user_id == owner.id,
            WorkJournalReport.report_type == payload.report_type,
            WorkJournalReport.period_start == period_start,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={"message": "该周期已存在报告", "report_id": existing.id, "deleted": existing.deleted_at is not None},
        )
    report = WorkJournalReport(
        owner_user_id=owner.id,
        report_type=payload.report_type,
        period_start=period_start,
        period_end=period_end,
        title=payload.title or default_report_title(payload.report_type, period_start, period_end),
        template_version=template_version_for(payload.report_type),
        sections=empty_sections(payload.report_type),
        status="draft",
        source_refs=[],
        revision=1,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def list_reports(
    db: Session,
    owner: AppUser,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    report_type: str | None = None,
    status: str | None = None,
    deleted: bool = False,
) -> dict[str, Any]:
    """List the owner's reports with server-side filtering."""
    safe_page, safe_size = _paginate(page, page_size)
    query = db.query(WorkJournalReport).filter(WorkJournalReport.owner_user_id == owner.id)
    query = query.filter(WorkJournalReport.deleted_at.isnot(None) if deleted else WorkJournalReport.deleted_at.is_(None))
    if report_type:
        if report_type not in REPORT_TYPES:
            raise HTTPException(status_code=422, detail="报告类型必须是 daily 或 weekly")
        query = query.filter(WorkJournalReport.report_type == report_type)
    if status:
        query = query.filter(WorkJournalReport.status == status)
    if date_from is not None:
        query = query.filter(WorkJournalReport.period_start >= date_from)
    if date_to is not None:
        query = query.filter(WorkJournalReport.period_start <= date_to)
    if q:
        keyword = f"%{q.strip()}%"
        query = query.filter(
            or_(WorkJournalReport.title.like(keyword), cast(WorkJournalReport.sections, String).like(keyword))
        )
    total = query.count()
    items = (
        query.order_by(WorkJournalReport.period_start.desc(), WorkJournalReport.id.desc())
        .offset((safe_page - 1) * safe_size)
        .limit(safe_size)
        .all()
    )
    return {"items": items, "total": total, "page": safe_page, "page_size": safe_size}


def get_report(db: Session, owner: AppUser, report_id: int) -> WorkJournalReport:
    """Load one report owned by the caller."""
    return _require_owned(db, WorkJournalReport, owner.id, report_id)


def update_report(db: Session, owner: AppUser, report_id: int, payload: ReportUpdate) -> WorkJournalReport:
    """Save report body; completed reports must be reopened first."""
    report = get_report(db, owner, report_id)
    if report.status == "completed":
        raise HTTPException(status_code=409, detail="已完成报告需先重新编辑才能修改")
    validate_sections(report.report_type, report.template_version, payload.sections)
    # sections 是 JSON 列，必须整体赋新对象，SQLAlchemy 才能检测到变更。
    _atomic_update(
        db,
        WorkJournalReport,
        owner_id=owner.id,
        record_id=report_id,
        revision=payload.revision,
        values={"title": payload.title, "sections": dict(payload.sections)},
        require_status="draft",
    )
    return get_report(db, owner, report_id)


def validate_sections(report_type: str, template_version: str, sections: dict[str, Any] | None) -> None:
    """Validate the JSON body shape for the current templates; legacy bodies pass through untouched."""
    if template_version in LEGACY_TEMPLATE_VERSIONS:
        return
    if not isinstance(sections, dict):
        raise HTTPException(status_code=422, detail="正文结构不合法")
    if report_type == "daily":
        for key, expected in (("items", list), ("blockers", list), ("next_plan", list)):
            if not isinstance(sections.get(key, []), expected):
                raise HTTPException(status_code=422, detail=f"日报 {key} 必须是数组")
        for key in ("quality", "reflection"):
            if not isinstance(sections.get(key, ""), str):
                raise HTTPException(status_code=422, detail=f"日报 {key} 必须是文本")
    else:
        for key in ("p_items", "r_items", "o_items"):
            if not isinstance(sections.get(key, []), list):
                raise HTTPException(status_code=422, detail=f"周报 {key} 必须是数组")


def completion_gap(report_type: str, sections: dict[str, Any]) -> str | None:
    """Return the blocking reason when a report cannot be completed, else None."""
    if report_type == "daily":
        items = sections.get("items") or []
        filled = [item for item in items if str(item.get("name") or "").strip() and str(item.get("progress") or "").strip()]
        if not filled:
            return "请至少在「今日完成」中填写一个事项的名称与进展"
        return None
    items = sections.get("p_items") or []
    filled = [
        item
        for item in items
        if str(item.get("name") or "").strip()
        and str(item.get("progress") or "").strip()
        and str(item.get("result") or "").strip()
    ]
    if not filled:
        return "请至少填写一个核心事项的名称、进展与结果（结果未定可写「结果待确认」）"
    return None


def complete_report(db: Session, owner: AppUser, report_id: int, revision: int) -> WorkJournalReport:
    """Validate the body then flip the report to completed."""
    report = get_report(db, owner, report_id)
    if report.status == "completed":
        raise HTTPException(status_code=409, detail="报告已完成")
    gap = completion_gap(report.report_type, report.sections or {})
    if gap:
        raise HTTPException(status_code=422, detail=gap)
    _atomic_update(
        db,
        WorkJournalReport,
        owner_id=owner.id,
        record_id=report_id,
        revision=revision,
        values={"status": "completed", "completed_at": now_utc()},
        require_status="draft",
    )
    return get_report(db, owner, report_id)


def reopen_report(db: Session, owner: AppUser, report_id: int, revision: int) -> WorkJournalReport:
    """Move a completed report back to draft so it can be edited again."""
    _atomic_update(
        db,
        WorkJournalReport,
        owner_id=owner.id,
        record_id=report_id,
        revision=revision,
        values={"status": "draft", "completed_at": None},
        require_status="completed",
    )
    return get_report(db, owner, report_id)


def delete_report(db: Session, owner: AppUser, report_id: int, revision: int) -> None:
    """Soft delete one report."""
    _atomic_update(db, WorkJournalReport, owner_id=owner.id, record_id=report_id, revision=revision, values={"deleted_at": now_utc()})


def restore_report(db: Session, owner: AppUser, report_id: int) -> WorkJournalReport:
    """Restore a soft-deleted report."""
    record = _require_owned(db, WorkJournalReport, owner.id, report_id, include_deleted=True)
    if record.deleted_at is None:
        return record
    record.deleted_at = None
    record.revision += 1
    record.updated_at = now_utc()
    db.commit()
    db.refresh(record)
    return record


def save_assembled(db: Session, owner: AppUser, report: WorkJournalReport, preview: dict[str, Any], mode: str) -> WorkJournalReport:
    """Persist an assembled candidate body into the report using append or replace semantics."""
    if report.status == "completed":
        raise HTTPException(status_code=409, detail="已完成报告需先重新编辑")
    if mode not in {"append", "replace"}:
        raise HTTPException(status_code=422, detail="mode 必须是 append 或 replace")
    current = report.sections or {}
    if mode == "replace":
        # 重新生成：以来源 item ID 更新未人工修改的生成块，人工修改块保留，且不新增重复事项。
        sections = assemble.merge_regenerated(report.report_type, current, preview["sections"])
    else:
        sections = assemble.merge_sections(report.report_type, current, preview["sections"])
    report.title = report.title or default_report_title(report.report_type, report.period_start, report.period_end)
    report.sections = dict(sections)
    report.source_refs = list(preview["source_refs"])
    report.assembled_at = now_utc()
    report.revision += 1
    report.updated_at = now_utc()
    db.commit()
    db.refresh(report)
    return report


# --------------------------------------------------------------------------------------
# 日历 / 筛选项 / 汇总
# --------------------------------------------------------------------------------------
def calendar(db: Session, owner: AppUser, month: str) -> dict[str, Any]:
    """Return per-day markers for the owner's month view."""
    first, last, day_count = month_bounds(month)
    # 月视图必须把跨越本月边界的周补齐，否则跨周记录会漏掉。
    grid_start = week_range(first)[0]
    grid_end = week_range(last)[1]
    entries = (
        db.query(WorkJournalEntry)
        .filter(
            WorkJournalEntry.owner_user_id == owner.id,
            WorkJournalEntry.deleted_at.is_(None),
            WorkJournalEntry.work_date >= grid_start,
            WorkJournalEntry.work_date <= grid_end,
        )
        .all()
    )
    reports = (
        db.query(WorkJournalReport)
        .filter(
            WorkJournalReport.owner_user_id == owner.id,
            WorkJournalReport.report_type == "daily",
            WorkJournalReport.deleted_at.is_(None),
        )
        .all()
    )
    entry_counts: dict[str, int] = {}
    for entry in entries:
        key = entry.work_date.isoformat()
        entry_counts[key] = entry_counts.get(key, 0) + 1
    report_status = {report.period_start.isoformat(): report.status for report in reports}
    days = [
        {"date": day.isoformat(), "entry_count": entry_counts.get(day.isoformat(), 0), "daily_status": report_status.get(day.isoformat())}
        for day in date_range(first, last)
    ]
    return {"month": month, "first": first.isoformat(), "last": last.isoformat(), "day_count": day_count, "grid_start": grid_start.isoformat(), "grid_end": grid_end.isoformat(), "days": days}


def filters(db: Session, owner: AppUser) -> dict[str, Any]:
    """Return the projects and tags this user has actually used."""
    projects = [
        row[0]
        for row in db.query(WorkJournalEntry.project)
        .filter(WorkJournalEntry.owner_user_id == owner.id, WorkJournalEntry.deleted_at.is_(None), WorkJournalEntry.project.isnot(None))
        .distinct()
        .order_by(WorkJournalEntry.project)
        .all()
        if row[0]
    ]
    tag_rows = (
        db.query(WorkJournalEntry.tags)
        .filter(WorkJournalEntry.owner_user_id == owner.id, WorkJournalEntry.deleted_at.is_(None))
        .all()
    )
    tags: list[str] = []
    for (values,) in tag_rows:
        for tag in values or []:
            if tag not in tags:
                tags.append(tag)
    return {"projects": projects, "tags": sorted(tags)}


def summary(db: Session, owner: AppUser, reference: date | None = None) -> dict[str, Any]:
    """Return the lightweight header summary for the current week."""
    anchor = reference or today_shanghai()
    monday, sunday = week_range(anchor)
    entry_count = (
        db.query(func.count(WorkJournalEntry.id))
        .filter(
            WorkJournalEntry.owner_user_id == owner.id,
            WorkJournalEntry.deleted_at.is_(None),
            WorkJournalEntry.work_date >= monday,
            WorkJournalEntry.work_date <= sunday,
        )
        .scalar()
        or 0
    )
    completed_daily = (
        db.query(func.count(WorkJournalReport.id))
        .filter(
            WorkJournalReport.owner_user_id == owner.id,
            WorkJournalReport.report_type == "daily",
            WorkJournalReport.status == "completed",
            WorkJournalReport.deleted_at.is_(None),
            WorkJournalReport.period_start >= monday,
            WorkJournalReport.period_start <= sunday,
        )
        .scalar()
        or 0
    )
    weekly = (
        db.query(WorkJournalReport)
        .filter(
            WorkJournalReport.owner_user_id == owner.id,
            WorkJournalReport.report_type == "weekly",
            WorkJournalReport.period_start == monday,
            WorkJournalReport.deleted_at.is_(None),
        )
        .first()
    )
    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "week_entry_count": int(entry_count),
        "completed_daily_count": int(completed_daily),
        "weekly_status": weekly.status if weekly else None,
        "weekly_report_id": weekly.id if weekly else None,
    }


def assemble_preview(db: Session, owner: AppUser, payload: AssemblePreviewRequest) -> dict[str, Any]:
    """Build a candidate report body from the owner's own sources without writing anything."""
    period_start, period_end = _period_bounds(payload.report_type, payload.period_start)
    return assemble.build_preview(
        db,
        owner,
        report_type=payload.report_type,
        period_start=period_start,
        period_end=period_end,
        include_draft_reports=payload.include_draft_reports,
        report_id=payload.report_id,
    )


# --------------------------------------------------------------------------------------
# 导出
# --------------------------------------------------------------------------------------
def entry_markdown(entry: WorkJournalEntry, author: str) -> str:
    """Render one entry as Markdown."""
    lines = [f"# {entry.title}", ""]
    lines.append(f"- 工作日期：{entry.work_date.isoformat()}")
    lines.append(f"- 工作类型：{entry.category}")
    lines.append(f"- 进展状态：{PROGRESS_LABELS.get(entry.progress_status, entry.progress_status)}")
    if entry.project:
        lines.append(f"- 项目：{entry.project}")
    if entry.duration_minutes is not None:
        lines.append(f"- 工时：{entry.duration_minutes} 分钟")
    if entry.tags:
        lines.append(f"- 标签：{'、'.join(entry.tags)}")
    lines.append(f"- 作者：{author}")
    lines.append("")
    lines.append("## 内容")
    lines.append(entry.body_markdown or "")
    for heading, value in (("结果与产出", entry.outcome_markdown), ("风险与阻碍", entry.blocker_markdown), ("下一步", entry.next_step_markdown)):
        if value:
            lines.extend(["", f"## {heading}", value])
    return "\n".join(lines).strip() + "\n"


def report_markdown(report: WorkJournalReport, author: str) -> str:
    """Render a report as Markdown using the shared formatter so copy and export always match."""
    return format_report_markdown(report, author, include_meta=True)


def format_report_body(report: WorkJournalReport) -> str:
    """Render only the report body, used by the "copy weekly body" action."""
    return format_report_markdown(report, author=None, include_meta=False)


def format_report_markdown(report: WorkJournalReport, author: str | None, *, include_meta: bool) -> str:
    """Render the report body; meta lines stay optional so copied text stays paste-ready."""
    sections = report.sections or {}
    if report.template_version in LEGACY_TEMPLATE_VERSIONS:
        legacy_body = str(sections.get("body") or sections.get("markdown") or "").strip()
        head = f"# {report.title}" if include_meta else ""
        meta = _meta_lines(report, author) if include_meta else []
        return "\n".join([line for line in [head, *meta, "", legacy_body] if line is not None]).strip() + "\n"

    lines: list[str] = []
    if include_meta:
        lines.append(f"# {report.title}")
        lines.extend(_meta_lines(report, author))
        lines.append("")

    if report.report_type == "daily":
        lines.append("## 今日完成")
        items = sections.get("items") or []
        if items:
            for item in items:
                name = str(item.get("name") or "").strip()
                project = str(item.get("project") or "").strip()
                suffix = f"（{project}）" if project else ""
                lines.append(f"- **{name}**{suffix}")
                lines.append(f"  - 进展：{str(item.get('progress') or '').strip()}")
                lines.append(f"  - 结果：{str(item.get('result') or '').strip() or '结果待确认'}")
                if item.get("status"):
                    lines.append(f"  - 状态：{PROGRESS_LABELS.get(item.get('status'), item.get('status'))}")
        else:
            lines.append("- 未填写")
        for heading, key in (("测试与质量", "quality"), ("成长与复盘", "reflection")):
            lines.extend(["", f"## {heading}", str(sections.get(key) or "").strip() or "未填写"])
        for heading, key in (("风险与阻碍", "blockers"), ("明日计划", "next_plan")):
            lines.extend(["", f"## {heading}"])
            rows = sections.get(key) or []
            if rows:
                for row in rows:
                    text = str(row.get("text") or "").strip()
                    if not text:
                        continue
                    if key == "blockers" and row.get("resolved"):
                        text += "（已解决）"
                    lines.append(f"- {text}")
            else:
                lines.append("未填写")
        return "\n".join(lines).strip() + "\n"

    # 周报固定 P / R / O 三段，编号与「● 进展 / ● 结果」标签不能改。
    lines.append("# P-核心进展与结果:")
    lines.append("")
    p_items = [item for item in (sections.get("p_items") or [])]
    if p_items:
        for index, item in enumerate(p_items, start=1):
            name = str(item.get("name") or "").strip()
            lines.append(f"**事项{chinese_index(index)}：{name}**")
            lines.append("")
            lines.append(f"● 进展：{str(item.get('progress') or '').strip()}")
            lines.append("")
            lines.append(f"● 结果：{str(item.get('result') or '').strip() or '结果待确认'}")
            lines.append("")
    else:
        lines.extend(["未填写", ""])
    lines.append("# R-需要关注的风险与问题:")
    lines.append("")
    r_items = sections.get("r_items") or []
    if r_items:
        for item in r_items:
            lines.append(f"● {str(item.get('text') or '').strip()}")
    else:
        lines.append("● 本周日报未记录风险与问题，待确认")
    lines.append("")
    lines.append("# O-下周核心目标与计划:")
    lines.append("")
    o_items = sections.get("o_items") or []
    if o_items:
        for item in o_items:
            lines.append(f"● {str(item.get('text') or '').strip()}")
    else:
        lines.append("● 下周计划待补充")
    return "\n".join(lines).strip() + "\n"


def _meta_lines(report: WorkJournalReport, author: str | None) -> list[str]:
    """Build the optional meta block shared by exports."""
    lines = [f"- 周期：{report.period_start.isoformat()} ～ {report.period_end.isoformat()}", f"- 状态：{STATUS_LABELS.get(report.status, report.status)}"]
    if author:
        lines.append(f"- 作者：{author}")
    return lines


def chinese_index(index: int) -> str:
    """Return 一/二/…/十 for the first ten items and the Arabic numeral afterwards."""
    digits = "一二三四五六七八九十"
    return digits[index - 1] if 1 <= index <= 10 else str(index)
