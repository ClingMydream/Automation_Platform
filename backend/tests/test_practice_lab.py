from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import hash_password,create_access_token
from app.db import Base,get_db
from app.models.entities import AppUser
from app.modules.practice_lab.router import management,router
from app.modules.practice_lab import execution,docs
from app.modules.personal_workspace.router import router as personal
from app.modules.personal_workspace import extras,learning

@pytest.fixture
def env(tmp_path,monkeypatch):
    monkeypatch.setenv('PERSONAL_WORKSPACE_DATA_DIR',str(tmp_path/'files'))
    engine=create_engine('sqlite:///'+str(tmp_path/'platform.db'),connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);sessions=sessionmaker(bind=engine)
    with sessions()as db:
        db.add_all([AppUser(username=name,password_hash=hash_password('test-only'),is_admin=False,is_active=True,menu_permissions=['practice_lab']if name!='denied'else[])for name in ['alice','bob','denied']]);db.commit()
    app=FastAPI();app.include_router(management,prefix='/api');app.include_router(router,prefix='/api');app.include_router(personal,prefix='/api');docs.mount_docs(app)
    def override():
        with sessions()as db:yield db
    app.dependency_overrides[get_db]=override
    return SimpleNamespace(client=TestClient(app),sessions=sessions,headers={name:{'Authorization':'Bearer '+create_access_token(name)}for name in ['alice','bob','denied']})

def login(env,owner='alice',username='lab_admin'):
    response=env.client.post('/api/v1/practice-lab/login',headers=env.headers[owner],json={'username':username,'password':'Practice123!'})
    assert response.status_code==200,response.text
    return {'Authorization':'Bearer '+response.json()['token']}

def product(env,headers,stock=5):
    response=env.client.post('/api/practice/v1/products',headers=headers,json={'sku':'T_'+uuid4().hex,'name':'测试商品','price_cents':2900,'stock':stock})
    assert response.status_code==201,response.text
    return response.json()

def test_roles_tenants_seed_and_reset(env):
    assert env.client.get('/api/v1/practice-lab/status',headers=env.headers['denied']).status_code==403
    admin=login(env);customer=login(env,username='learner');bob=login(env,owner='bob')
    assert env.client.get('/api/practice/v1/products',headers=env.headers['alice']).status_code==401
    assert env.client.get('/api/v1/personal-workspace/records',headers=admin).status_code==401
    item=product(env,admin)
    assert not any(row['id']==item['id']for row in env.client.get('/api/practice/v1/products',headers=bob).json())
    assert env.client.post('/api/practice/v1/products',headers=customer,json={'sku':'X','name':'x','price_cents':1,'stock':1}).status_code==403
    assert env.client.post('/api/v1/practice-lab/reset',headers=env.headers['alice'],json={'confirmation':'anything'}).status_code==422
    assert env.client.post('/api/v1/practice-lab/reset',headers=env.headers['alice'],json={'confirmation':'重置练习数据'}).status_code==200
    assert env.client.get('/api/practice/v1/products',headers=admin).status_code==401
    fresh=login(env);rows=env.client.get('/api/practice/v1/products',headers=fresh).json()
    assert [(row['sku'],row['stock'])for row in rows]==[('BAG-003',0),('LAMP-002',5),('NOTE-001',20)]

def test_order_idempotency_cancel_and_optimistic_stock(env):
    admin=login(env);customer=login(env,username='learner');item=product(env,admin)
    payload={'product_id':item['id'],'quantity':2,'request_key':uuid4().hex}
    first=env.client.post('/api/practice/v1/orders',headers=customer,json=payload).json()
    assert first['total_cents']==5800
    assert env.client.post('/api/practice/v1/orders',headers=customer,json=payload).json()['id']==first['id']
    assert env.client.post('/api/practice/v1/orders',headers=customer,json={**payload,'quantity':3}).status_code==409
    rows=env.client.get('/api/practice/v1/products',headers=admin).json();current=next(row for row in rows if row['id']==item['id'])
    assert current['stock']==3
    for _ in range(2):assert env.client.post('/api/practice/v1/orders/'+first['id']+'/cancel',headers=customer).json()['status']=='cancelled'
    current=next(row for row in env.client.get('/api/practice/v1/products',headers=admin).json()if row['id']==item['id']);assert current['stock']==5
    assert env.client.put(f'/api/practice/v1/products/{item["id"]}/stock',headers=admin,json={'stock':9,'version':item['version']}).status_code==409
    assert env.client.put(f'/api/practice/v1/products/{item["id"]}/stock',headers=admin,json={'stock':9,'version':current['version']}).status_code==200

