import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest


def test_final_failure_keeps_original_result_and_does_not_create_empty_video(monkeypatch, tmp_path):
    """A failed final case must not open an unused recovery page/video."""
    pytest.importorskip('playwright.sync_api', reason='Requires the UI runner test environment')
    runner = Path(__file__).resolve().parents[2] / 'deploy/ui-runner'
    monkeypatch.syspath_prepend(str(runner))
    spec = importlib.util.spec_from_file_location('tested_studio_engine', runner / 'studio_engine.py')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    events, contexts = [], []
    source_video = tmp_path / 'recording.webm'
    source_video.write_bytes(b'video')

    class Page:
        video = SimpleNamespace(path=lambda: str(source_video))

        def on(self, *args):
            pass

        def screenshot(self, path, **kwargs):
            Path(path).write_bytes(b'image')

        def is_closed(self):
            return False

    class Context:
        def set_default_timeout(self, value):
            pass

        def set_default_navigation_timeout(self, value):
            pass

        def new_page(self):
            return Page()

        def close(self):
            pass

    class Browser:
        def new_context(self, **kwargs):
            result = Context()
            contexts.append(result)
            return result

        def close(self):
            pass

    class Playwright:
        chromium = SimpleNamespace(launch=lambda **kwargs: Browser())

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Pages:
        checks = []

        def __init__(self, *args):
            pass

        def perform(self, step):
            raise RuntimeError('upstream unavailable')

    monkeypatch.setattr(engine, 'sync_playwright', Playwright)
    monkeypatch.setattr(engine, 'EmotePages', Pages)
    engine.execute_studio({'run_id': 1, 'base_url': 'https://example.org/',
        'cases': [{'id': 1, 'name': '登录', 'steps': [{'action': 'login'}]}]},
        lambda run_id, **event: events.append(event), tmp_path)
    assert len(contexts) == 1
    final = events[-1]
    assert final['status'] == 'failed'
    assert final['result_summary']['case_results'][0]['reason'] == 'upstream unavailable'
    assert final['result_summary']['report']['failed'] == 1
    assert {a['kind'] for a in final['artifacts']} == {'screenshot', 'video'}
    assert all(a['name'] != 'run-video.webm' for a in final['artifacts'])
