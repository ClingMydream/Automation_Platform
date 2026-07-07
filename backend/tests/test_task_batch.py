"""Tests for API task batch configuration helpers."""

from fastapi import HTTPException
import pytest

from app.models.entities import ExecutionBatch, TestResult as ResultModel, TestRun as RunModel, TestTask as TaskModel
from app.modules.test_tasks.service import api_case_ids_from_task, failed_api_case_ids_from_batch


class FakeQuery:
    """Tiny query double that supports the filter/all chain used by service helpers."""

    def __init__(self, rows):
        """Keep rows in memory for the fake SQLAlchemy query."""
        self.rows = rows

    def filter(self, *_, **__):
        """Ignore SQLAlchemy filter expressions because test rows are already scoped."""
        return self

    def all(self):
        """Return all rows provided to this query double."""
        return self.rows


class FakeDb:
    """Tiny DB double that returns rows by model class."""

    def __init__(self, rows_by_model):
        """Store a mapping from ORM model to fake query rows."""
        self.rows_by_model = rows_by_model

    def query(self, model):
        """Return a fake query for the requested ORM model."""
        return FakeQuery(self.rows_by_model.get(model, []))


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


def test_failed_api_case_ids_from_batch_prefers_result_evidence():
    """Retry helper should collect unique failed API case IDs from result rows first."""
    batch = ExecutionBatch(id=7, batch_no="BT-7", status="failed")
    rows = [
        ResultModel(batch_id=7, case_type="api", result_type="api", case_id=11, status="failed"),
        ResultModel(batch_id=7, case_type="api", result_type="api", case_id=11, status="error"),
        ResultModel(batch_id=7, case_type="ui", result_type="ui", case_id=22, status="failed"),
    ]
    db = FakeDb({ResultModel: rows, RunModel: [RunModel(batch_id=7, case_type="api", case_id=33, status="failed")]})

    assert failed_api_case_ids_from_batch(db, batch) == [11]


def test_failed_api_case_ids_from_batch_falls_back_to_run_rows():
    """Retry helper should use failed run rows when result center evidence is not available."""
    batch = ExecutionBatch(id=8, batch_no="BT-8", status="failed")
    db = FakeDb({
        ResultModel: [],
        RunModel: [
            RunModel(batch_id=8, case_type="api", case_id=31, status="failed"),
            RunModel(batch_id=8, case_type="api", case_id=31, status="error"),
            RunModel(batch_id=8, case_type="api", case_id=32, status="failed"),
        ],
    })

    assert failed_api_case_ids_from_batch(db, batch) == [31, 32]
