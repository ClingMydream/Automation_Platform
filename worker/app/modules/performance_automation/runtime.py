"""Minimal performance execution runtime for platform-owned scenarios."""

from __future__ import annotations

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

from app.security.target_guard import is_blocked_url


def _headers(value: Any) -> dict[str, str]:
    """Normalize headers loaded from MySQL JSON."""
    if isinstance(value, str):
        return json.loads(value or "{}")
    return value or {}


def _percentile(values: list[float], percentile: float) -> float | None:
    """Calculate a simple nearest-rank percentile in milliseconds."""
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percentile / 100) * len(ordered) + 0.5) - 1))
    return round(ordered[index], 2)


def _single_request(case: dict[str, Any]) -> dict[str, Any]:
    """Execute one HTTP sample and return timing plus status."""
    started = time.perf_counter()
    try:
        response = requests.request(
            case["method"],
            case["target_url"],
            headers=_headers(case.get("headers")),
            data=case.get("body") or None,
            timeout=30,
            allow_redirects=True,
        )
        duration_ms = (time.perf_counter() - started) * 1000
        return {"ok": response.status_code < 500, "status_code": response.status_code, "duration_ms": duration_ms}
    except requests.RequestException as exc:
        duration_ms = (time.perf_counter() - started) * 1000
        return {"ok": False, "status_code": None, "duration_ms": duration_ms, "error": str(exc)}


def execute_performance_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a bounded HTTP performance scenario and summarize metrics."""
    target_url = case["target_url"]
    if is_blocked_url(target_url):
        raise ValueError("Private or local performance targets are not allowed")
    concurrency = max(1, min(int(case.get("concurrency") or 1), 200))
    duration_seconds = max(1, min(int(case.get("duration_seconds") or 1), 300))
    max_samples = max(concurrency, min(concurrency * duration_seconds, 1000))
    started = time.perf_counter()
    samples = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_single_request, case) for _ in range(max_samples)]
        for future in as_completed(futures):
            samples.append(future.result())
            if time.perf_counter() - started >= duration_seconds:
                break
    elapsed_seconds = max(time.perf_counter() - started, 0.001)
    durations = [sample["duration_ms"] for sample in samples]
    failures = [sample for sample in samples if not sample["ok"]]
    error_rate = round((len(failures) / len(samples)) * 100, 2) if samples else 100
    avg_ms = round(statistics.mean(durations), 2) if durations else None
    p95_ms = _percentile(durations, 95)
    p99_ms = _percentile(durations, 99)
    tps = round(len(samples) / elapsed_seconds, 2)
    threshold_p95_ms = case.get("threshold_p95_ms")
    threshold_error_rate = case.get("threshold_error_rate")
    checks = [
        {"name": "p95", "passed": threshold_p95_ms is None or (p95_ms or 0) <= threshold_p95_ms, "actual": p95_ms, "expected": threshold_p95_ms},
        {"name": "error_rate", "passed": threshold_error_rate is None or error_rate <= threshold_error_rate, "actual": error_rate, "expected": threshold_error_rate},
    ]
    passed = all(check["passed"] for check in checks)
    metrics = {
        "avg_ms": avg_ms,
        "p95_ms": p95_ms,
        "p99_ms": p99_ms,
        "tps": tps,
        "error_rate": error_rate,
        "samples": len(samples),
        "concurrency": concurrency,
    }
    return {
        "passed": passed,
        "framework": "platform + requests",
        "request": {"method": case["method"], "url": target_url, "scenario_id": case.get("id")},
        "response": {"sample_status_codes": [sample.get("status_code") for sample in samples[:20]]},
        "checks": checks,
        "metrics": metrics,
        "error": failures[0].get("error") if failures else None,
    }
