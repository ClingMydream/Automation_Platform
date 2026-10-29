"""Complete demo commerce workflow. Payments and logistics are simulated locally."""
import hashlib,json,sqlite3
from uuid import uuid4
from typing import Literal
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field
from .router import router,lab_user,admin,audit,valid_generation
from . import store

class Model(BaseModel):
    model_config={'extra':'forbid'}
class ProductEdit(Model):
    name:str=Field(min_length=1,max_length=160)
    category:Literal['办公文具','桌面数码','出行配件','生活收纳']
    description:str=Field(default='',max_length=2000)
    price_cents:int=Field(gt=0,le=10000000,strict=True)
    status:Literal['active','inactive']='active'
    version:int=Field(ge=1,strict=True)
class CartInput(Model):
    product_id:int=Field(gt=0,strict=True)
    quantity:int=Field(ge=1,le=99,strict=True)
class AddressInput(Model):
    recipient:str=Field(min_length=1,max_length=40)
    phone:str=Field(pattern=r'^1[3-9]\d{9}$')
    region:str=Field(min_length=2,max_length=100)
    detail:str=Field(min_length=3,max_length=200)
    is_default:bool=False
class AddressEdit(AddressInput):version:int=Field(ge=1,strict=True)
class Checkout(Model):
    address_id:int=Field(gt=0,strict=True)
    address_version:int=Field(ge=1,strict=True)
    cart_revision:int=Field(ge=1,strict=True)
    quote_hash:str=Field(pattern=r'^[a-f0-9]{64}$')
    request_key:str=Field(min_length=8,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    remark:str=Field(default='',max_length=300)
class Receipt(Model):
    quantity:int=Field(gt=0,le=10000,strict=True)
    reason:str=Field(min_length=2,max_length=200)
    version:int=Field(ge=1,strict=True)
    request_key:str=Field(min_length=8,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
class Shipment(Model):tracking_number:str=Field(pattern=r'^[A-Za-z0-9-]{8,40}$')
class Refund(Model):reason:str=Field(min_length=5,max_length=500)
class RefundDecision(Model):
    approve:bool
    return_received:bool=False
    note:str=Field(min_length=2,max_length=300)

def context(user:dict=Depends(lab_user)):
    conn=store.connect(user['tenant'])
    try:row=conn.execute("SELECT value FROM meta WHERE key='commerce_generation'").fetchone();ready=bool(row and row['value']==user['generation'])
    finally:conn.close()
    if not ready:store.initialize(user['tenant'])
    return user

def customer(user):
    if user['role']!='customer':raise HTTPException(403,'该操作仅供练习客户使用')
def operator(user):
    if user['role']not in {'admin','warehouse'}:raise HTTPException(403,'需要仓库或管理员权限')
def clean(values,keys):
    for key in keys:
        values[key]=values[key].strip()
        if not values[key]:raise HTTPException(422,'必填内容不能只有空格')
    return values

def movement(conn,user,product,delta,reason,reference=''):
    balance=conn.execute('SELECT stock FROM products WHERE id=?',(product,)).fetchone()['stock']
    conn.execute('INSERT INTO inventory_movements(product_id,actor,delta,balance,reason,reference) VALUES(?,?,?,?,?,?)',(product,user['username'],delta,balance,reason,reference))
def event(conn,user,order,action,description):
    conn.execute('INSERT INTO order_events(order_id,actor,action,description) VALUES(?,?,?,?)',(order,user['username'],action,description));audit(conn,user,action,order)
def owned_order(conn,user,identifier):
    row=conn.execute('SELECT * FROM commerce_orders WHERE id=?',(identifier,)).fetchone()
    if not row or user['role']=='customer'and row['user_id']!=user['id']:raise HTTPException(404,'订单不存在')
    return row

def detail(conn,row):
    result=dict(row);result['address']=json.loads(result.pop('address_json'));result.pop('request_fingerprint',None)
    result['items']=[dict(item)for item in conn.execute('SELECT * FROM commerce_order_items WHERE order_id=? ORDER BY id',(row['id'],))]
    result['events']=[dict(item)for item in conn.execute('SELECT * FROM order_events WHERE order_id=? ORDER BY id',(row['id'],))]
    return result

def cart_data(conn,user):
    revision=conn.execute('SELECT revision FROM shopping_carts WHERE user_id=?',(user['id'],)).fetchone()
    items=[dict(row)for row in conn.execute('SELECT p.*,c.quantity FROM cart_items c JOIN products p ON p.id=c.product_id WHERE c.user_id=? ORDER BY p.id',(user['id'],))]
    subtotal=sum(row['price_cents']*row['quantity']for row in items);shipping=0 if not items or subtotal>=19900 else 500
    quote=hashlib.sha256(json.dumps([(row['id'],row['quantity'],row['price_cents'],row['status'])for row in items],ensure_ascii=False).encode()).hexdigest()
    return {'revision':revision['revision']if revision else 1,'items':items,'subtotal_cents':subtotal,'shipping_cents':shipping,'total_cents':subtotal+shipping,'quote_hash':quote}
def touch_cart(conn,user):
    conn.execute('INSERT INTO shopping_carts(user_id,revision) VALUES(?,2) ON CONFLICT(user_id) DO UPDATE SET revision=revision+1',(user['id'],))

@router.get('/commerce/catalog')
def catalog(q:str='',category:str='',availability:str='all',user:dict=Depends(context)):
    conn=store.connect(user['tenant'])
    try:
        sql='SELECT * FROM products WHERE (instr(lower(name),lower(?))>0 OR instr(lower(sku),lower(?))>0)';params=[q,q]
        if category:sql+=' AND category=?';params.append(category)
        if user['role']=='customer':sql+=" AND status='active'"
        if availability=='in_stock':sql+=' AND stock>0'
        elif availability=='out_of_stock':sql+=' AND stock=0'
        return {'items':[dict(row)for row in conn.execute(sql+' ORDER BY id DESC',params)],'categories':store.CATEGORIES}
    finally:conn.close()

@router.get('/commerce/products/{product_id}')
def product_detail(product_id:int,user:dict=Depends(context)):
    conn=store.connect(user['tenant'])
    try:
        row=conn.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone()
        if not row or user['role']=='customer'and row['status']!='active':raise HTTPException(404,'商品不存在或已下架')
        return dict(row)
    finally:conn.close()

@router.put('/commerce/products/{product_id}')
def edit_product(product_id:int,payload:ProductEdit,user:dict=Depends(context)):
    admin(user);values=clean(payload.model_dump(),['name'])
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user)
        if not conn.execute('SELECT id FROM products WHERE id=?',(product_id,)).fetchone():raise HTTPException(404,'商品不存在')
        r=conn.execute('UPDATE products SET name=?,category=?,description=?,price_cents=?,status=?,version=version+1 WHERE id=? AND version=?',(values['name'],payload.category,payload.description,payload.price_cents,payload.status,product_id,payload.version))
        if r.rowcount!=1:raise HTTPException(409,'商品版本已变化，请重新读取后编辑')
        audit(conn,user,'edit_product',str(product_id));return dict(conn.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone())

@router.get('/commerce/cart')
def cart(user:dict=Depends(context)):
    customer(user);conn=store.connect(user['tenant'])
    try:return cart_data(conn,user)
    finally:conn.close()

@router.put('/commerce/cart/items')
def put_cart(payload:CartInput,user:dict=Depends(context)):
    customer(user)
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);item=conn.execute('SELECT * FROM products WHERE id=?',(payload.product_id,)).fetchone()
        if not item or item['status']!='active':raise HTTPException(404,'商品不存在或已下架')
        if payload.quantity>item['stock']:raise HTTPException(409,'当前可用库存不足')
        if not conn.execute('SELECT 1 FROM cart_items WHERE user_id=? AND product_id=?',(user['id'],item['id'])).fetchone()and conn.execute('SELECT count(*) FROM cart_items WHERE user_id=?',(user['id'],)).fetchone()[0]>=50:raise HTTPException(422,'购物车最多50种商品')
        conn.execute('INSERT INTO cart_items(user_id,product_id,quantity) VALUES(?,?,?) ON CONFLICT(user_id,product_id) DO UPDATE SET quantity=excluded.quantity',(user['id'],item['id'],payload.quantity));touch_cart(conn,user);return cart_data(conn,user)

