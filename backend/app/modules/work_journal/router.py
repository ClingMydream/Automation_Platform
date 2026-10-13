"""HTTP routes for the work journal module.

所有接口都要求 work_journal 菜单权限，并且只读写调用者自己的记录。
路由前缀与前端 client 约定一致：前端调用 /v1/work-journal/...，由 /api 前缀聚合。
"""

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.modules.work_journal import service
from app.modules.work_journal.schemas import (
    AssemblePreviewRead,
    AssemblePreviewRequest,
    EntryCreate,
    EntryPage,
    EntryRead,
    EntryUpdate,
    ReportCreate,
    ReportPage,
    ReportRead,
    ReportUpdate,
    RevisionInput,
)

router = APIRouter(prefix="/v1/work-journal", tags=["工作手记"])

require_journal = require_menu("work_journal")


def _markdown_response(content: str, filename: str) -> Response:
    """Return a Markdown attachment that survives non-ASCII filenames."""
    encoded = quote(filename)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


# --------------------------------------------------------------------------------------
# 工作日志
# --------------------------------------------------------------------------------------
@router.get("/entries", response_model=EntryPage, summary="查询工作日志")
def list_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(service.DEFAULT_PAGE_SIZE, ge=1, le=service.MAX_PAGE_SIZE),
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    project: str | None = None,
    tag: str | None = None,
    progress_status: str | None = None,
    category: str | None = None,
    deleted: bool = False,
    current_user: AuthContext = Depends(require_journal),
    db: Session = Depends(get_db),
):
    """List the caller's own entries with server-side filters."""
    owner = service.resolve_owner(db, current_user)
    return service.list_entries(
        db, owner, page=page, page_size=page_size, q=q, date_from=date_from, date_to=date_to,
        project=project, tag=tag, progress_status=progress_status, category=category, deleted=deleted,
    )


