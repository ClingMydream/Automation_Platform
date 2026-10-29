from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from test_practice_lab import env,login,product

P='/api/practice/v1/commerce'
def add(c,h,pid,quantity=1):
    r=c.put(P+'/cart/items',headers=h,json={'product_id':pid,'quantity':quantity});assert r.status_code==200,r.text;return r.json()
def payload(c,h):
    cart=c.get(P+'/cart',headers=h).json();address=c.get(P+'/addresses',headers=h).json()[0]
    return {'address_id':address['id'],'address_version':address['version'],'cart_revision':cart['revision'],'quote_hash':cart['quote_hash'],'request_key':uuid4().hex}
def checkout(c,h,data=None):
    r=c.post(P+'/checkout',headers=h,json=data or payload(c,h));assert r.status_code==201,r.text;return r.json()

def test_commerce_atomic_checkout_ownership_cancel_and_snapshots(env):
    c=env.client;admin=login(env);a=login(env,username='learner');b=login(env,username='buyer_two');p1=product(env,admin,5);p2=product(env,admin,4)
    add(c,a,p1['id'],2);add(c,a,p2['id']);data=payload(c,a);order=checkout(c,a,data)
    assert order['subtotal_cents']==8700 and order['shipping_cents']==500 and order['total_cents']==9200 and len(order['items'])==2
    assert c.post(P+'/checkout',headers=a,json=data).json()['id']==order['id']
    assert c.post(P+'/checkout',headers=a,json={**data,'remark':'changed'}).status_code==409
    assert c.get(P+'/orders/'+order['id'],headers=b).status_code==404
    assert c.post(P+'/orders/'+order['id']+'/cancel',headers=b).status_code==404
    address_id=data['address_id'];assert c.delete(P+'/addresses/'+str(address_id),headers=b).status_code==404
    assert c.delete(P+'/addresses/'+str(address_id),headers=a).status_code==200
    assert c.get(P+'/orders/'+order['id'],headers=a).json()['address']['recipient']=='练习收件人'
    for _ in range(2):assert c.post(P+'/orders/'+order['id']+'/cancel',headers=a).json()['status']=='cancelled'
    assert c.get(P+'/products/'+str(p1['id']),headers=a).json()['stock']==5
    assert c.get(P+'/products/'+str(p2['id']),headers=a).json()['stock']==4
    assert c.post(P+'/orders/'+order['id']+'/pay',headers=a).status_code==409
    events=c.get(P+'/orders/'+order['id'],headers=a).json()['events'];assert [r['action']for r in events]==['checkout','cancel_order']

def test_commerce_payment_shipping_return_and_roles(env):
    c=env.client;admin=login(env);warehouse=login(env,username='warehouse');a=login(env,username='learner');item=product(env,admin,5)
    assert c.get(P+'/cart',headers=warehouse).status_code==403
    assert c.put(P+'/products/'+str(item['id']),headers=warehouse,json={**item,'category':'办公文具','description':'test','status':'inactive'}).status_code==422 # unknown sku/stock forbidden
    add(c,a,item['id'],2);order=checkout(c,a)
    assert c.post(P+'/orders/'+order['id']+'/ship',headers=warehouse,json={'tracking_number':'DEMO12345678'}).status_code==409
    for _ in range(2):assert c.post(P+'/orders/'+order['id']+'/pay',headers=a).json()['status']=='paid'
    assert c.post(P+'/orders/'+order['id']+'/cancel',headers=a).status_code==409
    assert c.post(P+'/orders/'+order['id']+'/ship',headers=a,json={'tracking_number':'DEMO12345678'}).status_code==403
    assert c.post(P+'/orders/'+order['id']+'/ship',headers=warehouse,json={'tracking_number':'DEMO12345678'}).json()['status']=='shipped'
    assert c.post(P+'/orders/'+order['id']+'/refund',headers=a,json={'reason':'需要退回验收商品'}).status_code==409
    assert c.post(P+'/orders/'+order['id']+'/receive',headers=a).json()['status']=='completed'
    assert c.post(P+'/orders/'+order['id']+'/refund',headers=a,json={'reason':'需要退回验收商品'}).json()['status']=='refund_requested'
    decision={'approve':True,'return_received':False,'note':'已核对申请'}
    assert c.post(P+'/orders/'+order['id']+'/refund-decision',headers=warehouse,json=decision).status_code==403
    assert c.post(P+'/orders/'+order['id']+'/refund-decision',headers=admin,json=decision).status_code==409
    for _ in range(2):assert c.post(P+'/orders/'+order['id']+'/refund-decision',headers=admin,json={**decision,'return_received':True}).json()['status']=='refunded'
    assert c.get(P+'/products/'+str(item['id']),headers=a).json()['stock']==5
    events=c.get(P+'/orders/'+order['id'],headers=a).json()['events'];assert [r['action']for r in events].count('demo_payment')==1 and [r['action']for r in events].count('refund_approve')==1

