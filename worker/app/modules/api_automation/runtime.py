"""API automation runtime implemented with requests and Allure attachments."""

import json
import re
from typing import Any
from urllib.parse import urljoin

import allure
import requests

from app.security.target_guard import is_blocked_url, json_path


VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z0-9_.-]+)\s*}}")


def render_variables(value: Any, variables: dict[str, Any]) -> Any:
    """Replace {{name}} placeholders inside strings, lists, and dictionaries."""
    if isinstance(value, str):
        return VARIABLE_PATTERN.sub(lambda match: str(variables.get(match.group(1), match.group(0))), value)
    if isinstance(value, list):
        return [render_variables(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: render_variables(item, variables) for key, item in value.items()}
    return value


def resolve_case_url(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Resolve full URL from either an absolute case URL or environment base URL plus relative path."""
    environment = case.get("environment") or {}
    variables = environment.get("variables") or {}
    if isinstance(variables, str):
        variables = json.loads(variables or "{}")
    raw_url = render_variables(case["url"], variables)
    if raw_url.startswith(("http://", "https://")):
        return raw_url, variables
    base_url = environment.get("base_url")
    if not base_url:
        raise ValueError("Relative API URL requires an environment base_url")
    return urljoin(base_url.rstrip("/") + "/", raw_url.lstrip("/")), variables


def execute_api_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute one API case with requests.

    这个函数是接口自动化的核心实现。pytest 只负责调度和断言结果，
    真正的请求、断言和报告数据组装都在这里，方便你后续直接改代码侧自动化能力。
    """
    url, variables = resolve_case_url(case)
    if is_blocked_url(url):
        raise ValueError("Private or local targets are not allowed")

    # Normalize headers because MySQL JSON may arrive as dict or JSON string depending on driver behavior.
    headers = json.loads(case["headers"]) if isinstance(case["headers"], str) else (case["headers"] or {})
    headers = render_variables(headers, variables)
    body = render_variables(case.get("body"), variables)
    request_info = {"method": case["method"], "url": url, "headers": headers, "body": body, "environment": case.get("environment")}
    allure.attach(json.dumps(request_info, ensure_ascii=False, indent=2), "request", allure.attachment_type.JSON)

    # requests performs the real HTTP call used by API automation.
    response = requests.request(
        case["method"],
        url,
        headers=headers,
        data=body or None,
        timeout=30,
        allow_redirects=True,
    )
    response_info = {"status_code": response.status_code, "headers": dict(response.headers), "body_preview": response.text[:2000]}
    allure.attach(json.dumps(response_info, ensure_ascii=False, indent=2), "response", allure.attachment_type.JSON)

    checks = []
    expected_status = case.get("assert_status")
    if expected_status:
        # Status assertion is the most common API-test check.
        checks.append({
            "name": "status",
            "passed": response.status_code == expected_status,
            "actual": response.status_code,
            "expected": expected_status,
        })

    expected_text = case.get("assert_text")
    if expected_text:
        # Text assertion checks whether a response contains expected content.
        checks.append({
            "name": "text",
            "passed": expected_text in response.text,
            "actual": response.text[:500],
            "expected": expected_text,
        })

    expected_path = case.get("assert_json_path")
    if expected_path:
        # JSON path assertion reads a simple dotted path like $.data.name.
        try:
            response_json = response.json()
        except ValueError:
            response_json = None
        value = json_path(response_json, expected_path) if response_json is not None else None
        checks.append({
            "name": "json_path",
            "passed": str(value) == str(case.get("assert_json_value")),
            "actual": value,
            "expected": case.get("assert_json_value"),
        })

    passed = all(item["passed"] for item in checks) if checks else response.status_code < 500
    # The returned report is stored in MySQL and rendered by execution records and test reports.
    return {
        "passed": passed,
        "framework": "pytest + requests + allure",
        "request": {"method": case["method"], "url": url, "environment_id": case.get("environment_id")},
        "response": {"status_code": response.status_code, "body_preview": response.text[:2000]},
        "checks": checks,
    }
