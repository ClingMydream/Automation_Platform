"""HTTP persistence, permissions and validation regression tests."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.core.auth import AuthContext, require_menu
from app.modules.data_generator.router import router
from app.modules.data_generator.service import generate_phone_numbers

@pytest.fixture
def env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'batches.db'}", connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    app = FastAPI()
    app.include_router(router)
    def db():
        with sessions() as session:
            yield session
    app.dependency_overrides[get_db] = db
    who = ['alice']
    # Override the route's exact permission dependency while preserving ownership checks.
    for route in router.routes:
        for dep in route.dependant.dependencies:
            if dep.call is not get_db:
                app.dependency_overrides[dep.call] = lambda: AuthContext(who[0], None, False, ['data_generator'])
    return TestClient(app), who

URL = '/v1/tools/data-generator/batches'
def body():
    return {'name': '登录测试', 'request_id': 'request-1', 'rows': [{'phone': generate_phone_numbers(1)[0]['phone'], 'remark': '仅测试'}]}

def test_crud_idempotency_ownership_and_conflicts(env):
    client, who = env
    payload = body()
    r = client.post(URL, json=payload)
    assert r.status_code == 201, r.text
    saved = r.json()
    key = f"{URL}/{saved['id']}"
    assert client.post(URL, json=payload).json()['id'] == saved['id']
    assert client.get(URL, params={'q': '仅测试'}).json()['total'] == 1
    who[0] = 'bob'
    assert client.get(key).status_code == 404
    assert client.put(key, json=payload).status_code == 404
    assert client.delete(key, params={'revision': 1}).status_code == 404
    assert client.get(URL).json()['total'] == 0
    who[0] = 'alice'
    payload['rows'][0]['remark'] = '已修改'
    payload['revision'] = 1
    updated = client.put(key, json=payload)
    assert updated.status_code == 200, updated.text
    assert client.get(key).json()['rows'][0]['remark'] == '已修改'
    assert client.put(key, json=payload).status_code == 409
    assert client.delete(key, params={'revision': 1}).status_code == 409
    assert client.delete(key, params={'revision': 2}).status_code == 200
    assert client.get(key).status_code == 404

@pytest.mark.parametrize('case', ['invalid_phone', 'duplicate', 'empty', 'blank'])
def test_invalid_batches_rejected(env, case):
    client, _ = env
    payload = body()
    if case == 'invalid_phone': payload['rows'][0]['phone'] = '12800138000'
    if case == 'duplicate': payload['rows'] *= 2
    if case == 'empty': payload['rows'] = []
    if case == 'blank': payload['name'] = '  '
    assert client.post(URL, json=payload).status_code == 422

def test_unauthenticated():
    app = FastAPI()
    app.include_router(router)
    assert TestClient(app).get(URL).status_code == 401
