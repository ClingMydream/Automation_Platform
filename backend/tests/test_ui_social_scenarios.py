from contextlib import contextmanager
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

pytest.importorskip('playwright.sync_api', reason='Requires the UI runner test environment')
path = Path(__file__).resolve().parents[2] / 'deploy/ui-runner/studio_flows.py'
spec = importlib.util.spec_from_file_location('social_test_flows', path)
flows = importlib.util.module_from_spec(spec); spec.loader.exec_module(flows)


@pytest.mark.parametrize('outcome,expected', [('watered', []), ('cooldown', ['secretary'])])
def test_self_cooldown_selects_official_account(outcome, expected):
    pages = object.__new__(flows.EmotePages)
    calls = []
    pages.go = lambda route: None
    pages.page = SimpleNamespace(locator=lambda selector: SimpleNamespace(first=object()))
    pages.water_button = lambda target, label: outcome
    pages.water_secretary = lambda: calls.append('secretary')
    pages.watering()
    assert calls == expected


def test_dual_post_stays_private_and_retains_both_records():
    pages = object.__new__(flows.EmotePages); pages.checks = []; pages.extra_images = []
    events = []
    pages.home = lambda: None
    pages.post_text = 'A私密时间戳'
    pages.create_post = lambda: events.append('A-private')
    other = SimpleNamespace(home=lambda: None, create_post=lambda: events.append('B-private'),
        post_text='B私密时间戳', page=SimpleNamespace(screenshot=lambda **kw: b'image'))

    @contextmanager
    def peer():
        yield other, 'B', 'B', 'A', 'A'

    pages.test_peer = peer
    pages.dual_post()
    assert events == ['A-private', 'B-private']
    assert any('两条帖子均保留' in x for x in pages.checks)
    assert pages.extra_images[0][0] == 'account-b-post'


@pytest.mark.parametrize('ai_available', [True, False])
def test_mutual_comments_generate_before_publication_and_use_opposite_posts(monkeypatch, ai_available):
    events = []

    def actor(name):
        pages = object.__new__(flows.EmotePages)
        pages.stamp = '2026-11-03 18:00:00';pages.checks = [];pages.extra_images = []
        pages.page = SimpleNamespace(screenshot=lambda **kw: b'image')
        pages.read_daily_task = lambda: name + '的每日任务'
        def publish(text):
            pages.post_id = name + '-post'
            events.append(('post', name, text))
        pages.publish_task_post = publish
        pages.comment_on_test_post = lambda pid, text, comment: events.append(('comment', name, pid, comment))
        pages.open_test_post = lambda pid, text: events.append(('verify', name, pid))
        pages.card = lambda: SimpleNamespace(get_by_text=lambda *args, **kw: object())
        return pages

    a, b = actor('A'), actor('B')
    @contextmanager
    def peer():
        yield b, 'B', 'B', 'A', 'A'
    a.test_peer = peer
    response = Mock(status_code=200 if ai_available else 503)
    response.json.return_value = {'post_a': 'A的任务帖', 'post_b': 'B的任务帖', 'comment_a_to_b': '回应B任务', 'comment_b_to_a': '回应A任务'}
    requests = []
    monkeypatch.setattr(flows.httpx, 'post', lambda *args, **kw: requests.append(kw['json']) or response)
    monkeypatch.setattr(flows, 'expect', lambda target: SimpleNamespace(to_be_visible=lambda: None))
    if not ai_available:
        with pytest.raises(flows.TestDataRequired):
            a.cross_comment()
        assert events == []
        return
    a.cross_comment()
    assert requests == [{'task_a': 'A的每日任务', 'task_b': 'B的每日任务'}]
    assert [(e[1], e[2]) for e in events if e[0] == 'comment'] == [('A', 'B-post'), ('B', 'A-post')]
    assert all('2026-11-03' in e[-1] and '[自动化测试]' in e[-1] for e in events if e[0] in {'post', 'comment'})
    assert [e for e in events if e[0] == 'verify'] == [('verify', 'A', 'A-post'), ('verify', 'B', 'B-post')]
