"""Deterministic assembly rules for daily and weekly reports.

本模块不依赖任何外部 AI：全部使用结构化字段与确定性规则。
所有推断都必须可追溯到来源，缺少依据时一律标注"待确认"，不得补造成果。

周报正文严格固定为 P / R / O 三段，事项编号与「● 进展 / ● 结果」标签由 service.format_report_markdown 输出。
"""

import re
import uuid
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AppUser, WorkJournalEntry, WorkJournalReport
from app.modules.work_journal.dates import date_range, now_utc, today_shanghai
from app.modules.work_journal.schemas import (
    DAILY_TEMPLATE_VERSION,
    LEGACY_TEMPLATE_VERSIONS,
    PROGRESS_OPTIONS,
    PROGRESS_STATUSES,
    V1_TEMPLATE_VERSIONS,
    WEEKLY_TEMPLATE_VERSION,
    summary_line,
)

NO_RESULT_TEXT = "结果待确认（日报未记录明确结果）"
CONFLICT_RESULT_TEXT = "结果存在差异，待确认"
NO_RISK_TEXT = "本周日报未记录风险与问题，待确认"
NO_PLAN_TEXT = "下周计划待补充"

# 只有出现这些明确措辞时才认为"较晚的记录更正了之前的结果"；否则判为矛盾并列原句。
CORRECTION_MARKERS = ("更正", "修正", "改为", "实际为", "实际是", "应为", "最终", "订正", "纠正")

TEST_CATEGORIES = {"测试执行", "缺陷跟进"}
REFLECTION_CATEGORIES = {"学习成长"}

_SENTENCE_SPLIT = re.compile(r"[\n。；;]+")


def normalize(text: Any) -> str:
    """Collapse whitespace so equal content compares equal."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _group_key(name: str, project: str) -> tuple[str, str]:
    """P items group by project plus the trimmed item name; identical names in different projects stay apart."""
    return normalize(project), normalize(name)


def split_sentences(text: Any) -> list[str]:
    """Split free text into sentences for de-duplication."""
    return [normalize(part) for part in _SENTENCE_SPLIT.split(str(text or "")) if normalize(part)]


def dedupe_sentences(parts: list[str]) -> list[str]:
    """Remove exactly duplicated sentences while preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        text = normalize(part)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _new_id() -> str:
    """Return a fresh identifier for a generated block."""
    return str(uuid.uuid4())


def legacy_body(report: WorkJournalReport) -> str:
    """Read the raw text kept by a pre-P/R/O report."""
    sections = report.sections or {}
    return str(sections.get("body") or sections.get("markdown") or "").strip()


def is_legacy(report: WorkJournalReport) -> bool:
    """Return whether the report still uses a pre-P/R/O template."""
    return (report.template_version or "") in LEGACY_TEMPLATE_VERSIONS


def _existing_blocks(report: WorkJournalReport | None, key: str) -> list[dict[str, Any]]:
    """Read a generated block list from the report being regenerated."""
    if report is None:
        return []
    sections = report.sections or {}
    rows = sections.get(key)
    return list(rows) if isinstance(rows, list) else []


def _reuse_by_entry(previous: list[dict[str, Any]], entry_id: int) -> str | None:
    """Reuse the stable id of a previously assembled daily item sourced from the same log."""
    for block in previous:
        for ref in block.get("source_refs") or []:
            if ref.get("entry_id") == entry_id:
                return block.get("item_id")
    return None


def _reuse_id(previous: list[dict[str, Any]], refs: list[dict[str, Any]]) -> str | None:
    """Find the stable id of a previously generated block that shares a source item."""
    wanted = {(ref.get("report_id"), ref.get("item_id")) for ref in refs}
    for block in previous:
        existing = {(ref.get("report_id"), ref.get("item_id")) for ref in block.get("source_item_refs") or []}
        if existing & wanted:
            return block.get("item_id") or block.get("id")
    return None


