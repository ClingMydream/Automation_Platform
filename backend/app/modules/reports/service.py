"""Report service helpers for turning runs and execution batches into report summaries."""

from sqlalchemy.orm import Session

from app.models.entities import ApiCase, ExecutionBatch, TestResult, TestRun, TestTask, UiCase
from app.modules.result_center.performance import performance_summary_from_results


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
        "report_key": f"run-{run.id}",
        "report_kind": "run",
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


def task_name_for_batch(db: Session, batch: ExecutionBatch) -> str:
    """Resolve the task name displayed by a batch report."""
    if batch.task_id is None:
        return "独立结果批次"
    task = db.get(TestTask, batch.task_id)
    return task.name if task else f"已删除任务 #{batch.task_id}"


def batch_results(db: Session, batch_id: int) -> list[TestResult]:
    """Load result rows that belong to one execution batch."""
    return db.query(TestResult).filter(TestResult.batch_id == batch_id).order_by(TestResult.id.asc()).all()


def batch_report_summary(db: Session, batch: ExecutionBatch) -> dict:
    """Convert an execution batch into a report-list summary object."""
    results = batch_results(db, batch.id)
    assertion_count = sum(len(result.assertions or []) for result in results)
    failed_results = [result for result in results if result.status in {"failed", "error"}]
    result_types = sorted({result.result_type for result in results if result.result_type})
    performance_summary = performance_summary_from_results(results)
    report = {
        "batch": {
            "id": batch.id,
            "batch_no": batch.batch_no,
            "task_id": batch.task_id,
            "trigger_type": batch.trigger_type,
            "environment_id": batch.environment_id,
            "summary": batch.summary or {},
        },
        "stats": {
            "total": batch.total_count,
            "passed": batch.passed_count,
            "failed": batch.failed_count,
            "skipped": batch.skipped_count,
        },
        "results": [
            {
                "id": result.id,
                "case_type": result.case_type,
                "case_id": result.case_id,
                "result_type": result.result_type,
                "status": result.status,
                "duration_ms": result.duration_ms,
                "request_data": result.request_data,
                "response_data": result.response_data,
                "assertions": result.assertions,
                "metrics": result.metrics,
                "error": result.error,
                "failure_category": result.failure_category,
            }
            for result in results
        ],
        "performance_summary": performance_summary,
    }
    return {
        "report_key": f"batch-{batch.id}",
        "report_kind": "batch",
        "id": batch.id,
        "case_type": "batch",
        "case_id": batch.task_id,
        "case_name": task_name_for_batch(db, batch),
        "status": batch.status,
        "passed": batch.status == "passed",
        "duration_ms": batch.duration_ms,
        "logs": f"批次 {batch.batch_no} 共 {batch.total_count} 条结果",
        "error": failed_results[0].error if failed_results else None,
        "created_at": batch.created_at,
        "updated_at": batch.updated_at,
        "check_count": assertion_count,
        "event_count": len(results),
        "screenshot_count": 0,
        "summary": {
            "batch_no": batch.batch_no,
            "total": batch.total_count,
            "passed": batch.passed_count,
            "failed": batch.failed_count,
            "skipped": batch.skipped_count,
            "result_types": result_types,
            "performance": {
                "total": performance_summary["total"],
                "avg_response_ms": performance_summary["avg_response_ms"],
                "max_p95_ms": performance_summary["max_p95_ms"],
                "max_error_rate": performance_summary["max_error_rate"],
                "max_tps": performance_summary["max_tps"],
                "risk_level": performance_summary["risk_level"],
            },
        },
        "report": report,
    }
