"""Single-concurrency, safe-action Playwright runner for Emote web preview."""

import os
import json
import shutil
import time
import hashlib
import random
from datetime import datetime
from pathlib import Path
from queue import Queue
from threading import Thread
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from playwright.sync_api import sync_playwright

app = FastAPI(title="cling UI Runner", docs_url=None, redoc_url=None)
TOKEN = os.environ.get("UI_RUNNER_TOKEN", "")
CALLBACK = os.environ.get("UI_RUNNER_CALLBACK", "http://backend:8000/api/v1/ui-automation/internal/runs")
DATA_ROOT = Path(os.environ.get("UI_AUTOMATION_DATA_DIR", "/data")).resolve()
AUTH_STATE_ROOT = DATA_ROOT / "auth-sessions"
AUTH_STATE_TTL_SECONDS = 24 * 60 * 60
tasks: Queue[dict] = Queue()


def _prepare_auth_state_root():
    AUTH_STATE_ROOT.mkdir(parents=True, exist_ok=True)
    try: AUTH_STATE_ROOT.chmod(0o700)
    except OSError: pass


def auth_state_path(base_url: str, username: str) -> Path | None:
    if not username:
        return None
    digest = hashlib.sha256(f"{base_url.rstrip('/')}|{username}".encode("utf-8")).hexdigest()
    return AUTH_STATE_ROOT / f"{digest}.json"


def reusable_auth_state(path: Path | None) -> Path | None:
    if not path or not path.is_file():
        return None
    try:
        if time.time() - path.stat().st_mtime >= AUTH_STATE_TTL_SECONDS:
            path.unlink(missing_ok=True)
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload.get("origins"), list):
            raise ValueError("invalid storage state")
        return path
    except Exception:
        path.unlink(missing_ok=True)
        return None


def save_auth_state(context, path: Path | None):
    if not path:
        return
    context.storage_state(path=str(path))
    try: path.chmod(0o600)
    except OSError: pass


_prepare_auth_state_root()


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
    for key, variable in variables.items():
        if not isinstance(variable, (dict, list, set, tuple)):
            text = text.replace("${" + key + "}", str(variable))
    return text


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


def diagnostic_url(url: str) -> str:
    """Keep the exact test URL so a copied command can be replayed as-is."""
    return url


def safe_curl(request) -> str:
    """Build a reproducible cURL command from the test request payload."""
    endpoint = diagnostic_url(request.url)
    command = f"curl -X {request.method} '{endpoint}'"
    content_type = request.headers.get("content-type", "")
    if content_type:
        command += f" -H 'Content-Type: {content_type}'"
    payload = request.post_data
    if payload:
        try:
            payload = json.dumps(json.loads(payload), ensure_ascii=False, separators=(",", ":"))
        except Exception:
            payload = request.post_data
        command += f" --data '{payload}'"
    return command


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


def locator(page, step, variables):
    kind = step.get("locator_type", "text")
    value = resolve_value(step.get("locator", ""), variables)
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
    elif kind == "post_action":
        content = page.get_by_text(value, exact=True).first
        card = content.locator("xpath=ancestor::div[.//button//*[contains(@class,'lucide-heart')]][1]")
        post_action = step.get("role", "")
        if post_action == "like": target = card.locator("button:has(.lucide-heart)")
        elif post_action == "liked": target = card.locator("button:has(.lucide-heart) .lucide-heart.fill-pink-500")
        elif post_action == "comment": target = card.locator("button:has(.lucide-message-circle)")
        elif post_action == "comment_input": target = card.get_by_placeholder("添加评论...")
        elif post_action == "favorite": target = card.locator("button:has(.lucide-bookmark)")
        elif post_action == "favorited": target = card.locator("button:has(.lucide-bookmark) .lucide-bookmark.fill-amber-400")
        elif post_action == "private": target = card.get_by_text("私密", exact=True)
        else: target = card
    elif kind == "post_tags":
        composer = page.get_by_placeholder(value, exact=True)
        target = composer.locator("xpath=following::div[contains(@class,'flex-wrap')][1]/button")
    elif kind == "chat_friend_action":
        name = page.get_by_text(value, exact=True).first
        card = name.locator("xpath=ancestor::div[.//button//*[contains(@class,'lucide-message-circle')]][1]")
        target = card.locator("button:has(.lucide-message-circle)")
    elif kind == "avatar_option":
        target = page.locator("div.flex.flex-wrap.justify-center.gap-2 button")
    elif kind == "garden_water":
        target = page.locator("button.absolute.bottom-4.right-4:has(.lucide-droplets)")
    elif kind == "daily_task_button":
        title = page.get_by_role("heading", name=value, exact=False).first
        card = title.locator("xpath=ancestor::div[./button][1]")
        target = card.locator(":scope > button")
    else: target = page.get_by_text(value, exact=exact)
    match = step.get("match")
    if match == "first": return target.first
    if match == "last": return target.last
    if match == "nth": return target.nth(int(step.get("index", 0)))
    return target