# --------------------------------------------------------------------------------------
# 日报
# --------------------------------------------------------------------------------------
def _build_daily(db: Session, owner: AppUser, work_date: date, report: WorkJournalReport | None) -> dict[str, Any]:
    """Assemble a daily candidate from the day's own log entries (二期：内容 / 状态 / 进度)."""
    entries = (
        db.query(WorkJournalEntry)
        .filter(
            WorkJournalEntry.owner_user_id == owner.id,
            WorkJournalEntry.work_date == work_date,
            WorkJournalEntry.deleted_at.is_(None),
        )
        .order_by(WorkJournalEntry.created_at, WorkJournalEntry.id)
        .all()
    )
    converting_v1 = report is not None and report.template_version in V1_TEMPLATE_VERSIONS
    previous_items = _existing_blocks(report, "items")
    items: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    next_plan: list[dict[str, Any]] = []
    source_refs: list[dict[str, Any]] = []
    warnings: list[str] = []

    for entry in entries:
        source_refs.append({
            "kind": "entry",
            "entry_id": entry.id,
            "revision": entry.revision,
            "work_date": entry.work_date.isoformat(),
            "title": entry.title,
            "fields": ["title", "body_markdown", "blocker_markdown", "next_step_markdown", "remarks_markdown"],
        })

    if converting_v1:
        # 一期日报转二期：name 与 progress 合成 content，保留 item_id 与来源；
        # 结果 / 测试与质量 / 成长与复盘另存为历史补充内容，不静默丢弃。
        items = _v1_items_to_v2(report)
        blockers = [dict(row) for row in ((report.sections or {}).get("blockers") or []) if isinstance(row, dict)]
        next_plan = [dict(row) for row in ((report.sections or {}).get("next_plan") or []) if isinstance(row, dict)]
        warnings.append("已按一期内容生成二期候选；原「结果 / 测试与质量 / 成长与复盘」收进历史补充内容")
    else:
        for entry in entries:
            item_refs = [{"report_id": None, "item_id": None, "entry_id": entry.id,
                          "work_date": entry.work_date.isoformat(), "title": entry.title}]
            item = {
                "item_id": _reuse_by_entry(previous_items, entry.id) or _new_id(),
                "content": _entry_content(entry),
                "status": entry.progress_status,
                # 日志没有百分比：已完成直接映射 100%，其余从 0 开始由本人调整。
                "progress_percent": 100 if entry.progress_status == "completed" else 0,
                "source_refs": item_refs,
                "manually_edited": False,
            }
            items.append(item)
            if normalize(entry.blocker_markdown) or entry.progress_status == "blocked":
                blocker_text = normalize(entry.blocker_markdown) or f"{entry.title} 处于受阻状态"
                blockers.append({"id": _new_id(), "item_id": item["item_id"], "text": blocker_text, "resolved": False,
                                 "source_refs": [{"entry_id": entry.id, "work_date": entry.work_date.isoformat()}]})
            if normalize(entry.next_step_markdown):
                next_plan.append({"id": _new_id(), "item_id": item["item_id"], "text": normalize(entry.next_step_markdown),
                                  "source_refs": [{"entry_id": entry.id, "work_date": entry.work_date.isoformat()}]})

    if not entries and not converting_v1:
        warnings.append("当天没有已保存的日志，可手动撰写日报")

    # 旧版纯文本日报：按标题给一条可编辑候选，不靠正则武断拆分原文。
    if report is not None and is_legacy(report) and not items:
        items.append({
            "item_id": _new_id(),
            "content": report.title,
            "status": "in_progress",
            "progress_percent": None,
            "source_refs": [],
            "manually_edited": False,
        })
        warnings.append("旧版日报缺少结构化事项，已按标题生成一条候选，请补充内容与进度")

    sections: dict[str, Any] = {"items": items, "blockers": blockers, "next_plan": next_plan, "remarks": ""}
    if converting_v1:
        sections["legacy_supplement"] = _v1_supplement(report)

    return {
        "report_type": "daily",
        "period_start": work_date,
        "period_end": work_date,
        "template_version": DAILY_TEMPLATE_VERSION,
        "sections": sections,
        "source_refs": source_refs,
        "source_count": len(entries),
        "missing_dates": [],
        "warnings": warnings,
        "totals": _daily_totals(entries),
        "already_referenced": _referenced_entry_ids(report),
        "generated_at": now_utc(),
    }