@router.delete('/commerce/cart/items/{product_id}')
def remove_cart(product_id:int,user:dict=Depends(context)):
    customer(user)
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);conn.execute('DELETE FROM cart_items WHERE user_id=? AND product_id=?',(user['id'],product_id));touch_cart(conn,user);return cart_data(conn,user)

@router.get('/commerce/addresses')
def addresses(user:dict=Depends(context)):
    customer(user);conn=store.connect(user['tenant'])
    try:return [dict(row)for row in conn.execute('SELECT * FROM addresses WHERE user_id=? ORDER BY is_default DESC,id DESC',(user['id'],))]
    finally:conn.close()

@router.post('/commerce/addresses',status_code=201)
def create_address(payload:AddressInput,user:dict=Depends(context)):
    customer(user);values=clean(payload.model_dump(),['recipient','region','detail'])
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user)
        count=conn.execute('SELECT count(*) FROM addresses WHERE user_id=?',(user['id'],)).fetchone()[0]
        if count>=20:raise HTTPException(422,'最多保存20个地址')
        default=payload.is_default or count==0
        if default:conn.execute('UPDATE addresses SET is_default=0,version=version+1 WHERE user_id=?',(user['id'],))
        r=conn.execute('INSERT INTO addresses(user_id,recipient,phone,region,detail,is_default) VALUES(?,?,?,?,?,?)',(user['id'],values['recipient'],payload.phone,values['region'],values['detail'],int(default)))
        return dict(conn.execute('SELECT * FROM addresses WHERE id=?',(r.lastrowid,)).fetchone())

