"""Tests for lightweight performance runtime metrics."""

import os
import sys
import types
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "mysql+pymysql://automation:password@127.0.0.1:3306/automation_platform")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

requests_stub = types.ModuleType("requests")
requests_stub.RequestException = Exception
requests_stub.request = lambda *_args, **_kwargs: None
sys.modules.setdefault("requests", requests_stub)

from app.modules.performance_automation import runtime  # noqa: E402


class FakeResponse:
    """Minimal response object returned by the fake requests client."""

    status_code = 200


def test_execute_performance_case_builds_metrics(monkeypatch):
    """A performance scenario should produce normalized metrics and threshold checks."""
    monkeypatch.setattr(runtime.requests, "request", lambda *_args, **_kwargs: FakeResponse())

    report = runtime.execute_performance_case({
        "id": 9,
        "method": "GET",
        "target_url": "https://example.com/health",
        "headers": {},
        "concurrency": 2,
        "duration_seconds": 1,
        "threshold_p95_ms": 5000,
        "threshold_error_rate": 1,
    })

    assert report["passed"] is True
    assert report["request"]["scenario_id"] == 9
    assert report["metrics"]["samples"] >= 1
    assert report["metrics"]["error_rate"] == 0
    assert report["metrics"]["tps"] > 0
    assert {item["name"] for item in report["checks"]} == {"p95", "error_rate"}