def test_commerce_stale_quote_stock_receipts_and_address_validation(env):
    c=env.client;admin=login(env);a=login(env,username='learner');warehouse=login(env,username='warehouse');item=product(env,admin,3)
    add(c,a,item['id']);data=payload(c,a)
    edit={'name':item['name'],'category':'办公文具','description':'更新描述','price_cents':9900,'status':'active','version':item['version']}
    assert c.put(P+'/products/'+str(item['id']),headers=warehouse,json=edit).status_code==403
    assert c.put(P+'/products/'+str(item['id']),headers=admin,json=edit).status_code==200
    assert c.post(P+'/checkout',headers=a,json=data).status_code==409
    item=c.get(P+'/products/'+str(item['id']),headers=admin).json();receipt={'quantity':4,'reason':'验收入库','version':item['version'],'request_key':uuid4().hex}
    for _ in range(2):assert c.post(P+'/inventory/'+str(item['id'])+'/receipt',headers=warehouse,json=receipt).json()['stock']==7
    assert c.post(P+'/inventory/'+str(item['id'])+'/receipt',headers=warehouse,json={**receipt,'quantity':5}).status_code==409
    assert c.post(P+'/addresses',headers=a,json={'recipient':'a','phone':'123','region':'test','detail':'somewhere'}).status_code==422
    assert c.post(P+'/addresses',headers=a,json={'recipient':' ','phone':'19900000000','region':'test','detail':'somewhere'}).status_code==422
    add(c,a,item['id'],2);order=checkout(c,a);assert order['subtotal_cents']==19800 and order['shipping_cents']==500
    c.post(P+'/orders/'+order['id']+'/cancel',headers=a)
    add(c,a,item['id'],3);assert checkout(c,a)['shipping_cents']==0

def test_commerce_concurrent_last_unit_has_one_winner(env):
    c=env.client;admin=login(env);a=login(env,username='learner');b=login(env,username='buyer_two');item=product(env,admin,1)
    add(c,a,item['id']);add(c,b,item['id']);da,db=payload(c,a),payload(c,b)
    with ThreadPoolExecutor(max_workers=2)as pool:
        responses=list(pool.map(lambda args:c.post(P+'/checkout',headers=args[0],json=args[1]),[(a,da),(b,db)]))
    assert sorted(r.status_code for r in responses)==[201,409]
    assert c.get(P+'/products/'+str(item['id']),headers=admin).json()['stock']==0
    assert sum(len(c.get(P+'/cart',headers=h).json()['items'])for h in [a,b])==1

def test_v1_database_upgrade_preserves_history_and_generation(tmp_path,monkeypatch):
    import sqlite3
    from app.modules.practice_lab import store
    from app.core.auth import hash_password
    monkeypatch.setenv('PERSONAL_WORKSPACE_DATA_DIR',str(tmp_path));tenant=store.tenant_id('legacy');path=store.root()/(tenant+'.sqlite3');conn=sqlite3.connect(path)
    conn.executescript('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT,role TEXT);CREATE TABLE products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE,name TEXT,price_cents INTEGER,stock INTEGER,version INTEGER DEFAULT 1);CREATE TABLE orders(id TEXT PRIMARY KEY,user_id INTEGER,product_id INTEGER,quantity INTEGER,unit_price_cents INTEGER,total_cents INTEGER,status TEXT,request_key TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);')
    conn.execute("INSERT INTO meta VALUES('generation','legacy-generation')");conn.execute("INSERT INTO users VALUES(1,'lab_admin',?,'admin')",(hash_password('Practice123!'),));conn.execute("INSERT INTO users VALUES(2,'learner',?,'customer')",(hash_password('Practice123!'),));conn.execute("INSERT INTO products VALUES(40,'OLD-SKU','原有商品',1234,7,9)");conn.execute("INSERT INTO orders(id,user_id,product_id,quantity,unit_price_cents,total_cents,status,request_key) VALUES('old-order',2,40,1,1234,1234,'created','old-key')");conn.commit();conn.close()
    store.initialize(tenant);conn=store.connect(tenant)
    try:
        assert store.generation(conn)=='legacy-generation'
        row=conn.execute('SELECT * FROM products WHERE id=40').fetchone();assert row['stock']==7 and row['version']==9
        assert conn.execute("SELECT count(*) FROM orders WHERE id='old-order'").fetchone()[0]==1
    finally:conn.close()
    assert path.with_name(tenant+'.pre-v2.sqlite3').is_file()