@router.put('/commerce/addresses/{address_id}')
def edit_address(address_id:int,payload:AddressEdit,user:dict=Depends(context)):
    customer(user);values=clean(payload.model_dump(),['recipient','region','detail'])
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);row=conn.execute('SELECT * FROM addresses WHERE id=? AND user_id=?',(address_id,user['id'])).fetchone()
        if not row:raise HTTPException(404,'地址不存在')
        if row['version']!=payload.version:raise HTTPException(409,'地址已被修改，请重新读取')
        default=payload.is_default or bool(row['is_default'])
        if default:conn.execute('UPDATE addresses SET is_default=0,version=version+1 WHERE user_id=? AND id!=?',(user['id'],address_id))
        conn.execute('UPDATE addresses SET recipient=?,phone=?,region=?,detail=?,is_default=?,version=version+1 WHERE id=?',(values['recipient'],payload.phone,values['region'],values['detail'],int(default),address_id));return dict(conn.execute('SELECT * FROM addresses WHERE id=?',(address_id,)).fetchone())

@router.delete('/commerce/addresses/{address_id}')
def delete_address(address_id:int,user:dict=Depends(context)):
    customer(user)
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);row=conn.execute('SELECT * FROM addresses WHERE id=? AND user_id=?',(address_id,user['id'])).fetchone()
        if not row:raise HTTPException(404,'地址不存在')
        conn.execute('DELETE FROM addresses WHERE id=?',(address_id,))
        if row['is_default']:conn.execute('UPDATE addresses SET is_default=1,version=version+1 WHERE id=(SELECT id FROM addresses WHERE user_id=? ORDER BY id LIMIT 1)',(user['id'],))
        return {'ok':True}

