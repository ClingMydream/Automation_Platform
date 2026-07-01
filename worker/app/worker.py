import base64
import json
import os
import time
from contextlib import closing
from dataclasses import dataclass
from typing import Any

import httpx
import pymysql
from playwright.sync_api import sync_playwright
from redis import Redis
from urllib.parse import urlparse
import ipaddress
import socket


QUEUE_NAME = "automation:runs"
DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]
ALLOW_PRIVATE_TARGETS = os.getenv("ALLOW_PRIVATE_TARGETS", "false").lower() == "true"
UI_STEP_VISUAL_DELAY_MS = int(os.getenv("UI_STEP_VISUAL_DELAY_MS", "700"))


@dataclass
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


def parse_mysql_url(url: str) -> DbConfig:
    parsed = urlparse(url.replace("mysql+pymysql://", "mysql://"))
    return DbConfig(
        host=parsed.hostname or "mysql",
        port=parsed.port or 3306,
        user=parsed.username or "automation",
        password=parsed.password or "",
        database=(parsed.path or "/automation_platform").lstrip("/"),
    )


DB = parse_mysql_url(DATABASE_URL)


def connect_db():
    return pymysql.connect(
        host=DB.host,
        port=DB.port,
        user=DB.user,
        password=DB.password,
        database=DB.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def update_run(run_id: int, **fields: Any) -> None:
    keys = list(fields)
    assignments = ", ".join(f"{key}=%s" for key in keys)
    values = [json.dumps(value, ensure_ascii=False) if key == "report" else value for key, value in fields.items()]
    with closing(connect_db()) as conn, conn.cursor() as cur:
        cur.execute(f"UPDATE test_runs SET {assignments}, updated_at=NOW() WHERE id=%s", [*values, run_id])


def fetch_run_case(run_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    with closing(connect_db()) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM test_runs WHERE id=%s", [run_id])
        run = cur.fetchone()
        table = "api_cases" if run["case_type"] == "api" else "ui_cases"
        cur.execute(f"SELECT * FROM {table} WHERE id=%s", [run["case_id"]])
        case = cur.fetchone()
    return run, case


def is_blocked_url(url: str) -> bool:
    if ALLOW_PRIVATE_TARGETS:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return True
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        return True
    candidates: list[str] = []
    try:
        candidates.append(str(ipaddress.ip_address(host)))
    except ValueError:
        for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP):
            candidates.append(info[4][0])
    for candidate in candidates:
        ip = ipaddress.ip_address(candidate)
        if not ip.is_global or ip == ipaddress.ip_address("169.254.169.254"):
            return True
    return False


def json_path(data: Any, path: str | None) -> Any:
    if not path:
        return None
    current = data
    for part in path.strip("$.").split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def run_api_case(case: dict[str, Any]) -> dict[str, Any]:
    if is_blocked_url(case["url"]):
        raise ValueError("Private or local targets are not allowed")
    headers = json.loads(case["headers"]) if isinstance(case["headers"], str) else (case["headers"] or {})
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.request(case["method"], case["url"], headers=headers, content=case.get("body") or None)
    checks = []
    expected_status = case.get("assert_status")
    if expected_status:
        checks.append({"name": "status", "passed": response.status_code == expected_status, "actual": response.status_code, "expected": expected_status})
    expected_text = case.get("assert_text")
    if expected_text:
        checks.append({"name": "text", "passed": expected_text in response.text, "expected": expected_text})
    expected_path = case.get("assert_json_path")
    if expected_path:
        value = json_path(response.json(), expected_path)
        checks.append({"name": "json_path", "passed": str(value) == str(case.get("assert_json_value")), "actual": value, "expected": case.get("assert_json_value")})
    passed = all(item["passed"] for item in checks) if checks else response.status_code < 500
    return {
        "passed": passed,
        "request": {"method": case["method"], "url": case["url"]},
        "response": {"status_code": response.status_code, "body_preview": response.text[:2000]},
        "checks": checks,
    }


def screenshot_data_url(page) -> str:
    image = page.screenshot(type="jpeg", quality=70, full_page=False)
    return "data:image/jpeg;base64," + base64.b64encode(image).decode("ascii")


def run_ui_case(case: dict[str, Any], run_id: int | None = None) -> dict[str, Any]:
    steps = json.loads(case["steps"]) if isinstance(case["steps"], str) else case["steps"]
    total_steps = len(steps)
    events = []
    screenshots = []
    latest_screenshot = None
    with sync_playwright() as p:
        launch_options = {
            "headless": True,
            "args": ["--disable-dev-shm-usage", "--no-sandbox"],
        }
        browser = p.chromium.launch(**launch_options)
        page = browser.new_page()
        try:
            for index, step in enumerate(steps, start=1):
                step_start = time.perf_counter()
                action = step["action"]
                target = step.get("target")
                value = step.get("value")
                timeout = step.get("timeout_ms") or 5000
                if run_id:
                    update_run(
                        run_id,
                        logs=f"Running UI step {index}/{total_steps}: {action}",
                        report={
                            "passed": False,
                            "running": True,
                            "current_step": index,
                            "total_steps": total_steps,
                            "current_action": action,
                            "events": events,
                            "screenshots": screenshots,
                            "latest_screenshot": latest_screenshot,
                        },
                    )
                if action == "goto":
                    if not value or is_blocked_url(value):
                        raise ValueError("Private or local targets are not allowed")
                    page.goto(value, wait_until="networkidle", timeout=timeout)
                elif action == "click":
                    page.click(target, timeout=timeout)
                elif action == "fill":
                    page.fill(target, value or "", timeout=timeout)
                elif action == "wait":
                    page.wait_for_timeout(int(value or timeout))
                elif action == "assert_text":
                    page.get_by_text(value or "", exact=False).wait_for(timeout=timeout)
                elif action == "screenshot":
                    latest_screenshot = screenshot_data_url(page)
                    screenshots.append({"step": index, "title": f"step-{index}", "image": latest_screenshot})
                else:
                    raise ValueError(f"Unsupported UI action: {action}")
                if action != "screenshot":
                    latest_screenshot = screenshot_data_url(page)
                events.append({
                    "step": index,
                    "action": action,
                    "target": target,
                    "value": value,
                    "status": "passed",
                    "elapsed_ms": int((time.perf_counter() - step_start) * 1000),
                    "url": page.url,
                    "title": page.title(),
                })
                if run_id:
                    update_run(
                        run_id,
                        logs=f"Completed UI step {index}/{len(steps)}",
                        report={
                            "passed": False,
                            "running": True,
                            "current_step": index,
                            "total_steps": total_steps,
                            "current_action": action,
                            "events": events,
                            "screenshots": screenshots,
                            "latest_screenshot": latest_screenshot,
                        },
                    )
                if UI_STEP_VISUAL_DELAY_MS > 0:
                    page.wait_for_timeout(UI_STEP_VISUAL_DELAY_MS)
        finally:
            browser.close()
    return {
        "passed": True,
        "running": False,
        "current_step": total_steps,
        "total_steps": total_steps,
        "events": events,
        "screenshots": screenshots,
        "latest_screenshot": latest_screenshot,
    }


def process_run(run_id: int) -> None:
    update_run(run_id, status="running", logs="Worker started")
    start = time.perf_counter()
    try:
        run, case = fetch_run_case(run_id)
        report = run_api_case(case) if run["case_type"] == "api" else run_ui_case(case, run_id)
        duration_ms = int((time.perf_counter() - start) * 1000)
        status = "passed" if report.get("passed") else "failed"
        update_run(run_id, status=status, duration_ms=duration_ms, logs="Run completed", error=None, report=report)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        update_run(run_id, status="failed", duration_ms=duration_ms, logs="Run failed", error=str(exc), report={"passed": False})


def main() -> None:
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    while True:
        _, payload = redis.blpop(QUEUE_NAME)
        process_run(json.loads(payload)["run_id"])


if __name__ == "__main__":
    main()