def artifact(path: Path, run_dir: Path, kind: str, content_type: str):
    return {"kind": kind, "name": path.name, "stored_name": str(path.relative_to(DATA_ROOT)).replace("\\", "/"),
            "content_type": content_type, "size_bytes": path.stat().st_size if path.exists() else 0}


def dismiss_interrupting_guides(page):
    """Close a delayed feature-guide overlay before a business interaction."""
    for label in ("跳过引导", "开始体验"):
        try:
            button = page.get_by_role("button", name=label, exact=True)
            if button.count() and button.first.is_visible():
                button.first.click(timeout=3000)
                page.wait_for_timeout(300)
        except Exception:
            pass


def execute_step(page, contexts, step, variables, base_url):
    action = step["action"]
    value = resolve_value(step.get("value") if "value" in step else step.get("variable") and "${" + step["variable"] + "}", variables)
    target = locator(page, step, variables) if action not in {"goto", "wait", "screenshot", "switch_account", "assert_url", "assert_watering_result"} else None
    if action in {"click", "click_random", "fill", "append", "press", "select", "check", "uncheck"} \
            and step.get("flow") != "feature_guide":
        dismiss_interrupting_guides(page)
    if action == "goto":
        # Test paths are relative to the configured preview base. A leading slash
        # must not escape /emote-preview/ and accidentally open the cling home page.
        target_url = urljoin(base_url.rstrip("/") + "/", (value or "/").lstrip("/"))
        page.goto(target_url, wait_until="domcontentloaded")
        if variables.get("_auth_reused"):
            try:
                page.wait_for_function("() => window.location.href.includes('#/home')", timeout=5000)
            except Exception:
                variables["_auth_reused"] = False
                state_path = variables.get("_auth_state_path")
                if isinstance(state_path, Path): state_path.unlink(missing_ok=True)
    elif action == "click":
        if step.get("force"): target.dispatch_event("click")
        else: target.click()
    elif action == "click_random":
        visible = [target.nth(index) for index in range(target.count()) if target.nth(index).is_visible()]
        if not visible:
            raise AssertionError("没有找到可随机选择的选项")
        random.SystemRandom().choice(visible).click()
    elif action == "fill": target.fill(value)
    elif action == "append":
        current = target.input_value()
        separator = " " if current.strip() else ""
        suffix = f"{separator}{value}"
        max_length = target.get_attribute("maxlength")
        if max_length and max_length.isdigit():
            limit = int(max_length)
            current = current[:max(0, limit - len(suffix))]
        target.fill(f"{current}{suffix}")
    elif action == "select": target.select_option(value)
    elif action == "check": target.check()
    elif action == "uncheck": target.uncheck()
    elif action == "press": target.press(value)
    elif action == "wait": page.wait_for_timeout(min(int(value or 1000), 10000))
    elif action == "detect_visible":
        try:
            target.wait_for(state="visible", timeout=3000)
            variables[f"condition.{step.get('condition', '')}"] = True
        except Exception:
            variables[f"condition.{step.get('condition', '')}"] = False
    elif action == "detect_enabled":
        try:
            target.wait_for(state="visible", timeout=5000)
            variables[f"condition.{step.get('condition', '')}"] = target.is_enabled()
        except Exception:
            variables[f"condition.{step.get('condition', '')}"] = False
    elif action == "assert_watering_result":
        success = page.locator("button.absolute.bottom-4.right-4.bg-emerald-500")
        cooldown = page.get_by_text("24小时内您已对该用户浇过水", exact=False)
        result_deadline = time.monotonic() + 6
        while time.monotonic() < result_deadline:
            if (success.count() and success.first.is_visible()) or (cooldown.count() and cooldown.first.is_visible()):
                break
            page.wait_for_timeout(150)
        else:
            raise AssertionError("页面未显示浇水成功或今日已浇水状态")
    elif action == "validate_onboarding_page":
        heading = page.get_by_role("heading", name=step.get("title", ""), exact=True)
        description = page.get_by_text(step.get("description", ""), exact=True)
        icon = page.get_by_text(step.get("icon", ""), exact=True)
        button = page.get_by_role("button", name=step.get("locator", ""), exact=True)
        for element in (heading, description, icon, button):
            element.wait_for(state="visible")
        box, viewport = icon.bounding_box(), page.viewport_size
        assert box and viewport and box["x"] >= 0 and box["y"] >= 0 \
            and box["x"] + box["width"] <= viewport["width"] \
            and box["y"] + box["height"] <= viewport["height"], "引导图标没有完整显示在当前屏幕内"
        page.wait_for_timeout(500)
        button.dispatch_event("click")
    elif action == "assert_visible": target.wait_for(state="visible")
    elif action == "assert_hidden": target.wait_for(state="hidden")
    elif action == "assert_in_viewport":
        target.wait_for(state="visible")
        box, viewport = target.bounding_box(), page.viewport_size
        assert box and viewport and box["x"] >= 0 and box["y"] >= 0 \
            and box["x"] + box["width"] <= viewport["width"] \
            and box["y"] + box["height"] <= viewport["height"], "元素没有完整显示在当前屏幕内"
    elif action == "assert_text": target.wait_for(state="visible"); assert value in target.inner_text()
    elif action == "assert_url":
        # Hash-router changes do not emit a new page load. Waiting for navigation
        # can therefore time out even after the browser is already on #/home.
        page.wait_for_function("expected => window.location.href.includes(expected)", arg=value)
        if value == "#/home" and not variables.get("_auth_reused"):
            save_auth_state(page.context, variables.get("_auth_state_path"))
    elif action == "assert_count": assert target.count() == int(value)
    elif action == "switch_account":
        account = value if value in contexts else "account_a"
        variables.setdefault("_used_accounts", set()).add(account)
        return contexts[account].pages[0]
    return page