@router.post('/commerce/checkout',status_code=201)
def checkout(payload:Checkout,user:dict=Depends(context)):
    customer(user);fingerprint=hashlib.sha256(json.dumps(payload.model_dump(exclude={'request_key'}),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);old=conn.execute('SELECT * FROM commerce_orders WHERE user_id=? AND request_key=?',(user['id'],payload.request_key)).fetchone()
        if old:
            if old['request_fingerprint']!=fingerprint:raise HTTPException(409,'同一提交编号不能用于不同结算内容')
            return detail(conn,old)
        data=cart_data(conn,user)
        if not data['items']:raise HTTPException(422,'购物车为空')
        if data['revision']!=payload.cart_revision or data['quote_hash']!=payload.quote_hash:raise HTTPException(409,'购物车或商品报价已变化，请重新确认结算')
        address=conn.execute('SELECT * FROM addresses WHERE id=? AND user_id=?',(payload.address_id,user['id'])).fetchone()
        if not address:raise HTTPException(404,'收货地址不存在')
        if address['version']!=payload.address_version:raise HTTPException(409,'收货地址已变化，请重新确认')
        identifier=uuid4().hex;number='CL'+identifier[:12].upper()
        conn.execute('INSERT INTO commerce_orders(id,number,user_id,status,subtotal_cents,shipping_cents,total_cents,address_json,remark,request_key,request_fingerprint) VALUES(?,?,?,\'pending_payment\',?,?,?,?,?,?,?)',(identifier,number,user['id'],data['subtotal_cents'],data['shipping_cents'],data['total_cents'],json.dumps(dict(address),ensure_ascii=False),payload.remark,payload.request_key,fingerprint))
        for item in data['items']:
            if item['status']!='active':raise HTTPException(409,'购物车包含已下架商品')
            r=conn.execute('UPDATE products SET stock=stock-?,version=version+1 WHERE id=? AND stock>=?',(item['quantity'],item['id'],item['quantity']))
            if r.rowcount!=1:raise HTTPException(409,'库存不足，请重新确认购物车')
            conn.execute('INSERT INTO commerce_order_items(order_id,product_id,sku,name,unit_price_cents,quantity,total_cents) VALUES(?,?,?,?,?,?,?)',(identifier,item['id'],item['sku'],item['name'],item['price_cents'],item['quantity'],item['price_cents']*item['quantity']))
            movement(conn,user,item['id'],-item['quantity'],'订单预占',number)
        conn.execute('DELETE FROM cart_items WHERE user_id=?',(user['id'],));touch_cart(conn,user);event(conn,user,identifier,'checkout','创建订单并预占库存')
        return detail(conn,conn.execute('SELECT * FROM commerce_orders WHERE id=?',(identifier,)).fetchone())

@router.get('/commerce/orders')
def list_orders(q:str='',status:str='',user:dict=Depends(context)):
    conn=store.connect(user['tenant'])
    try:
        sql='SELECT o.*,u.username FROM commerce_orders o LEFT JOIN users u ON u.id=o.user_id WHERE 1=1';params=[]
        if user['role']=='customer':sql+=' AND o.user_id=?';params.append(user['id'])
        if status:sql+=' AND o.status=?';params.append(status)
        if q:sql+=' AND (instr(lower(o.number),lower(?))>0 OR EXISTS(SELECT 1 FROM commerce_order_items i WHERE i.order_id=o.id AND (instr(lower(i.name),lower(?))>0 OR instr(lower(i.sku),lower(?))>0)))';params.extend([q,q,q])
        return [detail(conn,row)for row in conn.execute(sql+' ORDER BY o.created_at DESC,o.rowid DESC LIMIT 300',params).fetchall()]
    finally:conn.close()

@router.get('/commerce/orders/{identifier}')
def get_order(identifier:str,user:dict=Depends(context)):
    conn=store.connect(user['tenant'])
    try:return detail(conn,owned_order(conn,user,identifier))
    finally:conn.close()

def release_stock(conn,user,row,reason):
    for item in conn.execute('SELECT * FROM commerce_order_items WHERE order_id=?',(row['id'],)).fetchall():
        conn.execute('UPDATE products SET stock=stock+?,version=version+1 WHERE id=?',(item['quantity'],item['product_id']));movement(conn,user,item['product_id'],item['quantity'],reason,row['number'])

def transition(conn,user,row,status,action,description):
    conn.execute('UPDATE commerce_orders SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,row['id']));event(conn,user,row['id'],action,description)
    return detail(conn,conn.execute('SELECT * FROM commerce_orders WHERE id=?',(row['id'],)).fetchone())

@router.post('/commerce/orders/{identifier}/cancel')
def cancel_order(identifier:str,user:dict=Depends(context)):
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);row=owned_order(conn,user,identifier)
        if row['status']=='cancelled':return detail(conn,row)
        if row['status']!='pending_payment':raise HTTPException(409,'只有待付款订单可取消；已付款请走退款流程')
        release_stock(conn,user,row,'取消释放');return transition(conn,user,row,'cancelled','cancel_order','取消订单，库存已释放')

@router.post('/commerce/orders/{identifier}/pay')
def pay(identifier:str,user:dict=Depends(context)):
    customer(user)
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);row=owned_order(conn,user,identifier)
        if row['status']=='paid':return detail(conn,row)
        if row['status']!='pending_payment':raise HTTPException(409,'当前订单状态不能付款')
        return transition(conn,user,row,'paid','demo_payment','模拟付款成功，不产生真实扣款')

