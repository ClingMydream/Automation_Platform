from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.modules.online_preview import router


def test_missing_codeup_settings_do_not_call_git(monkeypatch):
    monkeypatch.setattr(router,'get_settings',lambda:SimpleNamespace(codeup_username='',codeup_password=''))
    git=Mock(side_effect=AssertionError('must not contact remote'))
    monkeypatch.setattr(router.subprocess,'run',git)
    with pytest.raises(HTTPException) as err:router._remote_revision('dev-20260930-1.9.2')
    assert err.value.status_code==503 and not git.called


@pytest.mark.parametrize('output',[None,'','bad format','bad\x1fa\x1fb\x1fc\x1fd'])
def test_malformed_git_metadata_is_explicit_502(monkeypatch,output):
    monkeypatch.setattr(router,'get_settings',lambda:SimpleNamespace(codeup_username='test',codeup_password='test'))
    monkeypatch.setattr(router.subprocess,'run',lambda *args,**kw:SimpleNamespace(stdout=output))
    with pytest.raises(HTTPException) as err:router._remote_revision('test')
    assert err.value.status_code==502


def test_unicode_git_metadata_is_decoded_explicitly(monkeypatch):
    monkeypatch.setattr(router,'get_settings',lambda:SimpleNamespace(codeup_username='test',codeup_password='test'))
    calls=[]
    def git(*a,**kw):
        calls.append(kw);return SimpleNamespace(stdout='a'*40+'\x1f测试者\x1ftest@example.invalid\x1f2026-10-26T00:00:00Z\x1f中文提交')
    monkeypatch.setattr(router.subprocess,'run',git)
    assert router._remote_revision('test')['subject']=='中文提交'
    assert all(x['encoding']=='utf-8' and x['errors']=='replace' for x in calls)


def test_branch_listing_without_credentials_stays_local(monkeypatch):
    monkeypatch.setattr(router,'get_settings',lambda:SimpleNamespace(codeup_username='',codeup_password=''))
    remote=Mock(side_effect=AssertionError('no unconfigured remote calls'))
    monkeypatch.setattr(router.httpx,'get',remote)
    with pytest.raises(HTTPException) as err:router.list_preview_branches()
    assert err.value.status_code==503 and not remote.called
