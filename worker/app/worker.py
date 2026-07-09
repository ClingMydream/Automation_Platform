"""Worker process entrypoint that consumes queued test runs and writes reports."""

import json
import time

from redis import Redis

from app.infrastructure.db import fetch_run_case, persist_run_result, update_run
from app.modules.api_automation.runner import run_api_case
from app.modules.performance_automation.runner import run_performance_case
from app.modules.ui_automation.runner import run_ui_case
from app.scheduler import enqueue_due_scheduled_tasks
from app.settings import QUEUE_NAME, REDIS_URL, SCHEDULER_ENABLED, SCHEDULER_POLL_SECONDS


def process_run(run_id: int) -> None:
    """Queue task entrypoint.

    worker.py 只做三件事：
    1. 从数据库拿到执行任务和用例。
    2. 按用例类型分发到独立自动化模块。
    3. 把最终报告回写到数据库。
    """
    # Mark the run as active before loading the case so the frontend sees immediate progress.
    update_run(run_id, status="running", logs="Worker started")
    start = time.perf_counter()
    try:
        # The run record decides whether this dispatches to API automation or UI automation.
        run, case = fetch_run_case(run_id)
        if run["case_type"] == "api":
            report = run_api_case(case)
        elif run["case_type"] == "performance":
            report = run_performance_case(case)
        else:
            report = run_ui_case(case, run_id)
        duration_ms = int((time.perf_counter() - start) * 1000)
        status = "passed" if report.get("passed") else "failed"
        # Persist the final status and report for execution records and test reports.
        update_run(run_id, status=status, duration_ms=duration_ms, logs="Run completed", error=report.get("error"), report=report)
        persist_run_result(run_id, status, duration_ms, report, report.get("error"))
    except Exception as exc:
        # Any unexpected error is converted into a failed report instead of crashing the worker loop.
        duration_ms = int((time.perf_counter() - start) * 1000)
        report = {"passed": False, "error": str(exc)}
        update_run(
            run_id,
            status="failed",
            duration_ms=duration_ms,
            logs="Run failed",
            error=str(exc),
            report=report,
        )
        persist_run_result(run_id, "failed", duration_ms, report, str(exc))


def main() -> None:
    """Start the worker loop, consume queued run IDs, and scan scheduled tasks."""
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    last_schedule_check = 0.0
    while True:
        now = time.monotonic()
        if SCHEDULER_ENABLED and now - last_schedule_check >= SCHEDULER_POLL_SECONDS:
            try:
                enqueue_due_scheduled_tasks(redis)
            except Exception as exc:
                print(f"Scheduler scan failed: {exc}", flush=True)
            last_schedule_check = now
        # The timeout lets the worker wake up regularly to scan scheduled tasks.
        item = redis.blpop(QUEUE_NAME, timeout=5)
        if item is None:
            continue
        _, payload = item
        process_run(json.loads(payload)["run_id"])


if __name__ == "__main__":
    main()
