"""Tests for execution-batch report summaries."""

from datetime import UTC, datetime

from app.models.entities import ExecutionBatch, TestResult as ResultModel, TestTask as TaskModel
from app.modules.reports.service import batch_report_summary


class FakeQuery:
    """Tiny query object that returns preconfigured result rows."""

    def __init__(self, rows):
        """Store rows for chained filter/order_by/all calls."""
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        """Ignore SQLAlchemy filter expressions in this unit test."""
        return self

    def order_by(self, *_args, **_kwargs):
        """Ignore ordering expressions because rows are already ordered."""
        return self

    def all(self):
        """Return the configured result rows."""
        return self.rows


class FakeDb:
    """Tiny fake database used by report service tests."""

    def __init__(self, task, results):
        """Store the task and result rows returned by helpers."""
        self.task = task
        self.results = results

    def get(self, model, item_id):
        """Return the fake task when requested."""
        if model is TaskModel and item_id == self.task.id:
            return self.task
        return None

    def query(self, _model):
        """Return a fake query over result rows."""
        return FakeQuery(self.results)


def test_batch_report_summary_includes_stats_and_results():
    """Batch reports should expose statistics and result evidence for the frontend."""
    now = datetime.now(UTC)
    task = TaskModel(id=7, code="TASK", name="接口冒烟", task_type="api")
    batch = ExecutionBatch(
        id=3,
        batch_no="BT-001",
        task_id=7,
        trigger_type="manual",
        environment_id=2,
        status="passed",
        total_count=1,
        passed_count=1,
        failed_count=0,
        skipped_count=0,
        duration_ms=123,
        summary={"source": "unit"},
        created_at=now,
        updated_at=now,
    )
    result = ResultModel(
        id=11,
        batch_id=3,
        task_id=7,
        case_type="api",
        case_id=5,
        result_type="api",
        status="passed",
        duration_ms=123,
        request_data={"url": "https://example.com"},
        response_data={"status_code": 200},
        assertions=[{"name": "status", "passed": True}],
        metrics={"framework": "pytest"},
        error=None,
        failure_category=None,
    )

    report = batch_report_summary(FakeDb(task, [result]), batch)

    assert report["report_key"] == "batch-3"
    assert report["report_kind"] == "batch"
    assert report["case_name"] == "接口冒烟"
    assert report["summary"]["passed"] == 1
    assert report["check_count"] == 1
    assert report["report"]["results"][0]["response_data"]["status_code"] == 200