@router.post('/commerce/orders/{identifier}/ship')
def ship(identifier:str,payload:Shipment,user:dict=Depends(context)):
    operator(user)
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);row=owned_order(conn,user,identifier)
        if row['status']=='shipped'and row['tracking_number']==payload.tracking_number:return detail(conn,row)
        if row['status']!='paid':raise HTTPException(409,'只有已付款订单可发货')
        conn.execute('UPDATE commerce_orders SET tracking_number=? WHERE id=?',(payload.tracking_number,identifier));return transition(conn,user,row,'shipped','ship','模拟发货：'+payload.tracking_number)

@router.post('/commerce/orders/{identifier}/receive')
def receive(identifier:str,user:dict=Depends(context)):
    customer(user)
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);row=owned_order(conn,user,identifier)
        if row['status']=='completed':return detail(conn,row)
        if row['status']!='shipped':raise HTTPException(409,'只有已发货订单可确认收货')
        return transition(conn,user,row,'completed','receive','客户确认收货')

@router.post('/commerce/orders/{identifier}/refund')
def refund(identifier:str,payload:Refund,user:dict=Depends(context)):
    customer(user)
    if len(payload.reason.strip())<5:raise HTTPException(422,'请填写至少5字退款原因')
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);row=owned_order(conn,user,identifier)
        if row['status']=='refund_requested'and row['refund_reason']==payload.reason.strip():return detail(conn,row)
        if row['status']not in {'paid','completed'}:raise HTTPException(409,'仅待发货或已收货订单可申请退款；运输中请先确认收货')
        conn.execute('UPDATE commerce_orders SET refund_from=status,refund_reason=? WHERE id=?',(payload.reason.strip(),identifier));return transition(conn,user,row,'refund_requested','refund_request',payload.reason.strip())

@router.post('/commerce/orders/{identifier}/refund-decision')
def decide_refund(identifier:str,payload:RefundDecision,user:dict=Depends(context)):
    admin(user)
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);row=owned_order(conn,user,identifier)
        if row['status']=='refunded'and payload.approve:return detail(conn,row)
        if row['status']!='refund_requested':raise HTTPException(409,'订单当前没有待处理退款')
        if payload.approve:
            if row['refund_from']=='completed'and not payload.return_received:raise HTTPException(409,'请先确认退货已收到，再批准退款与回补库存')
            release_stock(conn,user,row,'退款回补');return transition(conn,user,row,'refunded','refund_approve','模拟退款通过：'+payload.note)
        return transition(conn,user,row,row['refund_from'],'refund_reject','退款驳回：'+payload.note)