def _entry_content(entry: WorkJournalEntry) -> str:
    """日志转事项内容：标题作为首行摘要，正文完整保留在下方。"""
    title = normalize(entry.title)
    body = str(entry.body_markdown or "").strip()
    if not body or body == title:
        return title
    return f"{title}\n{body}"


def _v1_items_to_v2(report: WorkJournalReport) -> list[dict[str, Any]]:
    """一期事项转二期：name 与 progress 按原有顺序合成 content，保留 item_id 与来源。"""
    rows: list[dict[str, Any]] = []
    for item in (report.sections or {}).get("items", []):
        if not isinstance(item, dict):
            continue
        name = normalize(item.get("name"))
        progress = normalize(item.get("progress"))
        content = f"{name}：{progress}" if name and progress else (name or progress)
        if not content:
            continue
        status = item.get("status") if item.get("status") in PROGRESS_STATUSES else "in_progress"
        rows.append({
            "item_id": item.get("item_id") or _new_id(),
            "content": content,
            "status": status,
            # 旧进行中/受阻事项的百分比本来就未知，草稿允许留空；明确已完成映射 100%。
            "progress_percent": 100 if status == "completed" else None,
            "source_refs": item.get("source_refs") or [],
            "manually_edited": False,
        })
    return rows


def _v1_supplement(report: WorkJournalReport) -> dict[str, Any]:
    """把一期日报里被二期移除的填写区原样留档，供「历史补充内容」折叠查看。"""
    sections = report.sections or {}
    results = [
        {"item_id": item.get("item_id"), "name": normalize(item.get("name")), "result": normalize(item.get("result"))}
        for item in sections.get("items", [])
        if isinstance(item, dict) and normalize(item.get("result"))
    ]
    return {
        "quality": str(sections.get("quality") or ""),
        "reflection": str(sections.get("reflection") or ""),
        "results": results,
    }


def _daily_totals(entries: list[WorkJournalEntry]) -> dict[str, Any]:
    """Sum work minutes only from logs that actually recorded a duration."""
    recorded = [entry.duration_minutes for entry in entries if entry.duration_minutes is not None]
    return {
        "entry_count": len(entries),
        "completed": sum(1 for entry in entries if entry.progress_status == "completed"),
        "in_progress": sum(1 for entry in entries if entry.progress_status == "in_progress"),
        "blocked": sum(1 for entry in entries if entry.progress_status == "blocked"),
        "duration_minutes": sum(recorded) if recorded else None,
        "duration_log_count": len(recorded),
    }


def _referenced_entry_ids(report: WorkJournalReport | None) -> list[int]:
    """Collect entry ids already referenced by the report being updated."""
    if report is None:
        return []
    ids: list[int] = []
    for ref in report.source_refs or []:
        if isinstance(ref, dict) and ref.get("entry_id"):
            ids.append(int(ref["entry_id"]))
    return ids


