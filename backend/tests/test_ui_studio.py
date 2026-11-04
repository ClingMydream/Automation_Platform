from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models.entities import UiAutomationCase,UiAutomationDataSet,UiAutomationRun
from app.modules.ui_automation import router as api
from app.modules.online_preview import router as preview


@pytest.fixture
def db(tmp_path):
    engine=create_engine(f"sqlite:///{tmp_path/'studio.db'}")
    Base.metadata.create_all(engine)
    with Session(engine)as session:yield session


def test_studio_installs_seventeen_cases_without_overwriting_edits(db):
    cases=api._studio_cases(db)
    assert len(cases)==17
    assert any(c.name == '删除好友' for c in cases)
    cases[0].name='自定义登录';db.commit()
    assert api._studio_cases(db)[0].name=='自定义登录'
    assert db.query(UiAutomationCase).count()==17


def test_edit_is_whitelisted_and_preserves_locator_configuration(db):
    case=api._studio_cases(db)[0]
    payload=api.StudioCaseInput(name='检查首页',steps=[{'action':'assert_text','label':'标题','locator_type':'testid','locator':'heading','value':'首页'}])
    result=api.studio_update_case(case.id,payload,db)
    assert result['steps'][0]['value']=='首页'
    with pytest.raises(HTTPException):
        api.studio_update_case(case.id,api.StudioCaseInput(name='危险动作',steps=[{'action':'eval','label':'代码'}]),db)


def test_only_unmodified_builtin_post_steps_upgrade_to_dual_accounts(db):
    case = next(c for c in api._studio_cases(db) if c.name == '发帖')
    case.steps = api.LEGACY_POST_STEPS; db.commit()
    api._studio_cases(db)
    assert case.steps[-1]['action'] == 'dual_post'
    custom = [{'action': 'assert_visible', 'label': '自定义断言', 'locator': '首页', 'locator_type': 'text'}]
    case.steps = custom; db.commit()
    api._studio_cases(db)
    assert case.steps == custom


def test_run_checks_served_revision_and_dispatches_only_selected_cases(db,monkeypatch):
    cases=api._studio_cases(db)
    db.add(UiAutomationDataSet(name='隔离数据',is_default=True,encrypted_data='test'));db.commit()
    monkeypatch.setattr(api,'_decrypt_credentials',lambda _: {'account_a':{'username':'isolated','password':'secret'},'smoke':{'reset_test_friendship_once':True}})
    monkeypatch.setattr(api,'_jenkins_job_status',lambda _: {'building':False})
    monkeypatch.setattr(api,'_remote_revision',lambda _: {'sha':'new'})
    monkeypatch.setattr(preview,'_deployed_revision',lambda: {'sha':'old'})
    with pytest.raises(HTTPException)as error:
        api.studio_create_run(api.RunInput(case_ids=[cases[0].id]),db)
    assert error.value.status_code==409
    assert db.query(UiAutomationRun).count()==0
    monkeypatch.setattr(preview,'_deployed_revision',lambda: {'sha':'new'})
    sent=[]
    monkeypatch.setattr(api.httpx,'post',lambda *args,**kwargs:sent.append(kwargs['json'])or Mock())
    result=api.studio_create_run(api.RunInput(case_ids=[cases[0].id]),db)
    assert result['status']=='queued'
    assert sent[0]['engine']=='studio-v2'
    assert 'reset_test_friendship_once' not in sent[0]['credentials']['smoke']
    assert [c['id']for c in sent[0]['cases']]==[cases[0].id]
    assert 'credentials' not in result and 'secret' not in str(result)
    with pytest.raises(HTTPException)as error:
        api.studio_create_run(api.RunInput(),db)
    assert error.value.status_code==409
