"""Tests for the worker scheduled-task helpers."""

import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "mysql+pymysql://automation:password@127.0.0.1:3306/automation_platform")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scheduler import cron_matches, scheduled_task_due  # noqa: E402


def test_cron_matches_step_and_exact_hour():
    """Five-field cron expressions should support steps and exact values."""
    now = datetime(2026, 7, 7, 10, 20)

    assert cron_matches("*/10 10 * * *", now)
    assert not cron_matches("*/15 10 * * *", now)
    assert not cron_matches("*/10 9 * * *", now)


def test_cron_matches_lists_and_ranges():
    """Cron fields should support comma lists and ranges for simple schedules."""
    now = datetime(2026, 7, 7, 8, 5)

    assert cron_matches("5 7-9 * * 2,3", now)
    assert not cron_matches("5 7-9 * * 1", now)


def test_scheduled_task_due_rejects_duplicate_same_minute():
    """A task should not be scheduled twice in the same minute."""
    now = datetime(2026, 7, 7, 8, 5)
    task = {
        "schedule_cron": "* * * * *",
        "is_active": True,
        "task_type": "api",
        "runner_type": "platform",
        "last_run_at": datetime(2026, 7, 7, 8, 5, 12),
    }

    assert not scheduled_task_due(task, now)


def test_scheduled_task_due_only_allows_api_platform_tasks():
    """The lightweight scheduler should only auto-run API tasks owned by platform runner."""
    now = datetime(2026, 7, 7, 8, 5)
    base = {"schedule_cron": "* * * * *", "is_active": True, "last_run_at": None}

    assert scheduled_task_due({**base, "task_type": "api", "runner_type": "platform"}, now)
    assert not scheduled_task_due({**base, "task_type": "ui", "runner_type": "platform"}, now)
    assert not scheduled_task_due({**base, "task_type": "api", "runner_type": "jmeter"}, now)
