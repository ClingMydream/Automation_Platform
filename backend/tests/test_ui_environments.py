from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.modules.ui_automation import router as api
from app.modules.online_preview import router as preview
from app.models.entities import UiAutomationDataSet, UiAutomationRun


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path/'env.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(api, '_validate_target_url', lambda value: (value or 'http://frontend/emote-preview/', value or ''))
    with Session(engine) as session:
        yield session


def test_environment_crud_survives_new_session_and_duplicate_names(db):
    row = api.create_environment(api.EnvironmentInput(name=' 测试站 ', base_url='https://example.com/', notes='备注'), db)
    assert row['name'] == '测试站'
    assert api.list_environments(db)[0]['notes'] == '备注'
    with Session(db.bind) as another:
        assert api.list_environments(another)[0]['id'] == row['id']
    with pytest.raises(HTTPException) as error:
        api.create_environment(api.EnvironmentInput(name='测试站'), db)
    assert error.value.status_code == 409
    updated = api.update_environment(row['id'], api.EnvironmentInput(name='新环境', viewport='desktop'), db)
    assert updated['viewport'] == 'desktop' and updated['base_url'] == ''
    api.delete_environment(row['id'], db)
    assert api.list_environments(db) == []
    with pytest.raises(HTTPException):
        api.update_environment(row['id'], api.EnvironmentInput(name='已删'), db)


def test_saved_environment_is_resolved_on_server_and_history_is_independent(db, monkeypatch):
    case = api._studio_cases(db)[0]
    env = api.create_environment(api.EnvironmentInput(name='测试站', base_url='https://example.com/'), db)
    db.add(UiAutomationDataSet(name='隔离账号', is_default=True, encrypted_data='test')); db.commit()
    monkeypatch.setattr(api, '_jenkins_job_status', lambda _: {'building': False})
    monkeypatch.setattr(api, '_remote_revision', lambda _: {'sha': 'new'})
    monkeypatch.setattr(api, '_decrypt_credentials', lambda _: {})
    sent = []
    monkeypatch.setattr(api.httpx, 'post', lambda *args, **kw: sent.append(kw['json']) or Mock())
    run = api.studio_create_run(api.RunInput(environment_id=env['id'], case_ids=[case.id]), db)
    assert sent[0]['base_url'] == 'https://example.com/'
    api.update_environment(env['id'], api.EnvironmentInput(name='已修改', base_url='https://other.example/'), db)
    api.delete_environment(env['id'], db)
    stored = db.get(UiAutomationRun, run['id'])
    assert stored.result_summary['environment']['name'] == '测试站'
    assert stored.result_summary['target_url'] == 'https://example.com/'
    stored.status = 'passed'; db.commit()
    with pytest.raises(HTTPException) as error:
        api.studio_create_run(api.RunInput(environment_id=env['id']), db)
    assert error.value.status_code == 404


def test_invalid_environment_fields(db):
    for body in [dict(name='  '), dict(name='环境', viewport='unknown')]:
        with pytest.raises(HTTPException):
            api.create_environment(api.EnvironmentInput(**body), db)


@pytest.mark.parametrize('url', ['file:///data/private', 'http://user:pass@example.com/', 'http://127.0.0.1/', 'http://backend/'])
def test_environment_url_uses_existing_target_safety_rules(url):
    with pytest.raises(HTTPException):
        api._validate_target_url(url)
