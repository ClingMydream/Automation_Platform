"""Tests for API task batch configuration helpers."""

from fastapi import HTTPException
import pytest

from app.models.entities import ExecutionBatch, PerformanceScenario, TestResult as ResultModel, TestRun as RunModel, TestTask as TaskModel
from app.modules.test_tasks.schemas import TestTaskCreate as TaskCreateSchema
from app.modules.test_tasks import service as task_service
from app.modules.test_tasks.service import api_case_ids_from_task, external_task_config, failed_api_case_ids_from_batch, performance_tags_from_task, validate_jmeter_config, validate_performance_task_scenarios


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


def test_performance_task_can_select_scenarios_by_any_tag():
    """Performance tasks should expand tag selectors into active scenario IDs."""
    task = TaskModel(code="TASK-PERF", name="Perf task", task_type="performance", config={"performance_tags": ["smoke"]})
    rows = [
        PerformanceScenario(id=1, code="P1", name="Home", target_url="https://example.com", tags=["smoke"], is_active=True),
        PerformanceScenario(id=2, code="P2", name="Cart", target_url="https://example.com/cart", tags=["regression"], is_active=True),
        PerformanceScenario(id=3, code="P3", name="Old", target_url="https://example.com/old", tags=["smoke"], is_active=False),
    ]
    db = FakeDb({PerformanceScenario: rows})

    assert validate_performance_task_scenarios(db, task) == [1]


def test_performance_task_can_select_scenarios_by_all_tags():
    """The all match mode should require every selected tag to exist on a scenario."""
    task = TaskModel(code="TASK-PERF-ALL", name="Perf all", task_type="performance", config={"performance_tags": ["smoke", "checkout"], "performance_tag_match": "all"})
    rows = [
        PerformanceScenario(id=4, code="P4", name="Smoke only", target_url="https://example.com", tags=["smoke"], is_active=True),
        PerformanceScenario(id=5, code="P5", name="Checkout", target_url="https://example.com/cart", tags=["smoke", "checkout"], is_active=True),
    ]
    db = FakeDb({PerformanceScenario: rows})

    assert validate_performance_task_scenarios(db, task) == [5]


def test_performance_tags_from_task_rejects_invalid_shape():
    """Tag selectors should be lists and the match mode should be explicit."""
    task = TaskModel(code="TASK-BAD-TAGS", name="Bad tags", task_type="performance", config={"performance_tags": "smoke"})

    with pytest.raises(HTTPException) as exc:
        performance_tags_from_task(task)

    assert exc.value.status_code == 400


def test_validate_jmeter_config_accepts_metadata_object():
    """JMeter metadata should allow CI runners to read task execution hints."""
    payload = TaskCreateSchema(
        code="TASK-JMETER",
        name="JMeter task",
        task_type="performance",
        runner_type="jmeter",
        config={"jmeter": {"jmx_path": "tests/login.jmx", "report_dir": "reports/login", "jtl_path": "reports/login.jtl", "variables": {"threads": 10}}},
    )

    validate_jmeter_config(payload)


def test_validate_jmeter_config_rejects_invalid_metadata_shape():
    """JMeter metadata should stay predictable for external runners."""
    payload = TaskCreateSchema(
        code="TASK-JMETER-BAD",
        name="Bad JMeter task",
        task_type="performance",
        runner_type="jmeter",
        config={"jmeter": {"jmx_path": ["bad"], "variables": []}},
    )

    with pytest.raises(HTTPException) as exc:
        validate_jmeter_config(payload)

    assert exc.value.status_code == 400


def test_external_task_config_returns_jmeter_metadata_without_tokens(monkeypatch):
    """External config should expose task metadata and callback URLs without secrets."""
    settings = type("Settings", (), {"public_base_url": "http://example.test"})()
    monkeypatch.setattr(task_service, "get_settings", lambda: settings)
    task = TaskModel(
        id=12,
        code="TASK-JMETER-CONFIG",
        name="JMeter config task",
        task_type="performance",
        runner_type="jmeter",
        environment_id=3,
        is_active=True,
        config={"jmeter": {"jmx_path": "tests/login.jmx", "variables": {"threads": 10}}},
    )

    result = external_task_config(task)

    assert result["code"] == "TASK-JMETER-CONFIG"
    assert result["jmeter"]["jmx_path"] == "tests/login.jmx"
    assert result["callbacks"]["result_upload_url"] == "http://example.test/api/v1/test-tasks/by-code/TASK-JMETER-CONFIG/results/batch"
    assert "token" not in result
