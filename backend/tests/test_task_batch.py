"""Tests for API task batch configuration helpers."""

from fastapi import HTTPException
import pytest

from app.models.entities import TestTask as TaskModel
from app.modules.test_tasks.service import api_case_ids_from_task


def test_api_case_ids_from_task_prefers_new_key_and_deduplicates():
    """Task config should accept api_case_ids and remove duplicate IDs in order."""
    task = TaskModel(code="TASK-API", name="API task", task_type="api", config={"api_case_ids": ["1", 2, 2, "3"]})

    assert api_case_ids_from_task(task) == [1, 2, 3]


def test_api_case_ids_from_task_supports_legacy_case_ids_key():
    """Task config should keep supporting the older case_ids key."""
    task = TaskModel(code="TASK-OLD", name="Old task", task_type="api", config={"case_ids": [4, "5"]})

    assert api_case_ids_from_task(task) == [4, 5]


def test_api_case_ids_from_task_rejects_non_list():
    """A non-list api_case_ids value should produce a clear 400 error."""
    task = TaskModel(code="TASK-BAD", name="Bad task", task_type="api", config={"api_case_ids": "1,2"})

    with pytest.raises(HTTPException) as exc:
        api_case_ids_from_task(task)

    assert exc.value.status_code == 400
