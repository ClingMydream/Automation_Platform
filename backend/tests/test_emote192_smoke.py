"""Additive catalog, whitelist, runner safety and honest complete reporting."""
import importlib
import sys
import types
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.modules.ui_automation import router as api
from app.modules.ui_automation.smoke_catalog import SMOKE_CATALOG, SMOKE_KEYS
from app.models.entities import UiAutomationCase

@pytest.fixture
def db(tmp_path):
    engine=create_engine(f"sqlite:///{tmp_path / 'catalog.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:yield session


def test_catalog_is_additive_and_does_not_restore_user_edits(db):
    api._seed(db)
    cases=db.query(UiAutomationCase).all()
    专项=[x for x in cases if 'emote192' in x.tags]
    assert len(专项)==16 and len(SMOKE_KEYS)==16
    original=next(x for x in cases if 'emote192' not in x.tags)
    original.name='保留用户自定义名称';original.steps=[{'action':'screenshot'}]
    专项[0].name='用户修改专项';deleted_id=专项[1].id;db.delete(专项[1]);db.commit()
    api._seed(db)
    assert db.get(UiAutomationCase,deleted_id) is None
    assert db.get(UiAutomationCase,专项[0].id).name=='用户修改专项'
    assert original.name=='保留用户自定义名称' and original.steps==[{'action':'screenshot'}]


def test_scenario_whitelist():
    for key in SMOKE_KEYS:api._validate_steps([{'action':'emote_smoke','scenario':key}])
    with pytest.raises(HTTPException):api._validate_steps([{'action':'emote_smoke','scenario':'arbitrary_python'}])


def test_selection_and_one_run_consent(db,monkeypatch):
    sent=[]
    monkeypatch.setattr(api,'_remote_revision',lambda b:{'sha':'abc'})
    monkeypatch.setattr(api,'_jenkins_job_status',lambda name:{'building':False})
    monkeypatch.setattr(api,'_validate_target_url',lambda url:('http://frontend/emote-preview/',url))
    monkeypatch.setattr(api.httpx,'post',lambda *a,**kw:sent.append(kw['json']) or Mock())
    api.create_run(api.RunInput(mode='emote192'),db=db)
    assert len(sent[-1]['cases'])==16 and sent[-1]['allow_sensitive'] is False
    api.create_run(api.RunInput(mode='regression'),db=db)
    assert not any('sensitive' in x['tags'] for x in sent[-1]['cases'])
    with pytest.raises(HTTPException) as error:
        api.create_run(api.RunInput(mode='emote192',target_url='https://example.com',allow_sensitive=True),db=db)
    assert error.value.status_code==400


@pytest.fixture
def runner(monkeypatch,tmp_path):
    # Browser is stubbed only in unit tests. Actual integration uses the container's Playwright.
    fake=types.ModuleType('playwright.sync_api');fake.expect=Mock();fake.sync_playwright=Mock()
    monkeypatch.setitem(sys.modules,'playwright',types.ModuleType('playwright'))
    monkeypatch.setitem(sys.modules,'playwright.sync_api',fake)
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/'deploy/ui-runner'))
    monkeypatch.setitem(sys.modules,'smoke_catalog',importlib.import_module('app.modules.ui_automation.smoke_catalog'))
    for name in ('emote_smoke','runner'):sys.modules.pop(name,None)
    module=importlib.import_module('runner')
    monkeypatch.setattr(module,'DATA_ROOT',tmp_path)
    return module


def test_deletion_guards_and_no_token_in_diagnostics(runner):
    smoke=importlib.import_module('emote_smoke')
    credentials={'account_a':{'username':'A'},'account_b':{'username':'B','password':'test-secret'}}
    root='https://www.inxpiration.cn/emote-test/api'
    assert smoke.deletion_allowed('',root,credentials,True)
    for other in ('https://www.inxpiration.cn/api','https://evil.example/emote-test/api','http://www.inxpiration.cn/emote-test/api'):
        assert not smoke.deletion_allowed('',other,credentials,True)
    assert not smoke.deletion_allowed('',root,credentials,False)
    assert 'secret' not in runner.diagnostic_url('https://u:secret@host/api?token=secret&phone=secret&size=20')
    req=Mock(method='POST',url='https://host/login?token=secret',headers={},post_data='{"password":"secret","phone":"secret","safe":1}')
    assert 'secret' not in runner.safe_curl(req)


@pytest.mark.parametrize('first_status',['failed','blocked'])
def test_failed_or_blocked_case_continues_and_never_reports_all_passed(runner,monkeypatch,first_status):
    seen=[];callbacks=[]
    browser=Mock();context=Mock();page=Mock();page.video=None;context.pages=[page]
    browser.new_context.return_value=context
    pw=Mock();pw.chromium.launch.return_value=browser
    manager=Mock();manager.__enter__=Mock(return_value=pw);manager.__exit__=Mock(return_value=False)
    monkeypatch.setattr(runner,'sync_playwright',lambda:manager)
    monkeypatch.setattr(runner,'prepare_authenticated_state_with_retry',lambda *a:None)
    monkeypatch.setattr(runner,'reusable_auth_state',lambda p:p)
    monkeypatch.setattr(runner,'auth_state_path',lambda *a:None)
    monkeypatch.setattr(runner,'callback',lambda ident,**payload:callbacks.append(payload))
    def step(page,contexts,step,variables,url):
        seen.append(step['scenario'])
        if step['scenario']=='first':
            if first_status=='blocked':raise runner.ScenarioBlocked('fixture absent')
            raise AssertionError('business failed')
        return page
    monkeypatch.setattr(runner,'execute_step',step)
    cases=[{'id':i,'name':str(i),'feature_name':'feature','steps':[{'action':'emote_smoke','scenario':key}]} for i,key in enumerate(('first','second'),1)]
    runner.run_task({'run_id':99,'base_url':'http://test/','viewport':'mobile','cases':cases,'credentials':{}})
    assert seen==['first','second'] # Not retried: no duplicate writes.
    result=callbacks[-1]['result_summary']['report']
    assert result['passed']==1 and result[first_status]==1
    assert result['status']!='passed' and result['interrupted']==0
    assert callbacks[-1]['status']==('failed' if first_status=='failed' else 'interrupted')


def test_unknown_restoration_is_safety_stop(runner):
    smoke=importlib.import_module('emote_smoke')
    flow=object.__new__(smoke.Flow);flow.request=Mock(side_effect=smoke.ScenarioBlocked('network'))
    with pytest.raises(smoke.SafetyStop):flow.restore_block('A','B')


def test_cooling_recovery_can_login_without_existing_token(runner):
    smoke=importlib.import_module('emote_smoke')
    flow=object.__new__(smoke.Flow);flow.root='https://test/api';flow.token=Mock(return_value='')
    flow.page=Mock();flow.page.context.request.fetch.return_value.json.return_value={'success':True}
    assert flow.request('POST','/login',{'phone':'test','password':'test'})['success']
    assert 'Authorization' not in flow.page.context.request.fetch.call_args.kwargs['headers']
    with pytest.raises(smoke.ScenarioBlocked):flow.request('GET','/blocks')

