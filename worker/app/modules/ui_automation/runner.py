import json
import tempfile
from pathlib import Path
from typing import Any

import pytest


TEST_TEMPLATE = """
import json
from pathlib import Path

import allure

from app.modules.ui_automation.runtime import execute_ui_case


def test_ui_case():
    case = json.loads(Path(r"{case_file}").read_text(encoding="utf-8"))
    report = execute_ui_case(case, run_id={run_id})
    Path(r"{result_file}").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    allure.dynamic.title(case.get("name") or "UI Case")
    assert report["passed"], report
"""


def run_ui_case(case: dict[str, Any], run_id: int | None = None) -> dict[str, Any]:
    """Run a UI case through pytest while Playwright performs the browser actions."""
    with tempfile.TemporaryDirectory(prefix="ui-case-") as tmp:
        tmp_dir = Path(tmp)
        case_file = tmp_dir / "case.json"
        result_file = tmp_dir / "result.json"
        test_file = tmp_dir / "test_ui_case.py"
        allure_dir = tmp_dir / "allure-results"

        case_file.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
        test_file.write_text(TEST_TEMPLATE.format(case_file=case_file, result_file=result_file, run_id=run_id or "None"), encoding="utf-8")
        exit_code = pytest.main([str(test_file), "--alluredir", str(allure_dir), "-q"])

        if result_file.exists():
            report = json.loads(result_file.read_text(encoding="utf-8"))
            report["pytest_exit_code"] = int(exit_code)
            report["allure_results_dir"] = str(allure_dir)
            return report
        return {
            "passed": False,
            "running": False,
            "framework": "pytest + playwright + allure",
            "pytest_exit_code": int(exit_code),
            "error": "pytest did not produce a result file",
            "events": [],
            "screenshots": [],
        }
