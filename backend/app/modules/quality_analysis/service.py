"""Business helpers for quality analysis metrics and release risk evaluation."""

from collections import Counter
from math import ceil
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.entities import ExecutionBatch, TestResult


FAILED_STATUSES = {"failed", "error"}


def _percent(part: int | float, total: int | float) -> float:
    """Return a rounded percentage while avoiding division by zero."""
    return round(part / total * 100, 2) if total else 0


def _duration_percentile(durations: list[int], percentile: float) -> int | None:
    """Return the nearest-rank percentile value for duration samples."""
    if not durations:
        return None
    ordered = sorted(durations)
    index = max(ceil(len(ordered) * percentile / 100) - 1, 0)
    return ordered[min(index, len(ordered) - 1)]


def _counter_items(counter: Counter, limit: int = 8) -> list[dict]:
    """Convert a counter into a stable list shape for frontend tables."""
    return [{"name": key, "count": value} for key, value in counter.most_common(limit)]


def _result_case_key(result: TestResult) -> str:
    """Build a readable key for grouping frequent failures by case or object."""
    if result.case_type and result.case_id:
        return f"{result.case_type}#{result.case_id}"
    if result.test_object_id:
        return f"object#{result.test_object_id}"
    return result.result_type or "unknown"


def release_risk_from_metrics(total: int, failed: int, skipped: int, pass_rate: float, p95: int | None) -> tuple[str, list[str]]:
    """Evaluate release risk using pass rate, failed count, skipped count, and latency."""
    reasons: list[str] = []
    if failed:
        reasons.append(f"存在 {failed} 条失败或错误结果")
    if pass_rate < 80 and total:
        reasons.append("通过率低于 80%")
    if skipped:
        reasons.append(f"存在 {skipped} 条跳过结果")
    if p95 is not None and p95 > 3000:
        reasons.append("P95 耗时超过 3000ms")
    if failed or (pass_rate < 80 and total):
        return "high", reasons
    if skipped or (p95 is not None and p95 > 1500):
        return "medium", reasons or ["存在需要关注的稳定性或性能信号"]
    return "low", reasons or ["最近结果未发现明显阻塞风险"]


def quality_summary_from_results(results: Iterable[TestResult]) -> dict:
    """Calculate release-readiness metrics from recent test result rows."""
    rows = list(results)
    total = len(rows)
    passed = len([row for row in rows if row.status == "passed"])
    failed = len([row for row in rows if row.status in FAILED_STATUSES])
    skipped = len([row for row in rows if row.status == "skipped"])
    durations = [row.duration_ms for row in rows if row.duration_ms is not None]
    pass_rate = _percent(passed, total)
    fail_rate = _percent(failed, total)
    error_rate = _percent(len([row for row in rows if row.status == "error"]), total)
    avg_duration = round(sum(durations) / len(durations), 2) if durations else None
    p95 = _duration_percentile(durations, 95)
    p99 = _duration_percentile(durations, 99)
    release_risk, risk_reasons = release_risk_from_metrics(total, failed, skipped, pass_rate, p95)
    failure_rows = [row for row in rows if row.status in FAILED_STATUSES]
    stability_score = max(0, round(100 - fail_rate - error_rate - _percent(skipped, total) * 0.5, 2))
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": pass_rate,
        "fail_rate": fail_rate,
        "error_rate": error_rate,
        "stability_score": stability_score,
        "avg_duration_ms": avg_duration,
        "p95_duration_ms": p95,
        "p99_duration_ms": p99,
        "release_risk": release_risk,
        "release_risk_reasons": risk_reasons,
        "failure_categories": dict(Counter(row.failure_category or "未分类" for row in failure_rows)),
        "failure_category_items": _counter_items(Counter(row.failure_category or "未分类" for row in failure_rows)),
        "result_types": dict(Counter(row.result_type for row in rows)),
        "result_type_items": _counter_items(Counter(row.result_type for row in rows)),
        "status_items": _counter_items(Counter(row.status for row in rows)),
        "environment_items": _counter_items(Counter(str(row.environment_id or "未绑定环境") for row in rows)),
        "top_failed_cases": _counter_items(Counter(_result_case_key(row) for row in failure_rows), limit=10),
    }


def build_quality_summary(db: Session) -> dict:
    """Load recent result rows and return the quality dashboard summary."""
    results = db.query(TestResult).order_by(TestResult.id.desc()).limit(1000).all()
    return quality_summary_from_results(results)


def build_quality_trend(db: Session) -> list[dict]:
    """Return recent execution batches as trend rows with risk markers."""
    batches = db.query(ExecutionBatch).order_by(ExecutionBatch.id.desc()).limit(30).all()
    trend: list[dict] = []
    for batch in batches:
        pass_rate = _percent(batch.passed_count, batch.total_count)
        fail_rate = _percent(batch.failed_count, batch.total_count)
        risk, reasons = release_risk_from_metrics(batch.total_count, batch.failed_count, batch.skipped_count, pass_rate, batch.duration_ms)
        trend.append({
            "batch_no": batch.batch_no,
            "status": batch.status,
            "total": batch.total_count,
            "passed": batch.passed_count,
            "failed": batch.failed_count,
            "skipped": batch.skipped_count,
            "pass_rate": pass_rate,
            "fail_rate": fail_rate,
            "release_risk": risk,
            "release_risk_reasons": reasons,
            "duration_ms": batch.duration_ms,
            "created_at": batch.created_at,
        })
    return trend


def build_task_quality_report(db: Session, task_id: int) -> dict:
    """Return task-level quality metrics, recent batches, and failure distribution."""
    batches = db.query(ExecutionBatch).filter(ExecutionBatch.task_id == task_id).order_by(ExecutionBatch.id.desc()).limit(20).all()
    results = db.query(TestResult).filter(TestResult.task_id == task_id).order_by(TestResult.id.desc()).limit(200).all()
    return {
        "task_id": task_id,
        "summary": quality_summary_from_results(results),
        "batches": batches,
        "results": results,
        "total_results": len(results),
        "failed_results": len([row for row in results if row.status in FAILED_STATUSES]),
    }
