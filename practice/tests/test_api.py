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

COMMERCE='/commerce'
OTHER={'Authorization':'Bearer '+os.environ['PRACTICE_OTHER_CUSTOMER_TOKEN']}
WAREHOUSE={'Authorization':'Bearer '+os.environ['PRACTICE_WAREHOUSE_TOKEN']}
def clear_cart(headers=CUSTOMER):
    for item in request('GET',COMMERCE+'/cart',headers).json()['items']:assert request('DELETE',COMMERCE+'/cart/items/'+str(item['id']),headers).status_code==200

def cart_product(item,quantity=1,headers=CUSTOMER):
    response=request('PUT',COMMERCE+'/cart/items',headers,json={'product_id':item['id'],'quantity':quantity});assert response.status_code==200,response.text

def checkout_payload(headers=CUSTOMER):
    cart=request('GET',COMMERCE+'/cart',headers).json();address=request('GET',COMMERCE+'/addresses',headers).json()[0]
    return {'address_id':address['id'],'address_version':address['version'],'cart_revision':cart['revision'],'quote_hash':cart['quote_hash'],'request_key':uuid4().hex}

def test_commerce_cart_checkout_cancel():
    clear_cart();one,two=product(5),product(4);cart_product(one,2);cart_product(two);payload=checkout_payload()
    created=request('POST',COMMERCE+'/checkout',CUSTOMER,json=payload);assert created.status_code==201,created.text
    order=created.json();assert order['subtotal_cents']==8700 and order['shipping_cents']==500 and order['total_cents']==9200
    assert request('POST',COMMERCE+'/checkout',CUSTOMER,json=payload).json()['id']==order['id']
    assert request('GET',COMMERCE+'/orders/'+order['id'],OTHER).status_code==404
    for _ in range(2):assert request('POST',COMMERCE+'/orders/'+order['id']+'/cancel',CUSTOMER,json={}).json()['status']=='cancelled'
    assert current(one['id'])['stock']==5 and current(two['id'])['stock']==4

def test_commerce_order_lifecycle():
    clear_cart();item=product(3);cart_product(item);order=request('POST',COMMERCE+'/checkout',CUSTOMER,json=checkout_payload()).json();path=COMMERCE+'/orders/'+order['id']
    assert request('POST',path+'/pay',CUSTOMER,json={}).json()['status']=='paid'
    assert request('POST',path+'/cancel',CUSTOMER,json={}).status_code==409
    assert request('POST',path+'/ship',CUSTOMER,json={'tracking_number':'DEMO12345678'}).status_code==403
    assert request('POST',path+'/ship',WAREHOUSE,json={'tracking_number':'DEMO12345678'}).json()['status']=='shipped'
    assert request('POST',path+'/receive',CUSTOMER,json={}).json()['status']=='completed'
    assert request('POST',path+'/refund',CUSTOMER,json={'reason':'自动化退货退款验收'}).json()['status']=='refund_requested'
    assert request('POST',path+'/refund-decision',ADMIN,json={'approve':True,'return_received':False,'note':'尚未收货'}).status_code==409
    for _ in range(2):assert request('POST',path+'/refund-decision',ADMIN,json={'approve':True,'return_received':True,'note':'已收到退货'}).json()['status']=='refunded'
    assert current(item['id'])['stock']==3

def test_commerce_quote_conflicts_and_inventory_role():
    clear_cart();item=product(3);cart_product(item);stale=checkout_payload();body={'name':item['name'],'category':'办公文具','description':'报价校验','price_cents':3900,'status':'active','version':item['version']}
    assert request('PUT',COMMERCE+'/products/'+str(item['id']),WAREHOUSE,json=body).status_code==403
    updated=request('PUT',COMMERCE+'/products/'+str(item['id']),ADMIN,json=body);assert updated.status_code==200
    assert request('POST',COMMERCE+'/checkout',CUSTOMER,json=stale).status_code==409
    receipt={'quantity':2,'reason':'自动化入库','version':updated.json()['version'],'request_key':uuid4().hex}
    for _ in range(2):assert request('POST',COMMERCE+'/inventory/'+str(item['id'])+'/receipt',WAREHOUSE,json=receipt).json()['stock']==5
    assert request('GET',COMMERCE+'/inventory',CUSTOMER).status_code==403
    clear_cart()

def test_commerce_concurrent_checkout():
    clear_cart();clear_cart(OTHER);item=product(1);cart_product(item);cart_product(item,headers=OTHER);payloads=[(CUSTOMER,checkout_payload()),(OTHER,checkout_payload(OTHER))]
    with ThreadPoolExecutor(max_workers=2)as pool:responses=list(pool.map(lambda pair:request('POST',COMMERCE+'/checkout',pair[0],json=pair[1]),payloads))
    assert sorted(r.status_code for r in responses)==[201,409]
    assert current(item['id'])['stock']==0
    for (headers,_),response in zip(payloads,responses):
        if response.status_code==201:request('POST',COMMERCE+'/orders/'+response.json()['id']+'/cancel',headers,json={})
    clear_cart();clear_cart(OTHER)
