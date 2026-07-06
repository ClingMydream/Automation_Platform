"""Tests for API case debug run creation."""

from fastapi import HTTPException
import pytest

from app.models.entities import ApiCase, TestRun as RunModel
from app.modules.api_testing import router as api_router


class FakeDb:
    """Tiny fake session that records writes without using MySQL or Redis."""

    def __init__(self, case):
        """Store the case returned by db.get and capture saved objects."""
        self.case = case
        self.added = []
        self.committed = False

    def get(self, model, item_id):
        """Return the configured API case when requested."""
        if model is ApiCase and item_id == 1:
            return self.case
        return None

    def add(self, item):
        """Capture the new TestRun object."""
        self.added.append(item)

    def commit(self):
        """Mark that the transaction would have been committed."""
        self.committed = True

    def refresh(self, item):
        """Simulate SQLAlchemy assigning a primary key after commit."""
        item.id = 99


def test_create_debug_run_enqueues_api_case(monkeypatch):
    """A valid API case should create a queued debug run and enqueue it."""
    enqueued = []
    fake_db = FakeDb(case=ApiCase(id=1, project_id=1, name="demo", method="GET", url="https://example.com"))
    monkeypatch.setattr(api_router, "enqueue_run", lambda run_id: enqueued.append(run_id))

    run = api_router.create_debug_run(fake_db, 1)

    assert isinstance(run, RunModel)
    assert run.id == 99
    assert run.case_type == "api"
    assert run.case_id == 1
    assert run.status == "queued"
    assert fake_db.committed is True
    assert enqueued == [99]


def test_create_debug_run_rejects_missing_case():
    """A missing API case should return the same 404 behavior as normal execution."""
    with pytest.raises(HTTPException) as exc:
        api_router.create_debug_run(FakeDb(case=None), 1)

    assert exc.value.status_code == 404
