import importlib.util
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import pytest

pytest.importorskip('playwright.sync_api', reason='Requires the UI runner test environment')
path = Path(__file__).resolve().parents[2] / 'deploy/ui-runner/studio_flows.py'
spec = importlib.util.spec_from_file_location('friend_test_flows', path)
flows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flows)


def scenario():
    pages = object.__new__(flows.EmotePages)
    pages.checks = []
    events = []

    @contextmanager
    def peer():
        yield SimpleNamespace(), 'verified-b', 'B', 'verified-a', 'A'

    pages.test_peer = peer
    pages.find_test_peer = lambda *args: 'card'
    pages.remove_test_peer = lambda card, uid, name: events.append(('delete', uid)) or 'removed-card'
    pages.request_test_peer = lambda card: events.append(('request', card))
    return pages, events


def test_add_existing_friend_deletes_verified_peer_then_requests_without_old_reset_flag():
    pages, events = scenario()
    pages.peer_is_friend = lambda card: True
    pages.friend()
    assert events == [('delete', 'verified-b'), ('request', 'removed-card')]


def test_add_new_friend_does_not_delete_anyone():
    pages, events = scenario()
    pages.peer_is_friend = lambda card: False
    pages.friend()
    assert events == [('request', 'card')]


def test_delete_existing_friend_does_not_send_new_request():
    pages, events = scenario()
    pages.peer_is_friend = lambda card: True
    pages.delete_friend()
    assert events == [('delete', 'verified-b')]


@pytest.mark.parametrize('credentials', [
    {'account_a': {'username': 'A'}},
    {'account_a': {'username': 'A'}, 'account_b': {'username': 'A', 'password': 'test'}},
])
def test_unverified_or_same_accounts_cannot_delete(credentials):
    pages = object.__new__(flows.EmotePages)
    pages.credentials = credentials
    with pytest.raises(AssertionError):
        with pages.test_peer():
            pytest.fail('Invalid identities must never enter destructive actions')


def test_standalone_delete_establishes_missing_relationship_before_delete():
    pages, events = scenario()
    pages.peer_is_friend = lambda card: False
    pages.ensure_test_friendship = lambda *args: events.append(('prepare', 'verified-b')) or 'card'
    pages.delete_friend()
    assert [e[0] for e in events] == ['prepare', 'delete']


def test_daily_friend_limit_is_blocked_without_claiming_request_success(monkeypatch):
    pages = object.__new__(flows.EmotePages);pages.checks = []
    clicked = []
    button = SimpleNamespace(click=lambda: clicked.append(True))
    card = SimpleNamespace(get_by_text=lambda *a, **k: SimpleNamespace(count=lambda: 0), locator=lambda selector: button)
    response = SimpleNamespace(ok=True, json=lambda: {'success':False,'i18nKey':'error.friend.add_limit_daily','message':'今日添加好友已达5次，请明日再来'})
    @contextmanager
    def expected(*args, **kwargs):
        yield SimpleNamespace(value=response)
    pages.page = SimpleNamespace(expect_response=expected)
    monkeypatch.setattr(flows,'expect',lambda target:SimpleNamespace(to_have_count=lambda n:None))
    with pytest.raises(flows.TestDataRequired, match='本轮未发送'):
        pages.request_test_peer(card)
    assert clicked == [True] and pages.checks == []
