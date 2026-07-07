"""Scheduled test-task scanner for the worker process."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from redis import Redis

from app.settings import QUEUE_NAME


def _values_for_field(field: str, minimum: int, maximum: int) -> set[int]:
    """Expand one cron field into allowed integer values."""
    values: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        if not part:
            continue
        if part == "*":
            values.update(range(minimum, maximum + 1))
            continue
        if part.startswith("*/"):
            step = int(part[2:])
            if step <= 0:
                raise ValueError("cron step must be positive")
            values.update(range(minimum, maximum + 1, step))
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise ValueError("cron range start must be <= end")
            values.update(range(start, end + 1))
            continue
        values.add(int(part))
    if not values or min(values) < minimum or max(values) > maximum:
        raise ValueError("cron field out of range")
    return values


def cron_matches(expr: str, now: datetime) -> bool:
    """Return whether a five-field cron expression matches the current minute."""
    fields = expr.strip().split()
    if len(fields) != 5:
        return False
    minute, hour, day, month, weekday = fields
    cron_weekday = (now.weekday() + 1) % 7
    try:
        return (
            now.minute in _values_for_field(minute, 0, 59)
            and now.hour in _values_for_field(hour, 0, 23)
            and now.day in _values_for_field(day, 1, 31)
            and now.month in _values_for_field(month, 1, 12)
            and (cron_weekday in _values_for_field(weekday, 0, 7) or (cron_weekday == 0 and 7 in _values_for_field(weekday, 0, 7)))
        )
    except ValueError:
        return False


def _same_minute(left: datetime | None, right: datetime) -> bool:
    """Return whether two datetimes point at the same minute."""
    if left is None:
        return False
    return left.replace(second=0, microsecond=0) == right.replace(second=0, microsecond=0)


def scheduled_task_due(task: dict[str, Any], now: datetime) -> bool:
    """Decide whether a task should be fired by the lightweight scheduler."""
    schedule = (task.get("schedule_cron") or "").strip()
    if not schedule or not task.get("is_active"):
        return False
    if task.get("task_type") != "api" or (task.get("runner_type") or "platform") != "platform":
        return False
    if _same_minute(task.get("last_run_at"), now):
        return False
    return cron_matches(schedule, now)


def _json_value(value: Any) -> str:
    """Serialize values for MySQL JSON columns."""
    return json.dumps(value or {}, ensure_ascii=False)


def _task_case_ids(task: dict[str, Any]) -> list[int]:
    """Read API case IDs from a task config in new or legacy key form."""
    config = task.get("config") or {}
    if isinstance(config, str):
        config = json.loads(config or "{}")
    raw_ids = config.get("api_case_ids") or config.get("case_ids") or []
    if not isinstance(raw_ids, list):
        return []
    case_ids: list[int] = []
    for value in raw_ids:
        try:
            case_id = int(value)
        except (TypeError, ValueError):
            continue
        if case_id not in case_ids:
            case_ids.append(case_id)
    return case_ids


def _existing_case_ids(cur, case_ids: list[int]) -> list[int]:
    """Keep only API case IDs that still exist in the database."""
    if not case_ids:
        return []
    placeholders = ",".join(["%s"] * len(case_ids))
    cur.execute(f"SELECT id FROM api_cases WHERE id IN ({placeholders})", case_ids)
    found = {int(row["id"]) for row in cur.fetchall() or []}
    return [case_id for case_id in case_ids if case_id in found]


def _create_scheduled_batch(cur, task: dict[str, Any], case_ids: list[int], now: datetime) -> list[int]:
    """Create one scheduled execution batch and queued run rows."""
    batch_no = f"BT-{now:%Y%m%d%H%M%S}-{uuid4().hex[:8]}"
    summary = {"source": "schedule", "schedule_cron": task.get("schedule_cron"), "api_case_ids": case_ids}
    cur.execute(
        """
        INSERT INTO execution_batches
          (batch_no, task_id, trigger_type, environment_id, status, total_count,
           passed_count, failed_count, skipped_count, started_at, summary, created_at, updated_at)
        VALUES
          (%s, %s, 'schedule', %s, 'running', %s, 0, 0, 0, %s, %s, %s, %s)
        """,
        [batch_no, task["id"], task.get("environment_id"), len(case_ids), now, _json_value(summary), now, now],
    )
    batch_id = cur.lastrowid
    run_ids: list[int] = []
    for case_id in case_ids:
        cur.execute(
            """
            INSERT INTO test_runs
              (batch_id, task_id, case_type, case_id, status, logs, report, created_at, updated_at)
            VALUES
              (%s, %s, 'api', %s, 'queued', 'Scheduled task queued', %s, %s, %s)
            """,
            [batch_id, task["id"], case_id, _json_value({}), now, now],
        )
        run_ids.append(cur.lastrowid)
    cur.execute(
        "UPDATE test_tasks SET last_status='running', last_run_at=%s, updated_at=%s WHERE id=%s",
        [now, now, task["id"]],
    )
    return run_ids


def enqueue_due_scheduled_tasks(redis: Redis, now: datetime | None = None) -> int:
    """Scan active scheduled tasks and enqueue due API runs."""
    from app.infrastructure.db import connect_db

    current = (now or datetime.utcnow()).replace(second=0, microsecond=0)
    enqueued = 0
    with connect_db() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT * FROM test_tasks
            WHERE is_active=1 AND task_type='api' AND runner_type='platform'
              AND schedule_cron IS NOT NULL AND schedule_cron <> ''
            """
        )
        for task in cur.fetchall() or []:
            if not scheduled_task_due(task, current):
                continue
            case_ids = _existing_case_ids(cur, _task_case_ids(task))
            if not case_ids:
                cur.execute("UPDATE test_tasks SET last_run_at=%s, updated_at=%s WHERE id=%s", [current, current, task["id"]])
                continue
            for run_id in _create_scheduled_batch(cur, task, case_ids, current):
                redis.rpush(QUEUE_NAME, json.dumps({"run_id": run_id}))
                enqueued += 1
    return enqueued