@router.post("/entries", response_model=EntryRead, status_code=201, summary="新增工作日志")
def create_entry(payload: EntryCreate, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Create one entry; the same client_request_id returns the existing row instead of a duplicate."""
    owner = service.resolve_owner(db, current_user)
    return service.create_entry(db, owner, payload)


@router.get("/entries/{entry_id}", response_model=EntryRead, summary="工作日志详情")
def get_entry(entry_id: int, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Return one entry that belongs to the caller."""
    owner = service.resolve_owner(db, current_user)
    return service.get_entry(db, owner, entry_id)


@router.put("/entries/{entry_id}", response_model=EntryRead, summary="修改工作日志")
def update_entry(entry_id: int, payload: EntryUpdate, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Update one entry using an optimistic revision check."""
    owner = service.resolve_owner(db, current_user)
    return service.update_entry(db, owner, entry_id, payload)


@router.delete("/entries/{entry_id}", summary="删除工作日志（软删除）")
def delete_entry(entry_id: int, revision: int = Query(..., ge=1), current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Soft delete one entry."""
    owner = service.resolve_owner(db, current_user)
    service.delete_entry(db, owner, entry_id, revision)
    return {"status": "ok"}


@router.post("/entries/{entry_id}/restore", response_model=EntryRead, summary="恢复工作日志")
def restore_entry(entry_id: int, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Restore one soft-deleted entry."""
    owner = service.resolve_owner(db, current_user)
    return service.restore_entry(db, owner, entry_id)


# --------------------------------------------------------------------------------------
# 日报 / 周报
# --------------------------------------------------------------------------------------
@router.get("/reports", response_model=ReportPage, summary="查询日报与周报")
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(service.DEFAULT_PAGE_SIZE, ge=1, le=service.MAX_PAGE_SIZE),
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    report_type: str | None = None,
    status: str | None = None,
    deleted: bool = False,
    current_user: AuthContext = Depends(require_journal),
    db: Session = Depends(get_db),
):
    """List the caller's own reports with server-side filters."""
    owner = service.resolve_owner(db, current_user)
    return service.list_reports(
        db, owner, page=page, page_size=page_size, q=q, date_from=date_from, date_to=date_to,
        report_type=report_type, status=status, deleted=deleted,
    )


@router.post("/reports", response_model=ReportRead, status_code=201, summary="新建日报或周报")
def create_report(payload: ReportCreate, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Create one empty report slot; an existing slot returns 409 with its id."""
    owner = service.resolve_owner(db, current_user)
    return service.create_report(db, owner, payload)


@router.get("/reports/{report_id}", response_model=ReportRead, summary="报告详情")
def get_report(report_id: int, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Return one report that belongs to the caller."""
    owner = service.resolve_owner(db, current_user)
    return service.get_report(db, owner, report_id)


@router.put("/reports/{report_id}", response_model=ReportRead, summary="保存报告草稿")
def update_report(report_id: int, payload: ReportUpdate, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Save report body without touching the status."""
    owner = service.resolve_owner(db, current_user)
    return service.update_report(db, owner, report_id, payload)


@router.post("/reports/{report_id}/complete", response_model=ReportRead, summary="完成报告")
def complete_report(report_id: int, payload: RevisionInput, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Validate the body then mark the report completed."""
    owner = service.resolve_owner(db, current_user)
    return service.complete_report(db, owner, report_id, payload.revision)


@router.post("/reports/{report_id}/reopen", response_model=ReportRead, summary="重新编辑报告")
def reopen_report(report_id: int, payload: RevisionInput, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Move a completed report back to draft."""
    owner = service.resolve_owner(db, current_user)
    return service.reopen_report(db, owner, report_id, payload.revision)


@router.delete("/reports/{report_id}", summary="删除报告（软删除）")
def delete_report(report_id: int, revision: int = Query(..., ge=1), current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Soft delete one report."""
    owner = service.resolve_owner(db, current_user)
    service.delete_report(db, owner, report_id, revision)
    return {"status": "ok"}


@router.post("/reports/{report_id}/restore", response_model=ReportRead, summary="恢复报告")
def restore_report(report_id: int, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Restore one soft-deleted report."""
    owner = service.resolve_owner(db, current_user)
    return service.restore_report(db, owner, report_id)


@router.post("/reports/{report_id}/assemble", response_model=ReportRead, summary="采纳汇总内容")
def assemble_into_report(
    report_id: int,
    mode: str = Query("append", pattern="^(append|replace)$"),
    include_draft_reports: bool = False,
    current_user: AuthContext = Depends(require_journal),
    db: Session = Depends(get_db),
):
    """Persist an assembled candidate body into the report using append or replace semantics."""
    owner = service.resolve_owner(db, current_user)
    report = service.get_report(db, owner, report_id)
    preview = service.assemble_preview(
        db,
        owner,
        AssemblePreviewRequest(
            report_type=report.report_type,
            period_start=report.period_start,
            include_draft_reports=include_draft_reports,
            report_id=report.id,
        ),
    )
    return service.save_assembled(db, owner, report, preview, mode)


# --------------------------------------------------------------------------------------
# 汇总 / 日历 / 筛选
# --------------------------------------------------------------------------------------
@router.post("/assemble-preview", response_model=AssemblePreviewRead, summary="汇总预览（不写库）")
def assemble_preview(payload: AssemblePreviewRequest, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Return a candidate body plus source coverage without writing anything."""
    owner = service.resolve_owner(db, current_user)
    return service.assemble_preview(db, owner, payload)


@router.get("/calendar", summary="月历标记")
def calendar(month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Return per-day markers for the month grid."""
    owner = service.resolve_owner(db, current_user)
    try:
        return service.calendar(db, owner, month)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/filters", summary="本人使用过的项目与标签")
def filters(current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Return the projects and tags this user has actually used."""
    owner = service.resolve_owner(db, current_user)
    return service.filters(db, owner)


@router.get("/summary", summary="轻量摘要")
def summary(current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Return the small header summary for the current week."""
    owner = service.resolve_owner(db, current_user)
    return service.summary(db, owner)


# --------------------------------------------------------------------------------------
# 导出
# --------------------------------------------------------------------------------------
@router.get("/entries/{entry_id}/export", summary="导出工作日志 Markdown")
def export_entry(entry_id: int, current_user: AuthContext = Depends(require_journal), db: Session = Depends(get_db)):
    """Download one entry as a Markdown file."""
    owner = service.resolve_owner(db, current_user)
    entry = service.get_entry(db, owner, entry_id)
    author = owner.display_name or owner.username
    return _markdown_response(service.entry_markdown(entry, author), f"{entry.work_date.isoformat()} {entry.title}.md")


@router.get("/reports/{report_id}/export", summary="导出报告 Markdown")
def export_report(
    report_id: int,
    body_only: bool = Query(False, description="只返回 P/R/O 正文，用于复制到外部周报工具"),
    current_user: AuthContext = Depends(require_journal),
    db: Session = Depends(get_db),
):
    """Download one report as a Markdown file, optionally without the meta block."""
    owner = service.resolve_owner(db, current_user)
    report = service.get_report(db, owner, report_id)
    author = owner.display_name or owner.username
    # 复制与导出共用同一个格式化函数，避免三套格式不一致。
    content = service.format_report_body(report) if body_only else service.report_markdown(report, author)
    return _markdown_response(content, f"{report.title}.md")