def describe_step(case, index, step, variables):
    """Use beginner-friendly Chinese labels in the live window and reports."""
    action = step.get("action", "")
    target = resolve_value(step.get("locator", ""), variables)
    value = resolve_value(step.get("value", ""), variables)
    if action == "goto": detail = "跳转登录页" if value in {"", "/"} else f"跳转页面：{value}"
    elif action == "assert_visible": detail = f"断言元素出现：{target}"
    elif action == "assert_hidden": detail = f"断言引导已关闭：{target}"
    elif action == "assert_in_viewport": detail = f"检查图标完整显示：{target}"
    elif action == "assert_text": detail = f"断言文本正确：{target}"
    elif action == "assert_url": detail = "断言页面地址正确"
    elif action == "detect_visible": detail = "检测是否显示新手引导"
    elif action == "detect_enabled": detail = f"检测任务是否待完成：{target}"
    elif action == "assert_watering_result": detail = "确认浇水成功或今日已完成"
    elif action == "validate_onboarding_page": detail = f"确认引导页并继续：{step.get('title', '')}"
    elif action == "fill" and "password" in target: detail = "填写登录密码"
    elif action == "fill" and ("tel" in target or "手机号" in target): detail = "填写手机号/账号"
    elif action == "fill": detail = f"填写内容：{target or '输入框'}"
    elif action == "append": detail = f"追加时间戳：{target or '输入框'}"
    elif action == "click_random": detail = f"随机选择：{target or '选项'}"
    elif action == "click": detail = f"点击：{target or '目标按钮'}"
    elif action == "screenshot": detail = "保存当前页面截图"
    elif action == "switch_account": detail = "切换测试账号"
    elif action == "wait": detail = "等待页面响应"
    else: detail = action
    return f"{case['name']} · 第 {index} 步 · {detail}"


