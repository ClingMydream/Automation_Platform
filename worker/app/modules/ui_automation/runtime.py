import base64
import json
import os
import time
from typing import Any

import allure
from playwright.sync_api import sync_playwright

from app.infrastructure.db import update_run
from app.security.target_guard import is_blocked_url


UI_STEP_VISUAL_DELAY_MS = int(os.getenv("UI_STEP_VISUAL_DELAY_MS", "700"))


def _screenshot_data_url(page) -> str:
    image = page.screenshot(type="jpeg", quality=70, full_page=False)
    allure.attach(image, "browser screenshot", allure.attachment_type.JPG)
    return "data:image/jpeg;base64," + base64.b64encode(image).decode("ascii")


def _live_report(
    *,
    passed: bool,
    total_steps: int,
    current_step: int,
    current_action: str,
    events: list[dict[str, Any]],
    screenshots: list[dict[str, Any]],
    latest_screenshot: str | None,
) -> dict[str, Any]:
    return {
        "passed": passed,
        "running": not passed,
        "framework": "pytest + playwright + allure",
        "current_step": current_step,
        "total_steps": total_steps,
        "current_action": current_action,
        "events": events,
        "screenshots": screenshots,
        "latest_screenshot": latest_screenshot,
    }


def execute_ui_case(case: dict[str, Any], run_id: int | None = None) -> dict[str, Any]:
    """Execute one UI case with Playwright.

    这里是 UI 自动化代码侧的核心。pytest 负责调度，Playwright 负责浏览器操作，
    allure 负责附件和步骤记录，数据库回写负责页面实时执行窗口。
    """
    steps = json.loads(case["steps"]) if isinstance(case["steps"], str) else case["steps"]
    total_steps = len(steps)
    events: list[dict[str, Any]] = []
    screenshots: list[dict[str, Any]] = []
    latest_screenshot = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox"])
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
                        report=_live_report(
                            passed=False,
                            total_steps=total_steps,
                            current_step=index,
                            current_action=action,
                            events=events,
                            screenshots=screenshots,
                            latest_screenshot=latest_screenshot,
                        ),
                    )

                with allure.step(f"{index}. {action}"):
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
                        latest_screenshot = _screenshot_data_url(page)
                        screenshots.append({"step": index, "title": f"step-{index}", "image": latest_screenshot})
                    else:
                        raise ValueError(f"Unsupported UI action: {action}")

                if action != "screenshot":
                    latest_screenshot = _screenshot_data_url(page)

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
                        logs=f"Completed UI step {index}/{total_steps}",
                        report=_live_report(
                            passed=False,
                            total_steps=total_steps,
                            current_step=index,
                            current_action=action,
                            events=events,
                            screenshots=screenshots,
                            latest_screenshot=latest_screenshot,
                        ),
                    )

                if UI_STEP_VISUAL_DELAY_MS > 0:
                    page.wait_for_timeout(UI_STEP_VISUAL_DELAY_MS)
        finally:
            browser.close()

    return {
        "passed": True,
        "running": False,
        "framework": "pytest + playwright + allure",
        "current_step": total_steps,
        "total_steps": total_steps,
        "events": events,
        "screenshots": screenshots,
        "latest_screenshot": latest_screenshot,
    }