@router.post('/commerce/inventory/{product_id}/receipt')
def receipt(product_id:int,payload:Receipt,user:dict=Depends(context)):
    operator(user)
    if not payload.reason.strip():raise HTTPException(422,'请填写入库原因')
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user);reference='receipt:'+payload.request_key
        existing=conn.execute('SELECT * FROM inventory_movements WHERE reference=?',(reference,)).fetchone()
        if existing:
            if existing['actor']!=user['username']or existing['product_id']!=product_id or existing['delta']!=payload.quantity or existing['reason']!=payload.reason.strip():raise HTTPException(409,'入库编号已用于其他内容')
            return dict(conn.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone())
        r=conn.execute('UPDATE products SET stock=stock+?,version=version+1 WHERE id=? AND version=?',(payload.quantity,product_id,payload.version))
        if r.rowcount!=1:raise HTTPException(409,'商品不存在或库存版本已变化，请重新读取')
        movement(conn,user,product_id,payload.quantity,payload.reason.strip(),reference);audit(conn,user,'inventory_receipt',reference);return dict(conn.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone())

@router.get('/commerce/inventory')
def inventory(user:dict=Depends(context)):
    operator(user);conn=store.connect(user['tenant'])
    try:
        items=[dict(row)for row in conn.execute("SELECT p.*,COALESCE((SELECT SUM(i.quantity) FROM commerce_order_items i JOIN commerce_orders o ON o.id=i.order_id WHERE i.product_id=p.id AND (o.status IN ('pending_payment','paid') OR o.status='refund_requested'AND o.refund_from='paid')),0)+COALESCE((SELECT SUM(quantity) FROM orders WHERE product_id=p.id AND status='created'),0) reserved FROM products p ORDER BY p.id DESC")]
        movements=[dict(row)for row in conn.execute('SELECT m.*,p.name,p.sku FROM inventory_movements m LEFT JOIN products p ON p.id=m.product_id ORDER BY m.id DESC LIMIT 300')]
        return {'items':items,'movements':movements}
    finally:conn.close()

@router.get('/commerce/dashboard')
def dashboard(user:dict=Depends(context)):
    conn=store.connect(user['tenant'])
    try:
        where=' WHERE user_id=?'if user['role']=='customer'else'';params=(user['id'],)if where else()
        counts={row['status']:row['count']for row in conn.execute('SELECT status,count(*) count FROM commerce_orders'+where+' GROUP BY status',params)}
        total=conn.execute("SELECT COALESCE(sum(total_cents),0) FROM commerce_orders"+where+(" AND "if where else' WHERE ')+"status IN ('paid','shipped','completed','refund_requested')",params).fetchone()[0]
        return {'orders':sum(counts.values()),'statuses':counts,'paid_cents':total,'products':conn.execute("SELECT count(*) FROM products WHERE status='active'").fetchone()[0],'low_stock':conn.execute('SELECT count(*) FROM products WHERE stock<=3').fetchone()[0],'scope':'自己的订单'if user['role']=='customer'else'个人练习空间全部订单'}
    finally:conn.close()

class ProductCreate(Model):
    sku:str=Field(min_length=1,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    name:str=Field(min_length=1,max_length=160)
    category:Literal['办公文具','桌面数码','出行配件','生活收纳']
    description:str=Field(default='',max_length=2000)
    price_cents:int=Field(gt=0,le=10000000,strict=True)
    stock:int=Field(ge=0,le=100000,strict=True)

@router.post('/commerce/products',status_code=201)
def create_commerce_product(payload:ProductCreate,user:dict=Depends(context)):
    admin(user);values=clean(payload.model_dump(),['name'])
    with store.transaction(user['tenant'])as conn:
        valid_generation(conn,user)
        try:r=conn.execute('INSERT INTO products(sku,name,category,description,price_cents,stock) VALUES(?,?,?,?,?,?)',(payload.sku,values['name'],payload.category,payload.description,payload.price_cents,payload.stock))
        except sqlite3.IntegrityError:raise HTTPException(409,'SKU 已存在')
        movement(conn,user,r.lastrowid,payload.stock,'商品初始库存');audit(conn,user,'create_product',payload.sku);return dict(conn.execute('SELECT * FROM products WHERE id=?',(r.lastrowid,)).fetchone())