# --------------------------------------------------------------------------------------
# 周报
# --------------------------------------------------------------------------------------
def _build_weekly(db: Session, owner: AppUser, period_start: date, period_end: date,
                  include_draft_reports: bool, report: WorkJournalReport | None) -> dict[str, Any]:
    """Assemble a weekly candidate strictly from the week's own daily reports."""
    reports = (
        db.query(WorkJournalReport)
        .filter(
            WorkJournalReport.owner_user_id == owner.id,
            WorkJournalReport.report_type == "daily",
            WorkJournalReport.deleted_at.is_(None),
            WorkJournalReport.period_start >= period_start,
            WorkJournalReport.period_start <= period_end,
        )
        .order_by(WorkJournalReport.period_start, WorkJournalReport.id)
        .all()
    )
    completed = [item for item in reports if item.status == "completed"]
    drafts = [item for item in reports if item.status != "completed"]
    selected = completed + (drafts if include_draft_reports else [])

    warnings: list[str] = []
    all_dates = date_range(period_start, period_end)
    covered = {item.period_start for item in selected}
    missing_dates = [day.isoformat() for day in all_dates if day not in covered]
    if not selected:
        warnings.append("本周还没有日报，请先记录日报")
    elif missing_dates:
        warnings.append("本周部分日期没有纳入的日报，生成内容仅依据已有日报")
    if include_draft_reports and drafts:
        warnings.append("已包含草稿日报，请注意区分")
    # 未纳入的草稿要明确提示，不能悄悄当成已完成来源。
    excluded_drafts = [item for item in drafts if item not in selected]
    if excluded_drafts:
        warnings.append(f"有 {len(excluded_drafts)} 份草稿日报未纳入，可在来源面板勾选")

    groups: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []
    blocker_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    completed_contents: set[str] = set()
    source_refs: list[dict[str, Any]] = []

    for report_item in reports:
        for row in (report_item.sections or {}).get("items", []):
            normalized = _source_item(row)
            if normalized is not None and normalized["status"] == "completed":
                completed_contents.add(normalize(normalized["content"]))

    for report_item in selected:
        sections = report_item.sections or {}
        source_refs.append({
            "kind": "report",
            "report_id": report_item.id,
            "revision": report_item.revision,
            "work_date": report_item.period_start.isoformat(),
            "title": report_item.title,
            "status": report_item.status,
        })
        for row in sections.get("items", []):
            normalized = _source_item(row)
            if normalized is None:
                continue
            key = _group_key(normalized["content"], normalized["project"])
            if key not in groups:
                groups[key] = {"observations": [], "refs": []}
                order.append(key)
            bucket = groups[key]
            bucket["observations"].append((report_item.period_start, normalized))
            bucket["refs"].append({
                "report_id": report_item.id,
                "item_id": row.get("item_id"),
                "work_date": report_item.period_start.isoformat(),
                "title": report_item.title,
                "name": normalize(normalized["content"]),
            })

        for row in sections.get("blockers", []):
            text = normalize(row.get("text"))
            if not text:
                continue
            blocker_rows.append({
                "text": text,
                "resolved": bool(row.get("resolved")),
                "item_id": row.get("item_id"),
                "work_date": report_item.period_start.isoformat(),
                "report_id": report_item.id,
            })
        for row in sections.get("next_plan", []):
            text = normalize(row.get("text"))
            if not text:
                continue
            plan_rows.append({
                "text": text,
                "item_id": row.get("item_id"),
                "work_date": report_item.period_start.isoformat(),
                "report_id": report_item.id,
            })

    previous_p = _existing_blocks(report, "p_items")
    previous_r = _existing_blocks(report, "r_items")
    previous_o = _existing_blocks(report, "o_items")

    p_items: list[dict[str, Any]] = []
    for key in order:
        bucket = groups[key]
        _project, group_content = key
        latest, conflict = _latest_observation(bucket["observations"])
        p_items.append({
            "item_id": _reuse_id(previous_p, bucket["refs"]) or _new_id(),
            "content": latest["content"] if latest else group_content,
            # 取时间最晚的明确状态与进度，不取最大值或平均值。
            "status": latest["status"] if latest else "in_progress",
            "progress_percent": latest["progress_percent"] if latest else None,
            "status_conflict": conflict,
            "source_item_refs": bucket["refs"],
            "manually_edited": False,
        })

    # 已明确解决的风险移出 R；仅凭措辞无法判断的保留并提示待核对。
    r_items: list[dict[str, Any]] = []
    seen_risk: set[str] = set()
    for row in blocker_rows:
        if row["text"] in seen_risk:
            continue
        seen_risk.add(row["text"])
        if row["resolved"]:
            continue
        r_items.append({
            "id": _reuse_by_text(previous_r, row["text"]) or _new_id(),
            "text": row["text"],
            "source_refs": [{"report_id": row["report_id"], "work_date": row["work_date"]}],
            "manually_edited": False,
        })
    if not r_items:
        r_items.append({
            "id": _reuse_by_text(previous_r, NO_RISK_TEXT) or _new_id(),
            "text": NO_RISK_TEXT,
            "source_refs": [],
            "manually_edited": False,
        })

    # 已在后续日报完成的事项不再重复列为下周计划。
    o_items: list[dict[str, Any]] = []
    seen_plan: set[str] = set()
    for row in plan_rows:
        text = row["text"]
        if text in seen_plan:
            continue
        seen_plan.add(text)
        if any(done and done in text for done in completed_contents if done):
            continue
        o_items.append({
            "id": _reuse_by_text(previous_o, text) or _new_id(),
            "text": text,
            "source_refs": [{"report_id": row["report_id"], "work_date": row["work_date"]}],
            "manually_edited": False,
        })
    if not o_items:
        o_items.append({
            "id": _reuse_by_text(previous_o, NO_PLAN_TEXT) or _new_id(),
            "text": NO_PLAN_TEXT,
            "source_refs": [],
            "manually_edited": False,
        })

    totals = _weekly_totals(db, owner, selected, source_refs)
    sections: dict[str, Any] = {"p_items": p_items, "r_items": r_items, "o_items": o_items, "remarks": ""}
    if report is not None and report.template_version in V1_TEMPLATE_VERSIONS:
        # 一期周报转二期：人工写好的结果不映射成百分比模板，原样收进历史补充内容。
        sections["legacy_supplement"] = _v1_weekly_supplement(report)
        warnings.append("已按本周日报生成二期候选；一期周报原文收进历史补充内容，请确认后再保存")
    return {
        "report_type": "weekly",
        "period_start": period_start,
        "period_end": period_end,
        "template_version": WEEKLY_TEMPLATE_VERSION,
        "sections": sections,
        "source_refs": source_refs,
        "source_count": len(selected),
        "missing_dates": missing_dates,
        "warnings": warnings,
        "totals": totals,
        "already_referenced": _referenced_report_ids(report),
        "as_of": min(today_shanghai(), period_end).isoformat(),
        "generated_at": now_utc(),
    }


