"""Report service helpers for turning execution runs into report summaries."""

from sqlalchemy.orm import Session

from app.models.entities import ApiCase, TestRun, UiCase


def case_name_for_run(db: Session, run: TestRun) -> str:
    """Resolve the display case name for a run."""
    model = ApiCase if run.case_type == "api" else UiCase
    case = db.get(model, run.case_id)
    return case.name if case else f"已删除用例 #{run.case_id}"


def report_summary(run: TestRun, case_name: str) -> dict:
    """Convert a run into a report-list summary object."""
    report = run.report or {}
    # These counts let the frontend build a useful report list without parsing every report deeply.
    checks = report.get("checks") or []
    events = report.get("events") or []
    screenshots = report.get("screenshots") or []
    return {
        "id": run.id,
        "case_type": run.case_type,
        "case_id": run.case_id,
        "case_name": case_name,
        "status": run.status,
        "passed": report.get("passed") if report else run.status == "passed",
        "duration_ms": run.duration_ms,
        "logs": run.logs,
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "check_count": len(checks),
        "event_count": len(events),
        "screenshot_count": len(screenshots),
        "summary": {
            "request": report.get("request"),
            "response_status": (report.get("response") or {}).get("status_code"),
            "current_step": report.get("current_step"),
            "total_steps": report.get("total_steps"),
        },
        "report": report,
    }
