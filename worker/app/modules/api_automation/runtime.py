import json
from typing import Any

import allure
import requests

from app.security.target_guard import is_blocked_url, json_path


def execute_api_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute one API case with requests.

    这个函数是接口自动化的核心实现。pytest 只负责调度和断言结果，
    真正的请求、断言和报告数据组装都在这里，方便你后续直接改代码侧自动化能力。
    """
    if is_blocked_url(case["url"]):
        raise ValueError("Private or local targets are not allowed")

    headers = json.loads(case["headers"]) if isinstance(case["headers"], str) else (case["headers"] or {})
    request_info = {"method": case["method"], "url": case["url"], "headers": headers, "body": case.get("body")}
    allure.attach(json.dumps(request_info, ensure_ascii=False, indent=2), "request", allure.attachment_type.JSON)

    response = requests.request(
        case["method"],
        case["url"],
        headers=headers,
        data=case.get("body") or None,
        timeout=30,
        allow_redirects=True,
    )
    response_info = {"status_code": response.status_code, "headers": dict(response.headers), "body_preview": response.text[:2000]}
    allure.attach(json.dumps(response_info, ensure_ascii=False, indent=2), "response", allure.attachment_type.JSON)

    checks = []
    expected_status = case.get("assert_status")
    if expected_status:
        checks.append({
            "name": "status",
            "passed": response.status_code == expected_status,
            "actual": response.status_code,
            "expected": expected_status,
        })

    expected_text = case.get("assert_text")
    if expected_text:
        checks.append({
            "name": "text",
            "passed": expected_text in response.text,
            "actual": response.text[:500],
            "expected": expected_text,
        })

    expected_path = case.get("assert_json_path")
    if expected_path:
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
    return {
        "passed": passed,
        "framework": "pytest + requests + allure",
        "request": {"method": case["method"], "url": case["url"]},
        "response": {"status_code": response.status_code, "body_preview": response.text[:2000]},
        "checks": checks,
    }
