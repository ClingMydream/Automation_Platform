"""Single-concurrency, safe-action Playwright runner for Emote web preview."""

import os
import time
from pathlib import Path
from queue import Queue
from threading import Thread
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from playwright.sync_api import sync_playwright

app = FastAPI(title="cling UI Runner", docs_url=None, redoc_url=None)
TOKEN = os.environ.get("UI_RUNNER_TOKEN", "")
CALLBACK = os.environ.get("UI_RUNNER_CALLBACK", "http://backend:8000/api/v1/ui-automation/internal/runs")
DATA_ROOT = Path(os.environ.get("UI_AUTOMATION_DATA_DIR", "/data")).resolve()
tasks: Queue[dict] = Queue()


class ExecuteInput(BaseModel):
    run_id: int
    base_url: str
    viewport: str = "mobile"
    cases: list[dict]
    credentials: dict = Field(default_factory=dict)


def callback(run_id: int, **payload):
    httpx.put(f"{CALLBACK}/{run_id}", json=payload, headers={"X-Runner-Token": TOKEN}, timeout=15).raise_for_status()


def resolve_value(value, variables):
    if value is None: return ""
    text = str(value)
    if text.startswith("${") and text.endswith("}"):
        return str(variables.get(text[2:-1], ""))
    return text.replace("${run_id}", str(variables["run_id"]))


def redact_error(error, credentials):
    """Remove every runtime secret before an exception leaves the runner process."""
    text = str(error)
    for values in credentials.values():
        if not isinstance(values, dict):
            continue
        for value in values.values():
            secret = str(value or "")
            if secret:
                text = text.replace(secret, "******")
    return text[:4000]


def locator(page, step):
    kind, value = step.get("locator_type", "text"), step.get("locator", "")
    if kind == "testid": return page.get_by_test_id(value)
    if kind == "role": return page.get_by_role(step.get("role", "button"), name=value)
    if kind == "label": return page.get_by_label(value)
    if kind == "css": return page.locator(value)
    return page.get_by_text(value, exact=bool(step.get("exact")))


def artifact(path: Path, run_dir: Path, kind: str, content_type: str):
    return {"kind": kind, "name": path.name, "stored_name": str(path.relative_to(DATA_ROOT)).replace("\\", "/"),
            "content_type": content_type, "size_bytes": path.stat().st_size if path.exists() else 0}


def execute_step(page, contexts, step, variables, base_url):
    action = step["action"]
    value = resolve_value(step.get("value") if "value" in step else step.get("variable") and "${" + step["variable"] + "}", variables)
    target = locator(page, step) if action not in {"goto", "wait", "screenshot", "switch_account", "assert_url"} else None
    if action == "goto": page.goto(urljoin(base_url, value or "/"), wait_until="domcontentloaded")
    elif action == "click": target.click()
    elif action == "fill": target.fill(value)
    elif action == "select": target.select_option(value)
    elif action == "check": target.check()
    elif action == "uncheck": target.uncheck()
    elif action == "press": target.press(value)
    elif action == "wait": page.wait_for_timeout(min(int(value or 1000), 10000))
    elif action == "assert_visible": target.wait_for(state="visible")
    elif action == "assert_text": target.wait_for(state="visible"); assert value in target.inner_text()
    elif action == "assert_url": page.wait_for_url(f"**{value}**")
    elif action == "assert_count": assert target.count() == int(value)
    elif action == "switch_account": return contexts[value if value in contexts else "account_a"].pages[0]
    return page


