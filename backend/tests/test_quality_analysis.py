"""Tests for quality analysis metrics and release risk evaluation."""

from app.models.entities import TestResult as ResultModel
from app.modules.quality_analysis.service import quality_summary_from_results, release_risk_from_metrics


def test_quality_summary_calculates_release_metrics():
    """Quality summary should expose pass rate, latency percentiles, and failure distributions."""
    rows = [
        ResultModel(result_type="api", status="passed", duration_ms=100, environment_id=1),
        ResultModel(result_type="api", status="failed", duration_ms=4000, failure_category="assertion", case_type="api", case_id=3, environment_id=1),
        ResultModel(result_type="ui", status="error", duration_ms=2000, failure_category="timeout", case_type="ui", case_id=9, environment_id=2),
        ResultModel(result_type="api", status="skipped", duration_ms=500, environment_id=1),
    ]

    summary = quality_summary_from_results(rows)

    assert summary["total"] == 4
    assert summary["passed"] == 1
    assert summary["failed"] == 2
    assert summary["skipped"] == 1
    assert summary["pass_rate"] == 25
    assert summary["fail_rate"] == 50
    assert summary["release_risk"] == "high"
    assert summary["p95_duration_ms"] == 4000
    assert summary["failure_categories"] == {"assertion": 1, "timeout": 1}
    assert summary["top_failed_cases"] == [{"name": "api#3", "count": 1}, {"name": "ui#9", "count": 1}]


def test_release_risk_low_when_results_are_clean():
    """Clean results should be marked as low risk with a positive reason."""
    risk, reasons = release_risk_from_metrics(total=10, failed=0, skipped=0, pass_rate=100, p95=300)

    assert risk == "low"
    assert reasons == ["最近结果未发现明显阻塞风险"]
