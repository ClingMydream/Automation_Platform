from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4
import sqlite3
import hashlib

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel, Field

from app.core.auth import AuthContext, require_menu, verify_password
from app.core.config import get_settings
from . import store
from sqlalchemy.orm import Session
from app.db import get_db

management = APIRouter(prefix='/v1/practice-lab', tags=['实践实验室'])
router = APIRouter(prefix='/practice/v1', tags=['订单库存练习 API'])
guard = require_menu('practice_lab')


class Credentials(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=200)


class ProductInput(BaseModel):
    sku: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    name: str = Field(min_length=1, max_length=160)
    price_cents: int = Field(gt=0, le=10000000, strict=True)
    stock: int = Field(ge=0, le=100000, strict=True)


class StockInput(BaseModel):
    stock: int = Field(ge=0, le=100000, strict=True)
    version: int = Field(ge=1, strict=True)


class OrderInput(BaseModel):
    product_id: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, le=100, strict=True)
    request_key: str = Field(min_length=8, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')


class ResetInput(BaseModel):
    confirmation: Literal['重置练习数据']


def issue_token(tenant, row, gen):
    return jwt.encode({'sub': f'practice:{tenant}:{row["id"]}', 'scope': 'practice', 'tenant': tenant,
        'uid': row['id'], 'generation': gen, 'exp': datetime.now(timezone.utc) + timedelta(hours=1)},
        practice_key(), algorithm='HS256')


def practice_key():
    return hashlib.sha256((get_settings().app_secret_key+':practice-lab-v1').encode()).hexdigest()


def lab_user(request: Request):
    try:
        authorization = request.headers.get('authorization', '')
        if not authorization.startswith('Bearer '):
            raise ValueError()
        data = jwt.decode(authorization[7:], practice_key(), algorithms=['HS256'])
        if data.get('scope') != 'practice':
            raise ValueError()
        conn = store.connect(data['tenant'])
        try:
            if data['generation'] != store.generation(conn):
                raise ValueError()
            user = conn.execute('SELECT id,username,role FROM users WHERE id=?', (data['uid'],)).fetchone()
            if not user:
                raise ValueError()
            return {**dict(user), 'tenant': data['tenant'], 'generation': data['generation']}
        finally:
            conn.close()
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, '练习会话已失效，请重新登录练习账号')


def admin(user):
    if user['role'] != 'admin':
        raise HTTPException(403, '仅练习管理员可以维护商品和库存')


def audit(conn, user, action, detail):
    conn.execute('INSERT INTO audit(actor,action,detail) VALUES(?,?,?)', (user['username'], action, detail))


def valid_generation(conn, user):
    if store.generation(conn) != user['generation']:
        raise HTTPException(401, '数据已重置，请重新登录')


@management.get('/status')
def status(user: AuthContext = Depends(guard)):
    tenant = store.tenant_id(user.username)
    store.initialize(tenant)
    conn = store.connect(tenant)
    try:
        return {'seed_version': store.SEED_VERSION, 'products': conn.execute('SELECT count(*) FROM products').fetchone()[0],
            'orders': conn.execute('SELECT count(*) FROM orders').fetchone()[0], 'database': '个人独立 SQLite · 与平台数据库隔离',
            'accounts': [{'username': 'lab_admin', 'role': 'admin'}, {'username': 'learner', 'role': 'customer'}],
            'demo_password': store.DEMO_PASSWORD, 'docs_url': '/api/practice/docs'}
    finally:
        conn.close()


@management.post('/login')
def login(payload: Credentials, user: AuthContext = Depends(guard)):
    tenant = store.tenant_id(user.username)
    store.initialize(tenant)
    conn = store.connect(tenant)
    try:
        row = conn.execute('SELECT * FROM users WHERE username=?', (payload.username,)).fetchone()
        if not row or not verify_password(payload.password, row['password_hash']):
            raise HTTPException(401, '练习账号或密码错误')
        return {'token': issue_token(tenant, row, store.generation(conn)), 'username': row['username'], 'role': row['role']}
    finally:
        conn.close()


@management.post('/reset')
def reset(payload: ResetInput, user: AuthContext = Depends(guard), db: Session = Depends(get_db)):
    from .execution import PracticeRun
    from sqlalchemy import select
    if db.scalar(select(PracticeRun).where(PracticeRun.owner==user.username,PracticeRun.status.in_(['queued','running']))):
        raise HTTPException(409, '请先停止或完成当前测试，再重置练习数据')
    tenant = store.tenant_id(user.username)
    store.initialize(tenant)
    store.reset(tenant)
    return {'ok': True, 'message': '仅重置了你的练习数据库，原练习会话已失效'}


@router.get('/products')
def products(q: str = '', user: dict = Depends(lab_user)):
    conn = store.connect(user['tenant'])
    try:
        return [dict(row) for row in conn.execute('SELECT * FROM products WHERE instr(lower(name),lower(?))>0 OR instr(lower(sku),lower(?))>0 ORDER BY id DESC', (q, q))]
    finally:
        conn.close()


