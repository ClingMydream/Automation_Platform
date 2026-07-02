"""Pytest runner wrapper for executing one API case and collecting the report."""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest


TEST_TEMPLATE = """
import json
from pathlib import Path

import allure

from app.modules.api_automation.runtime import execute_api_case


def test_api_case():
    # Pytest entry point for executing the API case passed through environment variables.
    case = json.loads(Path(r"{case_file}").read_text(encoding="utf-8"))
    report = execute_api_case(case)
    Path(r"{result_file}").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    allure.dynamic.title(case.get("name") or "API Case")
    assert report["passed"], report
"""


def run_api_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run an API case through pytest so code-side automation matches real test projects."""
    with tempfile.TemporaryDirectory(prefix="api-case-") as tmp:
        tmp_dir = Path(tmp)
        # Temporary files pass case input and report output between this wrapper and pytest.
        case_file = tmp_dir / "case.json"
        result_file = tmp_dir / "result.json"
        test_file = tmp_dir / "test_api_case.py"
        allure_dir = tmp_dir / "allure-results"

        case_file.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
        test_file.write_text(TEST_TEMPLATE.format(case_file=case_file, result_file=result_file), encoding="utf-8")
        # pytest produces Allure raw result files and executes the generated test function.
        exit_code = pytest.main([str(test_file), "--alluredir", str(allure_dir), "-q"])

        if result_file.exists():
            # The runtime produced a structured report; enrich it with pytest metadata.
            report = json.loads(result_file.read_text(encoding="utf-8"))
            report["pytest_exit_code"] = int(exit_code)
            report["allure_results_dir"] = str(allure_dir)
            return report
        # If pytest failed before writing output, return a normalized failed report.
        return {
            "passed": False,
            "framework": "pytest + requests + allure",
            "pytest_exit_code": int(exit_code),
            "error": "pytest did not produce a result file",
            "checks": [],
        }