def prepare_authenticated_state(browser, base_url, viewport, credentials, state_path):
    """Authenticate once per run and persist the resulting one-day browser token."""
    reusable = reusable_auth_state(state_path)
    options = {"viewport": viewport}
    if reusable:
        options["storage_state"] = str(reusable)
    context = browser.new_context(**options)
    page = context.new_page()
    try:
        page.goto(base_url.rstrip("/") + "/", wait_until="domcontentloaded")
        if reusable:
            try:
                page.wait_for_function("() => window.location.href.includes('#/home')", timeout=7000)
                # Wait through the asynchronous refresh-token check. A stale state
                # can briefly render #/home before the app redirects to #/login.
                page.locator("button[data-feature-guide='create-post']:visible").wait_for(
                    state="visible", timeout=12000
                )
                page.wait_for_timeout(5000)
                assert "#/home" in page.url
                save_auth_state(context, state_path)
                return state_path
            except Exception:
                context.close()
                state_path.unlink(missing_ok=True)
                context = browser.new_context(viewport=viewport)
                page = context.new_page()
                page.goto(base_url.rstrip("/") + "/", wait_until="domcontentloaded")

        page.get_by_role("heading", name="欢迎来到 Emote").wait_for(state="visible")
        page.get_by_role("button", name="同意并继续").click()
        page.get_by_role("button", name="登录", exact=True).click()
        page.locator("div[style*='pointer-events: auto'] input[type='tel'][placeholder='手机号']").fill(str(credentials.get("username", "")))
        page.locator("div[style*='pointer-events: auto'] input[type='password']").fill(str(credentials.get("password", "")))
        page.get_by_role("button", name="进入心灵花园", exact=True).click()
        page.wait_for_function("() => window.location.href.includes('#/home')", timeout=30000)

        for _ in range(5):
            advanced = False
            for label in ("继续", "开启旅程"):
                button = page.get_by_role("button", name=label, exact=True)
                if button.count() and button.first.is_visible():
                    button.first.click()
                    page.wait_for_timeout(400)
                    advanced = True
                    break
            if not advanced:
                break
        for label in ("跳过引导", "开始体验"):
            button = page.get_by_role("button", name=label, exact=True)
            if button.count() and button.first.is_visible():
                button.first.click()
                page.wait_for_timeout(400)
        page.locator("button[data-feature-guide='create-post']:visible").wait_for(
            state="visible", timeout=12000
        )
        page.wait_for_timeout(5000)
        assert "#/home" in page.url
        save_auth_state(context, state_path)
        return state_path
    finally:
        try: context.close()
        except Exception: pass


