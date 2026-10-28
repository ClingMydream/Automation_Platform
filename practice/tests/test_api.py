"""Run against a personal sandbox. Tokens stay in environment variables, never reports."""
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import requests

BASE=os.environ['PRACTICE_API_URL'].rstrip('/')
ADMIN={'Authorization':'Bearer '+os.environ['PRACTICE_ADMIN_TOKEN']}
CUSTOMER={'Authorization':'Bearer '+os.environ['PRACTICE_CUSTOMER_TOKEN']}

def request(method,path,headers=None,**kwargs):
    return requests.request(method,BASE+path,headers=headers,timeout=(3,10),**kwargs)

def product(stock=5):
    response=request('POST','/products',ADMIN,json={'sku':'AUTO_'+uuid4().hex[:16],'name':'自动化专用商品','price_cents':2900,'stock':stock})
    assert response.status_code==201
    return response.json()

def current(identifier):
    return next(row for row in request('GET','/products',CUSTOMER).json()if row['id']==identifier)

def test_authentication_and_role():
    assert request('GET','/products').status_code==401
    assert request('POST','/products',CUSTOMER,json={'sku':'DENIED','name':'禁止','price_cents':1,'stock':1}).status_code==403

def test_order_cancel_and_idempotency():
    item=product();payload={'product_id':item['id'],'quantity':2,'request_key':uuid4().hex}
    created=request('POST','/orders',CUSTOMER,json=payload);assert created.status_code==201
    order=created.json();assert order['total_cents']==5800
    assert request('POST','/orders',CUSTOMER,json=payload).json()['id']==order['id']
    assert current(item['id'])['stock']==3
    assert request('POST','/orders/'+order['id']+'/cancel',CUSTOMER).json()['status']=='cancelled'
    request('POST','/orders/'+order['id']+'/cancel',CUSTOMER)
    assert current(item['id'])['stock']==5

def test_validation_and_stock_version():
    item=product(0)
    assert request('POST','/orders',CUSTOMER,json={'product_id':item['id'],'quantity':1,'request_key':uuid4().hex}).status_code==409
    assert request('POST','/orders',CUSTOMER,json={'product_id':item['id'],'quantity':0,'request_key':uuid4().hex}).status_code==422
    assert request('PUT',f'/products/{item["id"]}/stock',ADMIN,json={'stock':3,'version':item['version']}).status_code==200
    assert request('PUT',f'/products/{item["id"]}/stock',ADMIN,json={'stock':9,'version':item['version']}).status_code==409

def test_concurrent_inventory_never_negative():
    item=product(2)
    def buy(_):return request('POST','/orders',CUSTOMER,json={'product_id':item['id'],'quantity':1,'request_key':uuid4().hex})
    with ThreadPoolExecutor(max_workers=4)as pool:responses=list(pool.map(buy,range(4)))
    assert sorted(response.status_code for response in responses)==[201,201,409,409]
    assert current(item['id'])['stock']==0
    for response in responses:
        if response.status_code==201:request('POST','/orders/'+response.json()['id']+'/cancel',CUSTOMER)
