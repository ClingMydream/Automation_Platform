"""Performance result normalization and summary helpers for the result center."""

from __future__ import annotations

from typing import Any, Iterable

from app.models.entities import TestResult


# Metric aliases let JMeter, PTS, Locust, or custom scripts use familiar field names.
METRIC_ALIASES = {
    "avg_ms": ["avg_ms", "average_ms", "avg", "mean_ms", "mean", "avg_response_time", "average_response_time"],
    "p50_ms": ["p50_ms", "median_ms", "p50", "median"],
    "p90_ms": ["p90_ms", "p90"],
    "p95_ms": ["p95_ms", "p95", "percentile_95", "pct95"],
    "p99_ms": ["p99_ms", "p99", "percentile_99", "pct99"],
    "tps": ["tps", "throughput", "rps", "requests_per_second"],
    "error_rate": ["error_rate", "error_rate_percent", "errors_percent", "failure_rate"],
    "samples": ["samples", "sample_count", "count", "total", "requests"],
    "concurrency": ["concurrency", "threads", "users", "virtual_users", "vus"],
}


def _to_float(value: Any) -> float | None:
    """Convert numeric-looking metric values into float values."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_number(metrics: dict[str, Any], aliases: list[str]) -> float | None:
    """Return the first numeric value found by alias order."""
    for key in aliases:
        value = _to_float(metrics.get(key))
        if value is not None:
            return value
    return None


def _round_metric(value: float | None, digits: int = 2) -> float | None:
    """Round metric values while preserving missing values as None."""
    if value is None:
        return None
    return round(value, digits)


def _normalize_percent(value: float | None) -> float | None:
    """Normalize ratio values like 0.012 into percent values like 1.2."""
    if value is None:
        return None
    if 0 < value < 1:
        value = value * 100
    return round(value, 2)


def normalize_performance_metrics(metrics: dict[str, Any] | None, duration_ms: int | None = None) -> dict[str, Any]:
    """Normalize common performance metrics into stable platform fields."""
    source = metrics or {}
    avg_ms = _first_number(source, METRIC_ALIASES["avg_ms"])
    return {
        "avg_ms": _round_metric(avg_ms if avg_ms is not None else _to_float(duration_ms)),
        "p50_ms": _round_metric(_first_number(source, METRIC_ALIASES["p50_ms"])),
        "p90_ms": _round_metric(_first_number(source, METRIC_ALIASES["p90_ms"])),
        "p95_ms": _round_metric(_first_number(source, METRIC_ALIASES["p95_ms"])),
        "p99_ms": _round_metric(_first_number(source, METRIC_ALIASES["p99_ms"])),
        "tps": _round_metric(_first_number(source, METRIC_ALIASES["tps"])),
        "error_rate": _normalize_percent(_first_number(source, METRIC_ALIASES["error_rate"])),
        "samples": _round_metric(_first_number(source, METRIC_ALIASES["samples"]), 0),
        "concurrency": _round_metric(_first_number(source, METRIC_ALIASES["concurrency"]), 0),
    }


def _average(values: list[float]) -> float | None:
    """Calculate an average for a list that has already removed missing values."""
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _max_value(values: list[float]) -> float | None:
    """Return the maximum value for dashboard risk and summary cards."""
    if not values:
        return None
    return round(max(values), 2)


def _compact_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Remove empty normalized metrics so API responses stay readable."""
    return {key: value for key, value in metrics.items() if value is not None}


def _risk_level(max_error_rate: float | None, max_p95_ms: float | None, failed: int) -> tuple[str, list[str]]:
    """Convert performance thresholds into a simple release-risk hint."""
    reasons: list[str] = []
    if failed:
        reasons.append(f"存在 {failed} 条失败或错误的性能结果")
    if max_error_rate is not None and max_error_rate >= 5:
        reasons.append(f"最高错误率达到 {max_error_rate}%")
    if max_p95_ms is not None and max_p95_ms >= 3000:
        reasons.append(f"最高 P95 响应时间达到 {max_p95_ms} ms")
    if reasons:
        return "high", reasons
    if max_error_rate is not None and max_error_rate >= 1:
        reasons.append(f"最高错误率达到 {max_error_rate}%")
    if max_p95_ms is not None and max_p95_ms >= 1500:
        reasons.append(f"最高 P95 响应时间达到 {max_p95_ms} ms")
    if reasons:
        return "medium", reasons
    return "low", ["最近性能结果未发现明显风险"]


def performance_summary_from_results(rows: Iterable[TestResult]) -> dict[str, Any]:
    """Build a dashboard summary from stored performance result rows."""
    performance_rows = [row for row in rows if row.result_type == "performance"]
    normalized_pairs = [(row, normalize_performance_metrics(row.metrics, row.duration_ms)) for row in performance_rows]
    total = len(normalized_pairs)
    passed = len([row for row, _metrics in normalized_pairs if row.status == "passed"])
    failed = len([row for row, _metrics in normalized_pairs if row.status in {"failed", "error"}])
    skipped = len([row for row, _metrics in normalized_pairs if row.status == "skipped"])
    avg_values = [metrics["avg_ms"] for _row, metrics in normalized_pairs if metrics.get("avg_ms") is not None]
    p95_values = [metrics["p95_ms"] for _row, metrics in normalized_pairs if metrics.get("p95_ms") is not None]
    p99_values = [metrics["p99_ms"] for _row, metrics in normalized_pairs if metrics.get("p99_ms") is not None]
    tps_values = [metrics["tps"] for _row, metrics in normalized_pairs if metrics.get("tps") is not None]
    error_values = [metrics["error_rate"] for _row, metrics in normalized_pairs if metrics.get("error_rate") is not None]
    sample_values = [metrics["samples"] for _row, metrics in normalized_pairs if metrics.get("samples") is not None]
    max_error_rate = _max_value(error_values)
    max_p95_ms = _max_value(p95_values)
    risk_level, risk_reasons = _risk_level(max_error_rate, max_p95_ms, failed)
    latest_rows = sorted(performance_rows, key=lambda item: item.id or 0, reverse=True)[:20]
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round((passed / total) * 100, 2) if total else 0,
        "avg_response_ms": _average(avg_values),
        "max_p95_ms": max_p95_ms,
        "max_p99_ms": _max_value(p99_values),
        "max_error_rate": max_error_rate,
        "max_tps": _max_value(tps_values),
        "total_samples": int(sum(sample_values)) if sample_values else 0,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "latest_results": [
            {
                "id": row.id,
                "batch_id": row.batch_id,
                "task_id": row.task_id,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "created_at": row.created_at,
                "metrics": row.metrics or {},
                "normalized_metrics": _compact_metrics(normalize_performance_metrics(row.metrics, row.duration_ms)),
                "error": row.error,
            }
            for row in latest_rows
        ],
    }