def test_concurrent_orders_cannot_oversell(env):
    admin=login(env);customer=login(env,username='learner');item=product(env,admin,2)
    def buy(_):return env.client.post('/api/practice/v1/orders',headers=customer,json={'product_id':item['id'],'quantity':1,'request_key':uuid4().hex}).status_code
    with ThreadPoolExecutor(max_workers=4)as pool:statuses=list(pool.map(buy,range(4)))
    assert sorted(statuses)==[201,201,409,409]
    row=next(row for row in env.client.get('/api/practice/v1/products',headers=admin).json()if row['id']==item['id']);assert row['stock']==0

def test_personal_http_attachments_learning_and_summary(env):
    c=env.client;a=env.headers['alice'];b=env.headers['bob']
    created=c.post('/api/v1/personal-workspace/records',headers=a,json={'kind':'note','title':'Python','content':'```python\nprint(1)\n```','client_request_id':'idempotent-note'});assert created.status_code==201
    note=created.json();assert c.post('/api/v1/personal-workspace/records',headers=a,json={'kind':'note','title':'Python','content':note['content'],'client_request_id':'idempotent-note'}).json()['id']==note['id']
    assert c.get('/api/v1/personal-workspace/records/'+str(note['id']),headers=b).status_code==404
    attachment=c.post(f'/api/v1/personal-workspace/records/{note["id"]}/attachments',headers=a,files={'file':('demo.py',b'print(1)','text/plain')});assert attachment.status_code==201
    file=attachment.json();assert c.get('/api/v1/personal-workspace/attachments/'+str(file['id']),headers=b).status_code==404
    assert c.get('/api/v1/personal-workspace/attachments/'+str(file['id']),headers=a).content==b'print(1)'
    saved=c.put('/api/v1/personal-workspace/lessons/python-values',headers=a,json={'status':'practiced','evidence':'运行并改写了列表筛选，验证输出结果','note_id':note['id']});assert saved.status_code==200
    assert c.put('/api/v1/personal-workspace/lessons/python-values',headers=b,json={'status':'practiced','evidence':'运行并改写了列表筛选，验证输出结果','note_id':note['id']}).status_code==404
    assert c.put('/api/v1/personal-workspace/lessons/api-orders',headers=a,json={'status':'verified','evidence':'实际下单与取消，确认库存只恢复一次','run_id':999}).status_code==422
    summary=c.get('/api/v1/personal-workspace/summary',headers=a);assert summary.status_code==200 and summary.json()['notes'][0]['id']==note['id']
    assert c.get('/api/practice/openapi.json').status_code==200
    download=c.get('/api/v1/practice-lab/project-download',headers=a);assert download.status_code==200 and download.content.startswith(b'PK')

def test_unavailable_executor_is_explicit_not_passed(env,monkeypatch):
    def fail(*args,**kwargs):
        from fastapi import HTTPException
        raise HTTPException(503,'isolated runner unavailable')
    monkeypatch.setattr(execution,'runner_request',fail)
    response=env.client.post('/api/v1/practice-lab/runs',headers=env.headers['alice'],json={'suite':'api'})
    assert response.status_code==503
    rows=env.client.get('/api/v1/practice-lab/runs',headers=env.headers['alice']).json()
    assert rows[0]['status']=='blocked' and 'error'in rows[0]['result']