def run_task(task):
    run_id, run_dir = task["run_id"], DATA_ROOT / f"run-{task['run_id']}"
    run_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    variables = {
        "run_id": run_id,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "compact_timestamp": now.strftime("%m%d%H%M%S"),
    }
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

    def remember_request(request):
        if request.resource_type not in {"xhr", "fetch"}: return
        network_issues.append({
            "type": "pending", "method": request.method, "url": diagnostic_url(request.url),
            "curl": safe_curl(request),
        })

    def remember_response(response):
        request = response.request
        if request.resource_type not in {"xhr", "fetch"}: return
        endpoint = diagnostic_url(request.url)
        # A successful non-auth request is noise. Keep failed requests, pending
        # requests and authentication traffic so login errors are reproducible.
        is_auth = any(part in endpoint.lower() for part in ("/login", "/register", "/auth/", "/otp", "/verify"))
        for index in range(len(network_issues) - 1, -1, -1):
            item = network_issues[index]
            if item.get("type") == "pending" and item.get("method") == request.method and item.get("url") == endpoint:
                if response.status >= 400 or is_auth:
                    item.update({"type": "http", "status": response.status})
                else:
                    network_issues.pop(index)
                return
        if response.status >= 400 or is_auth:
            network_issues.append({"type": "http", "method": request.method, "status": response.status,
                                   "url": endpoint, "curl": safe_curl(request)})

    def remember_failed_request(request):
        if request.resource_type not in {"xhr", "fetch"}: return
        endpoint = diagnostic_url(request.url)
        detail = (request.failure or "网络请求失败")[:300]
        for item in reversed(network_issues):
            if item.get("type") == "pending" and item.get("method") == request.method and item.get("url") == endpoint:
                item.update({"type": "network", "error": detail})
                return
        network_issues.append({"type": "network", "method": request.method, "url": endpoint,
                               "error": detail, "curl": safe_curl(request)})

    def finalize_case(case_id, case_dir):
        """Close one case context so its video is finalized independently."""
        case_artifacts = []
        used_accounts = variables.get("_used_accounts", {"account_a"})
        for account_name, context in list(contexts.items()):
            try:
                videos = [item.video for item in context.pages if item.video]
                context.close()
                for number, video in enumerate(videos, 1):
                    source = Path(video.path())
                    if account_name not in used_accounts:
                        source.unlink(missing_ok=True)
                        continue
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
            account_a = task.get("credentials", {}).get("account_a", {})
            state_path = auth_state_path(task["base_url"], str(account_a.get("username", "")))
            inline_auth = len(task["cases"]) == 1 and any(
                step.get("flow") == "authentication"
                for step in task["cases"][0].get("steps", [])
            )
            if not inline_auth:
                prepare_authenticated_state(browser, task["base_url"], viewport, account_a, state_path)
            for case in task["cases"]:
                current_case = case
                variables["_used_accounts"] = {"account_a"}
                case_id = case["id"]
                case_dir = run_dir / f"case-{case_id}"
                case_dir.mkdir(parents=True, exist_ok=True)
                reusable_state = reusable_auth_state(state_path)
                variables["_auth_state_path"] = state_path
                variables["_auth_reused"] = bool(reusable_state)
                for name in ("account_a", "account_b"):
                    context_options = {"viewport": viewport, "record_video_dir": str(case_dir / "raw-video"), "record_video_size": viewport}
                    if name == "account_a" and reusable_state:
                        context_options["storage_state"] = str(reusable_state)
                    contexts[name] = browser.new_context(**context_options)
                    new_page = contexts[name].new_page()
                    new_page.on("request", remember_request)
                    new_page.on("response", remember_response)
                    new_page.on("requestfailed", remember_failed_request)
                page = contexts["account_a"].pages[0]
                has_key_screenshot = False
                for index, step in enumerate(case.get("steps", []), 1):
                    current_step, current_step_index = step, index
                    if time.monotonic() > deadline:
                        raise TimeoutError("达到最长执行时间 20 分钟，任务已停止")
                    label = describe_step(case, index, step, variables)
                    if step.get("flow") == "authentication" and variables.get("_auth_reused"):
                        timeline.append({"name": label, "case_id": case_id, "case_name": case["name"], "step_index": index,
                                         "action": step["action"], "status": "skipped", "duration_ms": 0,
                                         "note": "已复用24小时内登录Token"})
                        completed += 1
                        callback(run_id, status="running", current_step=f"{case['name']} · 已复用今日登录Token",
                                 progress=int(completed / total * 100), result_summary={"timeline": timeline, "viewport": viewport})
                        continue
                    condition = step.get("when")
                    if condition and not variables.get(f"condition.{condition}", False):
                        timeline.append({"name": label, "case_id": case_id, "case_name": case["name"], "step_index": index,
                                         "action": step["action"], "status": "skipped", "duration_ms": 0})
                        completed += 1
                        callback(run_id, status="running", current_step=f"{label}（本次无引导，已跳过）",
                                 progress=int(completed / total * 100), result_summary={"timeline": timeline, "viewport": viewport})
                        continue
                    step_started = time.monotonic()
                    page = execute_step(page, contexts, step, variables, task["base_url"])
                    timeline.append({"name": label, "case_id": case_id, "case_name": case["name"], "step_index": index,
                                     "action": step["action"], "status": "passed", "duration_ms": int((time.monotonic() - step_started) * 1000)})
                    completed += 1
                    is_key_screenshot = step["action"] == "screenshot"
                    has_key_screenshot = has_key_screenshot or is_key_screenshot
                    live = case_dir / (f"case-{case_id}-key-step-{index:02d}.png" if is_key_screenshot else f"case-{case_id}-live.png")
                    page.screenshot(path=str(live), full_page=False)
                    callback(run_id, status="running", current_step=label, progress=int(completed / total * 100),
                             result_summary={"timeline": timeline, "viewport": viewport},
                             artifacts=[artifact(live, run_dir, "screenshot", "image/png")])
                    # Keep the live preview readable without filling evidence storage
                    # with one permanent screenshot for every action.
                    page.wait_for_timeout(700)
                if not has_key_screenshot:
                    final = case_dir / f"case-{case_id}-final.png"
                    page.screenshot(path=str(final), full_page=False)
                    artifacts.append(artifact(final, run_dir, "screenshot", "image/png"))
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
        # Keep only the newest relevant calls. Pending entries indicate requests
        # that were still waiting when Playwright timed out.
        failure["network_issues"] = [item for item in network_issues if item.get("type") != "pending" or item.get("curl")][-10:]
        case_id = current_case.get("id", "startup") if current_case else "startup"
        case_dir = run_dir / f"case-{case_id}"
        case_dir.mkdir(parents=True, exist_ok=True)
        fail = case_dir / f"case-{case_id}-failure-step-{current_step_index or 0:02d}.png"
        try:
            page.screenshot(path=str(fail), full_page=False); artifacts.append(artifact(fail, run_dir, "screenshot", "image/png"))
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
            if target == AUTH_STATE_ROOT: continue
            if target.is_dir(): shutil.rmtree(target)
            else: target.unlink(missing_ok=True)
            removed += 1
    return {"status": "ok", "removed": removed}
