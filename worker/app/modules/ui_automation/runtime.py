"""UI automation runtime implemented with Playwright and Allure attachments."""

import base64
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import allure
from playwright.sync_api import sync_playwright

from app.infrastructure.db import update_run
from app.security.target_guard import is_blocked_url


UI_STEP_VISUAL_DELAY_MS = int(os.getenv("UI_STEP_VISUAL_DELAY_MS", "700"))
UI_RECORD_VIDEO = os.getenv("UI_RECORD_VIDEO", "true").lower() not in {"0", "false", "no"}
UI_RECORD_VIDEO_MAX_MB = int(os.getenv("UI_RECORD_VIDEO_MAX_MB", "25"))
UI_DOM_SNAPSHOT_MAX_CHARS = int(os.getenv("UI_DOM_SNAPSHOT_MAX_CHARS", "60000"))


def _screenshot_data_url(page) -> str:
    """Capture the current Playwright page as a data URL."""
    # Screenshots are attached to Allure and embedded into the live execution report.
    image = page.screenshot(type="jpeg", quality=70, full_page=False)
    allure.attach(image, "browser screenshot", allure.attachment_type.JPG)
    return "data:image/jpeg;base64," + base64.b64encode(image).decode("ascii")


def _recording_data_url(page) -> tuple[str | None, str | None, str | None]:
    """Return a browser recording as a data URL after Playwright saves the video file."""
    video = getattr(page, "video", None)
    if not video:
        return None, None, None
    try:
        video_path = Path(video.path())
        content = video_path.read_bytes()
    except Exception as exc:
        return None, None, f"读取 UI 录屏失败：{exc}"
    max_bytes = UI_RECORD_VIDEO_MAX_MB * 1024 * 1024
    if len(content) > max_bytes:
        return None, None, f"UI 录屏超过 {UI_RECORD_VIDEO_MAX_MB}MB，已跳过内嵌保存"
    allure.attach(content, "browser recording", "video/webm")
    return "data:video/webm;base64," + base64.b64encode(content).decode("ascii"), video_path.name, None


def _failure_dom_snapshot(page) -> tuple[str | None, str | None]:
    """Capture a bounded HTML snapshot and an actionable failure hint."""
    try:
        html = page.content()
    except Exception as exc:
        return None, f"DOM 快照采集失败：{exc}"
    if len(html) > UI_DOM_SNAPSHOT_MAX_CHARS:
        html = html[:UI_DOM_SNAPSHOT_MAX_CHARS] + "\n<!-- DOM snapshot truncated -->"
    allure.attach(html, "failure dom snapshot", allure.attachment_type.HTML)
    return html, None


def _failure_advice(action: str, target: str | None, value: str | None, error: str) -> list[str]:
    """Build human-readable advice for the failed UI step."""
    advice = [f"失败动作：{action}", f"错误信息：{error}"]
    if target:
        advice.append(f"检查选择器是否仍存在：{target}")
    if action in {"click", "fill"}:
        advice.append("确认元素没有被弹窗、遮罩、加载态或 iframe 隔开。")
    if action == "assert_text" and value:
        advice.append(f"确认页面实际文案包含：{value}")
    advice.append("结合最后截图、DOM 快照和录屏复现失败现场。")
    return advice