def test_multi_item_failure_rolls_back_all_inventory_and_events(env):
    c=env.client;admin=login(env);a=login(env,username='learner');b=login(env,username='buyer_two')
    first=product(env,admin,4);last=product(env,admin,1)
    add(c,a,first['id'],2);add(c,a,last['id']);data=payload(c,a)
    add(c,b,last['id']);checkout(c,b)
    before=c.get(P+'/inventory',headers=admin).json()
    assert c.post(P+'/checkout',headers=a,json=data).status_code==409
    after=c.get(P+'/inventory',headers=admin).json()
    assert before==after
    assert c.get(P+'/orders',headers=a).json()==[]
    assert len(c.get(P+'/cart',headers=a).json()['items'])==2


def test_addresses_refund_rejection_inactive_products_and_reset(env):
    c=env.client;admin=login(env);a=login(env,username='learner');item=product(env,admin,4)
    original=c.get(P+'/addresses',headers=a).json()[0]
    body={'recipient':'测试地址','phone':'19900000000','region':'测试省市','detail':'自动化练习地址','is_default':True}
    created=c.post(P+'/addresses',headers=a,json=body).json()
    addresses=c.get(P+'/addresses',headers=a).json();assert sum(r['is_default']for r in addresses)==1
    assert c.put(P+'/addresses/'+str(original['id']),headers=a,json={**body,'version':original['version']}).status_code==409
    add(c,a,item['id']);quote=payload(c,a)
    updated=c.put(P+'/addresses/'+str(created['id']),headers=a,json={**body,'detail':'已变更的练习地址','version':created['version']});assert updated.status_code==200
    assert c.post(P+'/checkout',headers=a,json=quote).status_code==409
    order=checkout(c,a);c.post(P+'/orders/'+order['id']+'/pay',headers=a)
    c.post(P+'/orders/'+order['id']+'/refund',headers=a,json={'reason':'验证退款驳回流程'})
    assert c.post(P+'/orders/'+order['id']+'/refund-decision',headers=admin,json={'approve':False,'note':'申请信息待补充'}).json()['status']=='paid'
    assert c.get(P+'/products/'+str(item['id']),headers=a).json()['stock']==3
    c.post(P+'/orders/'+order['id']+'/refund',headers=a,json={'reason':'补充材料后再次申请'})
    assert c.post(P+'/orders/'+order['id']+'/refund-decision',headers=admin,json={'approve':True,'note':'未发货全额退款'}).json()['status']=='refunded'
    assert c.get(P+'/products/'+str(item['id']),headers=a).json()['stock']==4
    add(c,a,item['id']);quote=payload(c,a);current=c.get(P+'/products/'+str(item['id']),headers=admin).json()
    edit={k:current[k]for k in ['name','category','description','price_cents','version']};edit['status']='inactive'
    assert c.put(P+'/products/'+str(item['id']),headers=admin,json=edit).status_code==200
    assert c.post(P+'/checkout',headers=a,json=quote).status_code==409
    assert c.get(P+'/products/'+str(item['id']),headers=a).status_code==404
    assert c.post('/api/v1/practice-lab/reset',headers=env.headers['alice'],json={'confirmation':'重置练习数据'}).status_code==200
    assert c.get(P+'/cart',headers=a).status_code==401
    fresh=login(env,username='learner');assert c.get(P+'/cart',headers=fresh).json()['items']==[]
    assert c.get(P+'/orders',headers=fresh).json()==[]
    assert len(c.get(P+'/addresses',headers=fresh).json())==1
    assert c.get(P+'/inventory',headers=login(env)).json()['movements']==[]