def _source_item(row: Any) -> dict[str, Any] | None:
    """把一期或二期的日报事项统一成二期形状，便于跨天归并。

    二期事项直接读 content / status / progress_percent；一期事项把 name 与 progress 合成
    content，旧的 result 只作为历史补充，不参与新模板的成果推导。
    """
    if not isinstance(row, dict):
        return None
    content = normalize(row.get("content"))
    if not content:
        name = normalize(row.get("name"))
        progress = normalize(row.get("progress"))
        content = f"{name}：{progress}" if name and progress else (name or progress)
    if not content:
        return None
    status = row.get("status") if row.get("status") in PROGRESS_STATUSES else "in_progress"
    percent = row.get("progress_percent")
    if isinstance(percent, bool) or not isinstance(percent, int) or percent not in PROGRESS_OPTIONS:
        # 老记录没有百分比：明确已完成映射 100%，进行中/受阻保持未知。
        percent = 100 if status == "completed" else None
    return {
        "content": content,
        "status": status,
        "progress_percent": percent,
        "project": normalize(row.get("project")),
    }


def _latest_observation(rows: list[tuple[date, dict[str, Any]]]) -> tuple[dict[str, Any] | None, bool]:
    """取时间最晚的明确状态与进度，不取最大值或平均值。

    同一天出现互相冲突的状态/进度时标记待核对，不用日报的编辑时间冒充事项发生时间。
    """
    if not rows:
        return None, False
    ordered = sorted(rows, key=lambda item: item[0])
    latest_day = ordered[-1][0]
    same_day = [row for day, row in ordered if day == latest_day]
    signals = {(row["status"], row["progress_percent"]) for row in same_day}
    return same_day[-1], len(signals) > 1


