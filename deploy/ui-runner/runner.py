"""Single-concurrency, safe-action Playwright runner for Emote web preview."""

import os
import shutil
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


def friendly_failure(error, case, step, step_index, credentials):
    """Turn Playwright internals into an actionable Chinese failure report."""
    technical = redact_error(error, credentials)
    lowered = technical.lower()
    if (step or {}).get("action") == "assert_url" and (step or {}).get("value") == "#/home":
        reason = "登录后没有进入首页"
        suggestion = "检查账号密码是否正确、登录接口是否成功，以及页面是否仍停留在登录页；请结合失败截图确认页面提示。"
    elif "timeout" in lowered:
        reason = "等待页面或元素超时"
        suggestion = "确认预览服务可访问，并检查元素名称、定位方式及页面加载速度。"
    elif "strict mode violation" in lowered:
        reason = "定位器匹配到多个元素"
        suggestion = "优先补充 data-testid，或使用更准确的角色、名称和标签定位。"
    elif "net::err" in lowered:
        reason = "目标页面网络访问失败"
        suggestion = "确认 Emote 预览已同步成功，后端测试环境和页面地址可正常访问。"
    elif isinstance(error, AssertionError) or "assert" in lowered:
        reason = "页面实际结果与预期不一致"
        suggestion = "查看失败截图，对照断言文本、数量或地址是否符合当前版本。"
    elif "closed" in lowered or "crash" in lowered:
        reason = "浏览器页面意外关闭或崩溃"
        suggestion = "重新执行；若重复发生，请检查服务器资源和目标页面控制台错误。"
    else:
        reason = "执行步骤发生异常"
        suggestion = "查看失败截图和技术详情，确认步骤参数及当前页面状态。"
    return {
        "case_id": case.get("id") if case else None,
        "case_name": case.get("name", "未知用例") if case else "启动阶段",
        "step_index": step_index,
        "action": (step or {}).get("action", "启动浏览器"),
        "locator_type": (step or {}).get("locator_type", ""),
        "locator": (step or {}).get("locator", ""),
        "reason": reason,
        "suggestion": suggestion,
        "technical_detail": technical,
    }


def visible_auth_feedback(page):
    """Return only known validation messages, never arbitrary page/account text."""
    messages = [
        "请先同意用户协议和隐私政策", "手机号格式不正确", "请输入正确的 11 位手机号",
        "密码至少需要6位", "服务连接失败", "账号或密码错误", "手机号或密码错误",
        "登录失败", "密码错误", "用户不存在", "网络请求失败",
    ]
    found = []
    for message in messages:
        try:
            matches = page.get_by_text(message, exact=False)
            if any(matches.nth(index).is_visible() for index in range(min(matches.count(), 10))): found.append(message)
        except Exception:
            try:
                if message in page.locator("body").inner_text(): found.append(message)
            except Exception:
                pass
    return list(dict.fromkeys(found))


def visible_page_markers(page):
    markers = ["原野", "发布心情", "连接", "我的", "每日任务", "成功", "正在进入花园"]
    visible = []
    for marker in markers:
        try:
            matches = page.get_by_text(marker, exact=False)
            if any(matches.nth(index).is_visible() for index in range(min(matches.count(), 10))): visible.append(marker)
        except Exception:
            pass
    return visible


def locator(page, step):
    kind, value = step.get("locator_type", "text"), step.get("locator", "")
    exact = bool(step.get("exact"))
    if kind == "testid": target = page.get_by_test_id(value)
    elif kind == "role": target = page.get_by_role(step.get("role", "button"), name=value, exact=exact)
    elif kind == "label": target = page.get_by_label(value, exact=exact)
    elif kind == "placeholder": target = page.get_by_placeholder(value, exact=exact)
    elif kind == "alt": target = page.get_by_alt_text(value, exact=exact)
    elif kind == "title": target = page.get_by_title(value, exact=exact)
    elif kind == "id": target = page.locator(f"#{value}")
    elif kind == "xpath": target = page.locator(f"xpath={value}")
    elif kind == "css": target = page.locator(value)
    else: target = page.get_by_text(value, exact=exact)
    match = step.get("match")
    if match == "first": return target.first
    if match == "last": return target.last
    if match == "nth": return target.nth(int(step.get("index", 0)))
    return target


def artifact(path: Path, run_dir: Path, kind: str, content_type: str):
    return {"kind": kind, "name": path.name, "stored_name": str(path.relative_to(DATA_ROOT)).replace("\\", "/"),
            "content_type": content_type, "size_bytes": path.stat().st_size if path.exists() else 0}


