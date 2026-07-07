"""Tests for performance result normalization and summaries."""

from datetime import UTC, datetime

from app.models.entities import TestResult as ResultModel
from app.modules.result_center.performance import normalize_performance_metrics, performance_summary_from_results


def test_normalize_performance_metrics_accepts_jmeter_like_aliases():
    """JMeter-style metric names should map into stable platform fields."""
    metrics = {
        "average": "ignored",
        "avg": "180.6",
        "p95": "520",
        "p99": 900,
        "throughput": "33.3",
        "error_rate": 0.015,
        "sample_count": "1200",
        "threads": "50",
    }

    normalized = normalize_performance_metrics(metrics)

    assert normalized["avg_ms"] == 180.6
    assert normalized["p95_ms"] == 520
    assert normalized["p99_ms"] == 900
    assert normalized["tps"] == 33.3
    assert normalized["error_rate"] == 1.5
    assert normalized["samples"] == 1200
    assert normalized["concurrency"] == 50


def test_performance_summary_calculates_dashboard_metrics():
    """Performance summary should expose pass rate, latency, TPS, samples, and risk."""
    now = datetime.now(UTC)
    rows = [
        ResultModel(id=1, result_type="api", status="passed", duration_ms=100, created_at=now),
        ResultModel(
            id=2,
            result_type="performance",
            status="passed",
            duration_ms=200,
            metrics={"avg_ms": 180, "p95_ms": 900, "p99_ms": 1200, "tps": 20, "error_rate": 0.005, "samples": 500},
            created_at=now,
        ),
        ResultModel(
            id=3,
            result_type="performance",
            status="failed",
            duration_ms=500,
            metrics={"avg_response_time": 300, "p95": 3600, "requests_per_second": 12, "error_rate_percent": 6, "count": 200},
            created_at=now,
            error="p95 threshold exceeded",
        ),
    ]

    summary = performance_summary_from_results(rows)

    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["pass_rate"] == 50
    assert summary["avg_response_ms"] == 240
    assert summary["max_p95_ms"] == 3600
    assert summary["max_error_rate"] == 6
    assert summary["max_tps"] == 20
    assert summary["total_samples"] == 700
    assert summary["risk_level"] == "high"
    assert summary["latest_results"][0]["id"] == 3