def _live_report(
    *,
    passed: bool,
    running: bool,
    total_steps: int,
    current_step: int,
    current_action: str,
    events: list[dict[str, Any]],
    screenshots: list[dict[str, Any]],
    latest_screenshot: str | None,
    error: str | None = None,
    recording_url: str | None = None,
    recording_name: str | None = None,
    recording_error: str | None = None,
    dom_snapshot: str | None = None,
    dom_snapshot_error: str | None = None,
    failure_advice: list[str] | None = None,
) -> dict[str, Any]:
    """Write live UI execution status, events, and screenshots back to the run record."""
    return {
        "passed": passed,
        "running": running,
        "framework": "pytest + playwright + allure",
        "current_step": current_step,
        "total_steps": total_steps,
        "current_action": current_action,
        "events": events,
        "screenshots": screenshots,
        "latest_screenshot": latest_screenshot,
        "error": error,
        "recording_url": recording_url,
        "recording_name": recording_name,
        "recording_error": recording_error,
        "dom_snapshot": dom_snapshot,
        "dom_snapshot_error": dom_snapshot_error,
        "failure_advice": failure_advice or [],
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
    final_report: dict[str, Any] | None = None

    with sync_playwright() as p:
        # Chromium runs headless inside Docker; no Docker socket or host browser is needed.
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox"])
        with tempfile.TemporaryDirectory(prefix="ui-recording-") as video_dir:
            context_kwargs = {"viewport": {"width": 1280, "height": 720}}
            if UI_RECORD_VIDEO:
                context_kwargs["record_video_dir"] = video_dir
                context_kwargs["record_video_size"] = {"width": 1280, "height": 720}
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            try:
                for index, step in enumerate(steps, start=1):
                    # Each low-code step becomes one Playwright action and one Allure step.
                    step_start = time.perf_counter()
                    action = step["action"]
                    target = step.get("target")
                    value = step.get("value")
                    timeout = step.get("timeout_ms") or 5000

                    if run_id:
                        # Write a live snapshot before the step starts so the popup can show progress.
                        update_run(
                            run_id,
                            logs=f"Running UI step {index}/{total_steps}: {action}",
                            report=_live_report(
                                passed=False,
                                running=True,
                                total_steps=total_steps,
                                current_step=index,
                                current_action=action,
                                events=events,
                                screenshots=screenshots,
                                latest_screenshot=latest_screenshot,
                            ),
                        )

                    try:
                        with allure.step(f"{index}. {action}"):
                            if action == "goto":
                                # Navigation targets are re-checked in the worker before Playwright opens them.
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
                            # Capture after every action so the live window has visual feedback.
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
                    except Exception as exc:
                        error_message = str(exc)
                        try:
                            latest_screenshot = _screenshot_data_url(page)
                            screenshots.append({"step": index, "title": f"failed-step-{index}", "image": latest_screenshot})
                        except Exception:
                            pass
                        dom_snapshot, dom_snapshot_error = _failure_dom_snapshot(page)
                        advice = _failure_advice(action, target, value, error_message)
                        events.append({
                            "step": index,
                            "action": action,
                            "target": target,
                            "value": value,
                            "status": "failed",
                            "elapsed_ms": int((time.perf_counter() - step_start) * 1000),
                            "url": page.url,
                            "title": page.title(),
                            "error": error_message,
                            "advice": advice,
                        })
                        final_report = _live_report(
                            passed=False,
                            running=False,
                            total_steps=total_steps,
                            current_step=index,
                            current_action=action,
                            events=events,
                            screenshots=screenshots,
                            latest_screenshot=latest_screenshot,
                            error=error_message,
                            dom_snapshot=dom_snapshot,
                            dom_snapshot_error=dom_snapshot_error,
                            failure_advice=advice,
                        )
                        break

                    if run_id:
                        # Persist completed-step state for the execution record and live window.
                        update_run(
                            run_id,
                            logs=f"Completed UI step {index}/{total_steps}",
                            report=_live_report(
                                passed=False,
                                running=True,
                                total_steps=total_steps,
                                current_step=index,
                                current_action=action,
                                events=events,
                                screenshots=screenshots,
                                latest_screenshot=latest_screenshot,
                            ),
                        )

                    if UI_STEP_VISUAL_DELAY_MS > 0:
                        # A small delay makes the live execution window readable for humans.
                        page.wait_for_timeout(UI_STEP_VISUAL_DELAY_MS)
                if final_report is None:
                    final_report = _live_report(
                        passed=True,
                        running=False,
                        total_steps=total_steps,
                        current_step=total_steps,
                        current_action="done",
                        events=events,
                        screenshots=screenshots,
                        latest_screenshot=latest_screenshot,
                    )
            finally:
                context.close()

            recording_url, recording_name, recording_error = _recording_data_url(page)
            final_report["recording_url"] = recording_url
            final_report["recording_name"] = recording_name
            final_report["recording_error"] = recording_error
            if run_id and not final_report["passed"]:
                update_run(run_id, logs=f"Failed UI step {final_report['current_step']}/{total_steps}: {final_report['current_action']}", error=final_report.get("error"), report=final_report)
        browser.close()

    return final_report