def execute_step(page, contexts, step, variables, base_url):
    action = step["action"]
    value = resolve_value(step.get("value") if "value" in step else step.get("variable") and "${" + step["variable"] + "}", variables)
    target = locator(page, step) if action not in {"goto", "wait", "screenshot", "switch_account", "assert_url"} else None
    if action == "goto":
        # Test paths are relative to the configured preview base. A leading slash
        # must not escape /emote-preview/ and accidentally open the cling home page.
        target_url = urljoin(base_url.rstrip("/") + "/", (value or "/").lstrip("/"))
        page.goto(target_url, wait_until="domcontentloaded")
    elif action == "click": target.click()
    elif action == "fill": target.fill(value)
    elif action == "select": target.select_option(value)
    elif action == "check": target.check()
    elif action == "uncheck": target.uncheck()
    elif action == "press": target.press(value)
    elif action == "wait": page.wait_for_timeout(min(int(value or 1000), 10000))
    elif action == "assert_visible": target.wait_for(state="visible")
    elif action == "assert_text": target.wait_for(state="visible"); assert value in target.inner_text()
    elif action == "assert_url":
        # Hash-router changes do not emit a new page load. Waiting for navigation
        # can therefore time out even after the browser is already on #/home.
        page.wait_for_function("expected => window.location.href.includes(expected)", arg=value)
    elif action == "assert_count": assert target.count() == int(value)
    elif action == "switch_account": return contexts[value if value in contexts else "account_a"].pages[0]
    return page


