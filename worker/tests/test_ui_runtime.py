"""Tests for UI automation runtime report shaping."""

import os
import sys
import types
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "mysql+pymysql://automation:password@127.0.0.1:3306/automation_platform")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class NoopStep:
    """No-op context manager used to replace allure.step in unit tests."""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

allure_stub = types.SimpleNamespace(
    attach=lambda *_args, **_kwargs: None,
    step=lambda *_args, **_kwargs: NoopStep(),
    attachment_type=types.SimpleNamespace(JPG="jpg"),
)
playwright_stub = types.ModuleType("playwright")
sync_api_stub = types.ModuleType("playwright.sync_api")
db_stub = types.ModuleType("app.infrastructure.db")
sync_api_stub.sync_playwright = lambda: None
db_stub.update_run = lambda *_args, **_kwargs: None
sys.modules.setdefault("allure", allure_stub)
sys.modules.setdefault("playwright", playwright_stub)
sys.modules.setdefault("playwright.sync_api", sync_api_stub)
sys.modules.setdefault("app.infrastructure.db", db_stub)

from app.modules.ui_automation import runtime  # noqa: E402


class FakePage:
    """Minimal Playwright page double that fails on click."""

    def __init__(self, video_path):
        self.url = "https://example.com/login"
        self.video = types.SimpleNamespace(path=lambda: str(video_path))

    def screenshot(self, **_kwargs):
        return b"fake-image"

    def click(self, *_args, **_kwargs):
        raise RuntimeError("selector not found: #missing")

    def title(self):
        return "Example Login"


class FakeBrowser:
    """Minimal browser double that returns the fake page."""

    def new_context(self, **kwargs):
        return FakeContext(Path(kwargs["record_video_dir"]) / "ui-test.webm")

    def close(self):
        return None


class FakeContext:
    """Minimal context double that writes a fake Playwright video on close."""

    def __init__(self, video_path):
        self.video_path = video_path
        self.page = FakePage(video_path)

    def new_page(self):
        return self.page

    def close(self):
        self.video_path.write_bytes(b"fake-webm-video")
        return None


class FakeChromium:
    """Minimal chromium double that returns the fake browser."""

    def launch(self, **_kwargs):
        return FakeBrowser()


class FakePlaywright:
    """Context manager matching sync_playwright for runtime tests."""

    chromium = FakeChromium()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_execute_ui_case_returns_structured_failed_step(monkeypatch):
    """Failed UI steps should still return a report that the live window can render."""
    updates = []

    monkeypatch.setattr(runtime, "sync_playwright", lambda: FakePlaywright())
    monkeypatch.setattr(runtime.allure, "attach", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runtime, "update_run", lambda *args, **kwargs: updates.append((args, kwargs)))

    report = runtime.execute_ui_case(
        {"steps": [{"action": "click", "target": "#missing", "timeout_ms": 50}]},
        run_id=123,
    )

    assert report["passed"] is False
    assert report["running"] is False
    assert report["current_step"] == 1
    assert report["events"][0]["status"] == "failed"
    assert report["events"][0]["target"] == "#missing"
    assert "selector not found" in report["events"][0]["error"]
    assert report["latest_screenshot"].startswith("data:image/jpeg;base64,")
    assert report["recording_url"].startswith("data:video/webm;base64,")
    assert report["recording_name"] == "ui-test.webm"
    assert updates[-1][1]["error"] == report["error"]