def _v1_weekly_supplement(report: WorkJournalReport) -> dict[str, Any]:
    """一期周报原文留档，供转换后对比查看，不参与新模板生成。"""
    sections = report.sections or {}
    return {
        "p_items": [
            {
                "item_id": item.get("item_id"),
                "name": normalize(item.get("name")),
                "progress": normalize(item.get("progress")),
                "result": normalize(item.get("result")),
            }
            for item in sections.get("p_items", [])
            if isinstance(item, dict)
        ],
    }


def _reuse_by_text(previous: list[dict[str, Any]], text: str) -> str | None:
    """Reuse the id of a previously generated block with the same text."""
    for block in previous:
        if normalize(block.get("text")) == normalize(text):
            return block.get("id")
    return None


def _referenced_report_ids(report: WorkJournalReport | None) -> list[int]:
    """Collect daily report ids already referenced by the weekly report being updated."""
    if report is None:
        return []
    ids: list[int] = []
    for ref in report.source_refs or []:
        if isinstance(ref, dict) and ref.get("report_id"):
            ids.append(int(ref["report_id"]))
    return ids


def _weekly_totals(db: Session, owner: AppUser, selected: list[WorkJournalReport], source_refs: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum durations from de-duplicated logs actually referenced by the selected daily reports."""
    entry_ids: list[int] = []
    for report_item in selected:
        for ref in (report_item.sections or {}).get("items", []):
            for item_ref in ref.get("source_refs") or []:
                entry_id = item_ref.get("entry_id")
                if entry_id and entry_id not in entry_ids:
                    entry_ids.append(int(entry_id))
    total = None
    if entry_ids:
        rows = (
            db.query(WorkJournalEntry.duration_minutes)
            .filter(WorkJournalEntry.owner_user_id == owner.id, WorkJournalEntry.id.in_(entry_ids))
            .all()
        )
        recorded = [row[0] for row in rows if row[0] is not None]
        total = sum(recorded) if recorded else None
    return {"daily_report_count": len(selected), "entry_count": len(entry_ids), "duration_minutes": total}


# --------------------------------------------------------------------------------------
# 入口与合并
# --------------------------------------------------------------------------------------
def build_preview(db: Session, owner: AppUser, *, report_type: str, period_start: date, period_end: date,
                  include_draft_reports: bool, report_id: int | None) -> dict[str, Any]:
    """Build a candidate body without writing anything to the database."""
    report = None
    if report_id is not None:
        report = (
            db.query(WorkJournalReport)
            .filter(WorkJournalReport.id == report_id, WorkJournalReport.owner_user_id == owner.id)
            .first()
        )
    if report_type == "daily":
        preview = _build_daily(db, owner, period_start, report)
    else:
        preview = _build_weekly(db, owner, period_start, period_end, include_draft_reports, report)
    if report is not None and is_legacy(report):
        # 旧版报告转换时必须保留原文，不能静默覆盖历史内容。
        preview["sections"]["legacy_body"] = legacy_body(report)
        preview["warnings"] = list(preview.get("warnings") or []) + [
            "这是旧版报告：转换后原始正文会保留在 legacy_body，历史内容不会被覆盖"
        ]
    return preview


def merge_sections(report_type: str, current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Append assembled content to the existing body without duplicating the same source."""
    # 合并两侧的附加字段（例如旧版报告的 legacy_body），避免追加时丢掉历史内容。
    result = {**incoming, **(current or {})}
    if report_type == "daily":
        existing_items = list(result.get("items") or [])
        seen = {_entry_id_of(item) for item in existing_items}
        for item in incoming.get("items") or []:
            key = _entry_id_of(item)
            if key is not None and key in seen:
                continue
            existing_items.append(item)
            seen.add(key)
        result["items"] = existing_items
        result["blockers"] = _append_unique(result.get("blockers") or [], incoming.get("blockers") or [], "text")
        result["next_plan"] = _append_unique(result.get("next_plan") or [], incoming.get("next_plan") or [], "text")
        for key in ("quality", "reflection"):
            merged = dedupe_sentences(split_sentences(result.get(key)) + split_sentences(incoming.get(key)))
            result[key] = "\n".join(merged)
        return result

    for key in ("p_items", "r_items", "o_items"):
        existing = list(result.get(key) or [])
        if key == "p_items":
            seen_keys = {_group_key(item.get("name"), item.get("project") or "") for item in existing}
            for item in incoming.get(key) or []:
                if _group_key(item.get("name"), item.get("project") or "") in seen_keys:
                    continue
                existing.append(item)
        else:
            existing = _append_unique(existing, incoming.get(key) or [], "text")
        result[key] = existing
    return result


def _entry_id_of(item: dict[str, Any]) -> int | None:
    """Read the source entry id of an assembled daily item."""
    for ref in item.get("source_refs") or []:
        if ref.get("entry_id"):
            return int(ref["entry_id"])
    return None


def _append_unique(existing: list[dict[str, Any]], incoming: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Append rows whose key text is not present yet."""
    seen = {normalize(row.get(key)) for row in existing}
    merged = list(existing)
    for row in incoming:
        text = normalize(row.get(key))
        if not text or text in seen:
            continue
        seen.add(text)
        merged.append(row)
    return merged


def _ref_keys(block: dict[str, Any]) -> frozenset:
    """Read the stable source identity of one generated block."""
    refs = block.get("source_item_refs") or []
    return frozenset((str(ref.get("report_id")), str(ref.get("item_id"))) for ref in refs if ref.get("report_id") or ref.get("item_id"))


def _entry_key(block: dict[str, Any]) -> str | None:
    """Read the source log id of one generated daily item."""
    for ref in block.get("source_refs") or []:
        if ref.get("entry_id"):
            return str(ref["entry_id"])
    return None


def merge_regenerated(report_type: str, current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """重新生成时以来源 ID 更新未人工修改的块，人工修改块原样保留，且不新增重复事项。"""
    result = dict(incoming)
    if report_type == "daily":
        manual: dict[str, dict[str, Any]] = {}
        for row in current.get("items") or []:
            key = _entry_key(row)
            if row.get("manually_edited") and key:
                manual[key] = row
        merged_items: list[dict[str, Any]] = []
        used: set[str] = set()
        for row in incoming.get("items") or []:
            key = _entry_key(row)
            if key and key in manual:
                merged_items.append(manual[key])
                used.add(key)
            else:
                merged_items.append(row)
        # 来源已消失但被人工修改过的条目继续保留，不因重新生成而丢失。
        merged_items.extend(row for key, row in manual.items() if key not in used)
        result["items"] = merged_items
        return result

    manual_p = [(index, row) for index, row in enumerate(current.get("p_items") or []) if row.get("manually_edited")]
    merged_p: list[dict[str, Any]] = []
    consumed: set[int] = set()
    for row in incoming.get("p_items") or []:
        key = _ref_keys(row)
        matched = False
        if key:
            for index, manual_row in manual_p:
                if index not in consumed and _ref_keys(manual_row) == key:
                    merged_p.append(manual_row)
                    consumed.add(index)
                    matched = True
                    break
        if not matched:
            merged_p.append(row)
    merged_p.extend(row for index, row in manual_p if index not in consumed)
    result["p_items"] = merged_p

    for key in ("r_items", "o_items"):
        incoming_texts = {normalize(row.get("text")) for row in incoming.get(key) or []}
        merged = list(incoming.get(key) or [])
        # 人工改写过、且本次生成没有再产出的条目保留下来。
        merged.extend(
            row
            for row in current.get(key) or []
            if row.get("manually_edited") and normalize(row.get("text")) not in incoming_texts
        )
        result[key] = merged
    return result
