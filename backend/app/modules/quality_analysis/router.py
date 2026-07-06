"""Quality analysis routes for release-readiness and stability metrics."""

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import ExecutionBatch, TestResult


router = APIRouter(tags=["质量分析"])


@router.get("/v1/quality/summary", summary="查询质量总览")
def quality_summary(_: AuthContext = Depends(require_menu("quality")), db: Session = Depends(get_db)):
    """Return pass rate, failure distribution, and basic performance indicators."""
    results = db.query(TestResult).order_by(TestResult.id.desc()).limit(1000).all()
    total = len(results)
    passed = len([row for row in results if row.status == "passed"])
    failed = len([row for row in results if row.status in {"failed", "error"}])
    skipped = len([row for row in results if row.status == "skipped"])
    durations = sorted([row.duration_ms for row in results if row.duration_ms is not None])
    failure_categories = Counter(row.failure_category or "未分类" for row in results if row.status in {"failed", "error"})
    result_types = Counter(row.result_type for row in results)
    p95 = durations[int(len(durations) * 0.95) - 1] if durations else None
    p99 = durations[int(len(durations) * 0.99) - 1] if durations else None
    avg = round(sum(durations) / len(durations), 2) if durations else None
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round(passed / total * 100, 2) if total else 0,
        "avg_duration_ms": avg,
        "p95_duration_ms": p95,
        "p99_duration_ms": p99,
        "failure_categories": dict(failure_categories),
        "result_types": dict(result_types),
        "release_risk": "high" if failed else ("medium" if skipped else "low"),
    }


@router.get("/v1/reports/quality-trend", summary="查询质量趋势")
def quality_trend(_: AuthContext = Depends(require_menu("quality")), db: Session = Depends(get_db)):
    """Return recent execution batches as a lightweight quality trend."""
    batches = db.query(ExecutionBatch).order_by(ExecutionBatch.id.desc()).limit(30).all()
    return [
        {
            "batch_no": batch.batch_no,
            "status": batch.status,
            "total": batch.total_count,
            "passed": batch.passed_count,
            "failed": batch.failed_count,
            "skipped": batch.skipped_count,
            "pass_rate": round(batch.passed_count / batch.total_count * 100, 2) if batch.total_count else 0,
            "created_at": batch.created_at,
        }
        for batch in batches
    ]


@router.get("/v1/reports/tasks/{task_id}", summary="查询任务质量报告")
def task_quality_report(task_id: int, _: AuthContext = Depends(require_menu("quality")), db: Session = Depends(get_db)):
    """Return recent batches and results for one task as a task-level report."""
    batches = db.query(ExecutionBatch).filter(ExecutionBatch.task_id == task_id).order_by(ExecutionBatch.id.desc()).limit(20).all()
    results = db.query(TestResult).filter(TestResult.task_id == task_id).order_by(TestResult.id.desc()).limit(200).all()
    return {
        "task_id": task_id,
        "batches": batches,
        "results": results,
        "total_results": len(results),
        "failed_results": len([row for row in results if row.status in {"failed", "error"}]),
    }
