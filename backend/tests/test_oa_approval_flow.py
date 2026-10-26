"""Isolated approval flow: real routes/database, no external messages or accounts."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthContext, get_current_user
from app.db import Base, get_db
from app.modules.oa.router import router


@pytest.fixture
def approval_env():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        app = FastAPI()
        app.include_router(router)
        who = [AuthContext('admin', '管理员', True, [])]
        app.dependency_overrides[get_current_user] = lambda: who[0]
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            yield client, who
    engine.dispose()


def test_submit_review_and_duplicate_decision(approval_env):
    client, who = approval_env
    def create(name, reviewers=()):
        response = client.post('/oa/admin/accounts', json={'username': name, 'password': 'isolated-only', 'display_name': name, 'approver_account_ids': list(reviewers)})
        assert response.status_code == 200, response.text
        return response.json()['id']
    reviewer_id = create('reviewer')
    create('requester', [reviewer_id])
    create('unrelated')
    login = client.post('/oa/auth/account-login', json={'username': 'requester', 'password': 'isolated-only'})
    assert login.status_code == 200 and login.json()['access_token']
    who[0] = AuthContext('requester', '申请人', False, [])
    assert client.post('/oa/requests', json={'template_key': 'purchase', 'form_data': {}}).status_code == 422
    data = {'template_key': 'purchase', 'form_data': {'item_name': '隔离测试用品', 'category': '居家用品', 'amount': '12.50', 'reason': '验证审批'}}
    response = client.post('/oa/requests', json=data)
    assert response.status_code == 200, response.text
    request_id = response.json()['id']
    assert response.json()['status'] == 'pending'
    assert client.post(f'/oa/requests/{request_id}/decision', json={'action': 'approved'}).status_code == 403
    who[0] = AuthContext('unrelated', '无关人员', False, [])
    assert client.get('/oa/requests').json() == []
    assert client.post(f'/oa/requests/{request_id}/decision', json={'action': 'approved'}).status_code == 403
    who[0] = AuthContext('reviewer', '审核人', False, [])
    assert request_id in [row['id'] for row in client.get('/oa/requests?scope=pending').json()]
    response = client.post(f'/oa/requests/{request_id}/decision', json={'action': 'approved', 'comment': '验证通过'})
    assert response.status_code == 200 and response.json()['status'] == 'approved'
    assert client.post(f'/oa/requests/{request_id}/decision', json={'action': 'rejected'}).status_code == 409
    assert client.get('/oa/requests?scope=pending').json() == []
    who[0] = AuthContext('requester', '申请人', False, [])
    record = next(row for row in client.get('/oa/requests').json() if row['id'] == request_id)
    assert record['status'] == 'approved'
    assert [item['action'] for item in record['actions']] == ['submitted', 'approved']
