"""Tests for single-run report summaries."""

from datetime import UTC, datetime

from app.models.entities import PerformanceScenario, TestResult as ResultModel, TestRun as RunModel
from app.modules.reports.service import case_name_for_run, report_summary, result_id_for_run


class FakeQuery:
    """Tiny query object that returns one configured result row."""

    def __init__(self, row):
        """Store the row returned by first()."""
        self.row = row

    def filter(self, *_args, **_kwargs):
        """Ignore SQLAlchemy filter expressions in this unit test."""
        return self

    def order_by(self, *_args, **_kwargs):
        """Ignore ordering expressions because the row is already selected."""
        return self

    def first(self):
        """Return the configured result row."""
        return self.row


class FakeDb:
    """Tiny fake database used by single-run report tests."""

    def __init__(self, scenario, result):
        """Store the scenario and result row returned by helpers."""
        self.scenario = scenario
        self.result = result

    def get(self, model, item_id):
        """Return the fake performance scenario when requested."""
        if model is PerformanceScenario and item_id == self.scenario.id:
            return self.scenario
        return None

    def query(self, _model):
        """Return a fake query over the result row."""
        return FakeQuery(self.result)


def test_performance_run_report_uses_scenario_name_and_result_id():
    """Single performance reports should resolve scenario names and result-center IDs."""
    now = datetime.now(UTC)
    scenario = PerformanceScenario(id=5, code="PERF-HOME", name="首页压测", target_url="https://example.com")
    result = ResultModel(id=31, batch_id=9, case_type="performance", case_id=5, result_type="performance", status="passed")
    run = RunModel(
        id=17,
        batch_id=9,
        task_id=3,
        case_type="performance",
        case_id=5,
        status="passed",
        duration_ms=1000,
        report={"metrics": {"avg_ms": 120}},
        created_at=now,
        updated_at=now,
    )
    db = FakeDb(scenario, result)

    case_name = case_name_for_run(db, run)
    report = report_summary(db, run, case_name)

    assert case_name == "首页压测"
    assert result_id_for_run(db, run) == 31
    assert report["result_id"] == 31
    assert report["case_name"] == "首页压测"
