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


def test_standalone_delete_establishes_missing_relationship_before_delete(monkeypatch):
    pages, events = scenario()
    empty = SimpleNamespace(count=lambda: 0)
    accept = SimpleNamespace(count=lambda: 1)
    card = SimpleNamespace(locator=lambda selector: empty)
    other = SimpleNamespace(find_test_peer=lambda *args: SimpleNamespace(locator=lambda selector: accept),
        submit=lambda target, endpoint, method: events.append(('accept', endpoint)))

    @contextmanager
    def peer():
        yield other, 'verified-b', 'B', 'verified-a', 'A'

    pages.test_peer = peer
    pages.find_test_peer = lambda *args: card
    states = iter([False, True])
    pages.peer_is_friend = lambda card: next(states)
    monkeypatch.setattr(flows, 'expect', lambda target: SimpleNamespace(to_have_count=lambda count: None))
    pages.delete_friend()
    assert [e[0] for e in events] == ['request', 'accept', 'delete']