def run_task(task):
    run_id, run_dir = task["run_id"], DATA_ROOT / f"run-{task['run_id']}"
    run_dir.mkdir(parents=True, exist_ok=True)
    variables = {"run_id": run_id}
    for group, values in task.get("credentials", {}).items():
        if isinstance(values, dict):
            for key, value in values.items(): variables[f"{group}.{key}"] = value
    artifacts = []
    total = sum(len(case.get("steps", [])) for case in task["cases"]) or 1
    completed = 0
    timeline = []
    deadline = time.monotonic() + 20 * 60
    contexts = {}
    browser = None
    try:
        callback(run_id, status="running", current_step="启动 Chromium", progress=0)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            viewport = {"width": 390, "height": 844} if task["viewport"] == "mobile" else {"width": 1440, "height": 900}
            for name in ("account_a", "account_b"):
                contexts[name] = browser.new_context(viewport=viewport, record_video_dir=str(run_dir / "video"), record_video_size=viewport)
                contexts[name].tracing.start(screenshots=True, snapshots=True, sources=False)
                contexts[name].new_page()
            page = contexts["account_a"].pages[0]
            for case in task["cases"]:
                for index, step in enumerate(case.get("steps", []), 1):
                    if time.monotonic() > deadline:
                        raise TimeoutError("达到最长执行时间 20 分钟，任务已停止")
                    label = f"{case['name']} · 第 {index} 步 · {step['action']}"
                    step_started = time.monotonic()
                    page = execute_step(page, contexts, step, variables, task["base_url"])
                    timeline.append({"name": label, "status": "passed", "duration_ms": int((time.monotonic() - step_started) * 1000)})
                    completed += 1
                    live = run_dir / "latest.png"
                    page.screenshot(path=str(live), full_page=False)
                    callback(run_id, status="running", current_step=label, progress=int(completed / total * 100),
                             result_summary={"timeline": timeline}, artifacts=[artifact(live, run_dir, "screenshot", "image/png")])
            for name, context in contexts.items():
                trace = run_dir / f"trace-{name}.zip"
                context.tracing.stop(path=str(trace)); artifacts.append(artifact(trace, run_dir, "trace", "application/zip"))
                videos = [p.video for p in context.pages if p.video]
                context.close()
                for number, video in enumerate(videos, 1):
                    source = Path(video.path()); destination = run_dir / f"video-{name}-{number}.webm"
                    source.replace(destination); artifacts.append(artifact(destination, run_dir, "video", "video/webm"))
            browser.close()
        if (run_dir / "latest.png").exists(): artifacts.append(artifact(run_dir / "latest.png", run_dir, "screenshot", "image/png"))
        callback(run_id, status="passed", current_step="执行完成", progress=100,
                 result_summary={"passed": len(task["cases"]), "failed": 0, "timeline": timeline}, artifacts=artifacts)
    except Exception as exc:
        error = redact_error(exc, task.get("credentials", {}))
        fail = run_dir / "failure.png"
        try:
            page.screenshot(path=str(fail), full_page=True); artifacts.append(artifact(fail, run_dir, "screenshot", "image/png"))
        except Exception: pass
        # Close contexts on failures too; Playwright only finalizes WebM files when the
        # recording context closes, so failed executions still leave useful evidence.
        for name, context in contexts.items():
            try:
                trace = run_dir / f"trace-{name}.zip"
                context.tracing.stop(path=str(trace)); artifacts.append(artifact(trace, run_dir, "trace", "application/zip"))
                videos = [p.video for p in context.pages if p.video]
                context.close()
                for number, video in enumerate(videos, 1):
                    source = Path(video.path()); destination = run_dir / f"video-{name}-{number}.webm"
                    source.replace(destination); artifacts.append(artifact(destination, run_dir, "video", "video/webm"))
            except Exception:
                pass
        try:
            if browser: browser.close()
        except Exception:
            pass
        timeline.append({"name": "执行失败", "status": "failed", "duration_ms": 0})
        callback(run_id, status="failed", current_step="执行失败", progress=int(completed / total * 100),
                 result_summary={"passed": 0, "failed": 1, "timeline": timeline}, error_message=error, artifacts=artifacts)


def worker():
    while True:
        task = tasks.get()
        try: run_task(task)
        finally: tasks.task_done()


Thread(target=worker, daemon=True).start()


@app.get("/health")
def health(): return {"status": "ok", "queue": tasks.qsize()}


@app.post("/execute", status_code=202)
def execute(payload: ExecuteInput, x_runner_token: str | None = Header(None)):
    if not TOKEN or x_runner_token != TOKEN: raise HTTPException(403, "Runner token invalid")
    tasks.put(payload.model_dump())
    return {"status": "queued", "position": tasks.qsize()}