def describe_step(case, index, step):
    """Use beginner-friendly Chinese labels in the live window and reports."""
    action, target, value = step.get("action", ""), step.get("locator", ""), step.get("value", "")
    if action == "goto": detail = "跳转登录页" if value in {"", "/"} else f"跳转页面：{value}"
    elif action == "assert_visible": detail = f"断言元素出现：{target}"
    elif action == "assert_text": detail = f"断言文本正确：{target}"
    elif action == "assert_url": detail = "断言页面地址正确"
    elif action == "fill" and "password" in target: detail = "填写登录密码"
    elif action == "fill" and ("tel" in target or "手机号" in target): detail = "填写手机号/账号"
    elif action == "fill": detail = f"填写内容：{target or '输入框'}"
    elif action == "click": detail = f"点击：{target or '目标按钮'}"
    elif action == "screenshot": detail = "保存当前页面截图"
    elif action == "switch_account": detail = "切换测试账号"
    elif action == "wait": detail = "等待页面响应"
    else: detail = action
    return f"{case['name']} · 第 {index} 步 · {detail}"


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
    network_issues = []
    deadline = time.monotonic() + 20 * 60
    contexts = {}
    browser = None
    current_case = None
    current_step = None
    current_step_index = 0

    def finalize_case(case_id, case_dir):
        """Close one case context so its video and trace are finalized independently."""
        case_artifacts = []
        for account_name, context in list(contexts.items()):
            try:
                trace = case_dir / f"case-{case_id}-trace-{account_name}.zip"
                context.tracing.stop(path=str(trace))
                case_artifacts.append(artifact(trace, run_dir, "trace", "application/zip"))
                videos = [item.video for item in context.pages if item.video]
                context.close()
                for number, video in enumerate(videos, 1):
                    source = Path(video.path())
                    destination = case_dir / f"case-{case_id}-video-{account_name}-{number}.webm"
                    source.replace(destination)
                    case_artifacts.append(artifact(destination, run_dir, "video", "video/webm"))
            except Exception:
                pass
        contexts.clear()
        return case_artifacts
    try:
        callback(run_id, status="running", current_step="启动 Chromium", progress=0)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"),
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            # Pixel-exact mobile viewport requested for the Emote target device.
            viewport = {"width": 390, "height": 844} if task["viewport"] == "mobile" else {"width": 1440, "height": 900}
            for case in task["cases"]:
                current_case = case
                case_id = case["id"]
                case_dir = run_dir / f"case-{case_id}"
                case_dir.mkdir(parents=True, exist_ok=True)
                for name in ("account_a", "account_b"):
                    contexts[name] = browser.new_context(viewport=viewport, record_video_dir=str(case_dir / "raw-video"), record_video_size=viewport)
                    contexts[name].tracing.start(screenshots=True, snapshots=True, sources=False)
                    new_page = contexts[name].new_page()
                    new_page.on("response", lambda response: network_issues.append({
                        "type": "http", "method": response.request.method, "status": response.status,
                        "url": response.url.split("?", 1)[0],
                    }) if response.status >= 400 or response.request.resource_type in {"xhr", "fetch"} else None)
                    new_page.on("requestfailed", lambda request: network_issues.append({
                        "type": "network", "method": request.method,
                        "url": request.url.split("?", 1)[0], "error": (request.failure or "网络请求失败")[:300],
                    }))
                page = contexts["account_a"].pages[0]
                for index, step in enumerate(case.get("steps", []), 1):
                    current_step, current_step_index = step, index
                    if time.monotonic() > deadline:
                        raise TimeoutError("达到最长执行时间 20 分钟，任务已停止")
                    label = describe_step(case, index, step)
                    step_started = time.monotonic()
                    page = execute_step(page, contexts, step, variables, task["base_url"])
                    timeline.append({"name": label, "case_id": case_id, "case_name": case["name"], "step_index": index,
                                     "action": step["action"], "status": "passed", "duration_ms": int((time.monotonic() - step_started) * 1000)})
                    completed += 1
                    live = case_dir / f"case-{case_id}-step-{index:02d}.png"
                    page.screenshot(path=str(live), full_page=False)
                    callback(run_id, status="running", current_step=label, progress=int(completed / total * 100),
                             result_summary={"timeline": timeline, "viewport": viewport},
                             artifacts=[artifact(live, run_dir, "screenshot", "image/png")])
                    # Keep each completed action visible long enough for the live
                    # execution window to poll and show the form-filling process.
                    page.wait_for_timeout(1200)
                artifacts.extend(finalize_case(case_id, case_dir))
                callback(run_id, status="running", current_step=f"{case['name']} · 证据已保存", progress=int(completed / total * 100),
                         result_summary={"timeline": timeline, "viewport": viewport}, artifacts=artifacts)
            browser.close()
        callback(run_id, status="passed", current_step="执行完成", progress=100,
                 result_summary={"passed": len(task["cases"]), "failed": 0, "timeline": timeline, "viewport": viewport}, artifacts=artifacts)
    except Exception as exc:
        failure = friendly_failure(exc, current_case, current_step, current_step_index, task.get("credentials", {}))
        failure["page_feedback"] = visible_auth_feedback(page) if page else []
        failure["page_markers"] = visible_page_markers(page) if page else []
        failure["current_url"] = page.url if page else ""
        failure["network_issues"] = network_issues[-10:]
        case_id = current_case.get("id", "startup") if current_case else "startup"
        case_dir = run_dir / f"case-{case_id}"
        case_dir.mkdir(parents=True, exist_ok=True)
        fail = case_dir / f"case-{case_id}-failure-step-{current_step_index or 0:02d}.png"
        try:
            page.screenshot(path=str(fail), full_page=True); artifacts.append(artifact(fail, run_dir, "screenshot", "image/png"))
        except Exception: pass
        artifacts.extend(finalize_case(case_id, case_dir))
        try:
            if browser: browser.close()
        except Exception:
            pass
        timeline.append({"name": f"{failure['case_name']} · 第 {failure['step_index']} 步失败", "case_id": failure["case_id"],
                         "case_name": failure["case_name"], "step_index": failure["step_index"],
                         "action": failure["action"], "status": "failed", "duration_ms": 0})
        callback(run_id, status="failed", current_step="执行失败", progress=int(completed / total * 100),
                 result_summary={"passed": 0, "failed": 1, "timeline": timeline, "failure": failure,
                                 "viewport": {"width": 390, "height": 844} if task["viewport"] == "mobile" else {"width": 1440, "height": 900}},
                 error_message=f"{failure['reason']}：{failure['suggestion']}", artifacts=artifacts)


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


@app.delete("/cleanup")
def cleanup(x_runner_token: str | None = Header(None)):
    if not TOKEN or x_runner_token != TOKEN: raise HTTPException(403, "Runner token invalid")
    if tasks.unfinished_tasks: raise HTTPException(409, "Runner task is active")
    removed = 0
    if DATA_ROOT.is_dir():
        for child in DATA_ROOT.iterdir():
            target = child.resolve()
            if not target.is_relative_to(DATA_ROOT) or target == DATA_ROOT: continue
            if target.is_dir(): shutil.rmtree(target)
            else: target.unlink(missing_ok=True)
            removed += 1
    return {"status": "ok", "removed": removed}