@router.post('/products', status_code=201)
def create_product(payload: ProductInput, user: dict = Depends(lab_user)):
    admin(user)
    if not payload.name.strip():
        raise HTTPException(422, '商品名称不能为空')
    with store.transaction(user['tenant']) as conn:
        valid_generation(conn, user)
        try:
            cursor = conn.execute('INSERT INTO products(sku,name,price_cents,stock) VALUES(?,?,?,?)', (payload.sku, payload.name.strip(), payload.price_cents, payload.stock))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'SKU 已存在')
        audit(conn, user, 'create_product', payload.sku)
        return dict(conn.execute('SELECT * FROM products WHERE id=?', (cursor.lastrowid,)).fetchone())


@router.put('/products/{product_id}/stock')
def set_stock(product_id: int, payload: StockInput, user: dict = Depends(lab_user)):
    admin(user)
    with store.transaction(user['tenant']) as conn:
        valid_generation(conn, user)
        if not conn.execute('SELECT id FROM products WHERE id=?', (product_id,)).fetchone():
            raise HTTPException(404, '商品不存在')
        result = conn.execute('UPDATE products SET stock=?,version=version+1 WHERE id=? AND version=?', (payload.stock, product_id, payload.version))
        if result.rowcount != 1:
            raise HTTPException(409, '库存已变化，请刷新后重试')
        audit(conn, user, 'set_stock', f'{product_id}: {payload.stock}')
        return dict(conn.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone())


@router.post('/orders', status_code=201)
def order(payload: OrderInput, user: dict = Depends(lab_user)):
    with store.transaction(user['tenant']) as conn:
        valid_generation(conn, user)
        existing = conn.execute('SELECT * FROM orders WHERE user_id=? AND request_key=?', (user['id'], payload.request_key)).fetchone()
        if existing:
            if existing['product_id'] != payload.product_id or existing['quantity'] != payload.quantity:
                raise HTTPException(409, '同一幂等编号不能提交不同订单')
            return dict(existing)
        product = conn.execute('SELECT * FROM products WHERE id=?', (payload.product_id,)).fetchone()
        if not product:
            raise HTTPException(404, '商品不存在')
        result = conn.execute('UPDATE products SET stock=stock-?,version=version+1 WHERE id=? AND stock>=?', (payload.quantity, payload.product_id, payload.quantity))
        if result.rowcount != 1:
            raise HTTPException(409, '库存不足')
        identifier = uuid4().hex
        conn.execute('INSERT INTO orders(id,user_id,product_id,quantity,unit_price_cents,total_cents,status,request_key) VALUES(?,?,?,?,?,?,?,?)',
            (identifier, user['id'], payload.product_id, payload.quantity, product['price_cents'], product['price_cents']*payload.quantity, 'created', payload.request_key))
        audit(conn, user, 'create_order', identifier)
        return dict(conn.execute('SELECT * FROM orders WHERE id=?', (identifier,)).fetchone())


@router.get('/orders')
def orders(user: dict = Depends(lab_user)):
    conn = store.connect(user['tenant'])
    try:
        sql = 'SELECT o.*,p.name AS product_name FROM orders o JOIN products p ON p.id=o.product_id'
        params = ()
        if user['role'] != 'admin':
            sql += ' WHERE user_id=?'; params = (user['id'],)
        return [dict(row) for row in conn.execute(sql+' ORDER BY created_at DESC,id DESC LIMIT 500', params)]
    finally:
        conn.close()


@router.post('/orders/{order_id}/cancel')
def cancel(order_id: str, user: dict = Depends(lab_user)):
    with store.transaction(user['tenant']) as conn:
        valid_generation(conn, user)
        row = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
        if not row or (row['user_id'] != user['id'] and user['role'] != 'admin'):
            raise HTTPException(404, '订单不存在')
        if row['status'] == 'created':
            conn.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
            conn.execute('UPDATE products SET stock=stock+?,version=version+1 WHERE id=?', (row['quantity'], row['product_id']))
            audit(conn, user, 'cancel_order', order_id)
        return dict(conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone())


@router.get('/audit')
def logs(user: dict = Depends(lab_user)):
    admin(user)
    conn = store.connect(user['tenant'])
    try:
        return [dict(row) for row in conn.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 200')]
    finally:
        conn.close()


@management.get('/project-guide')
def guide(user: AuthContext = Depends(guard)):
    return {'business': ['登录练习账号', '查询商品与库存', '提交幂等订单', '查看订单', '取消订单并恢复库存'],
        'assertions': ['price_cents 使用整数分', '订单不能超卖', '重复请求不重复扣库存', '重复取消不重复恢复', '普通用户无法维护库存'],
        'tables': ['users', 'products', 'orders', 'audit', 'meta'], 'seed_version': store.SEED_VERSION}
