"""Independent per-person business sandbox with an additive, versioned schema."""
import hashlib
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from uuid import uuid4
from fastapi import HTTPException
from app.core.auth import hash_password

SEED_VERSION='orders-inventory-v2'
DEMO_PASSWORD='Practice123!'
SCHEMA_LOCK=RLock()
CATEGORIES=['办公文具','桌面数码','出行配件','生活收纳']
EXTRA_PRODUCTS=[
 (4,'MOUSE-004','静音无线鼠标',6900,12,'桌面数码','双模连接，适合办公与日常使用。'),
 (5,'KEY-005','轻巧机械键盘',23900,8,'桌面数码','紧凑布局，带可调节支架。'),
 (6,'CUP-006','随行保温杯',9900,16,'出行配件','500ml容量，轻巧便携。'),
 (7,'PEN-007','中性笔套装',1900,40,'办公文具','六支装，适合书写与练习记录。'),
 (8,'BOX-008','桌面收纳盒',3900,18,'生活收纳','分区收纳，整理日常小物。'),
 (9,'CABLE-009','多口充电线',4900,3,'桌面数码','多接口设计，适合移动办公。'),
 (10,'MAT-010','柔软桌垫',5900,10,'办公文具','宽幅桌垫，提供平整书写区域。'),
 (11,'HOLDER-011','折叠支架',7900,0,'桌面数码','可调角度，支持折叠收纳。'),
 (12,'POUCH-012','旅行收纳包',8900,7,'生活收纳','多个分隔袋，便于整理物品。'),
]

def tenant_id(username):return hashlib.sha256(username.encode()).hexdigest()
def root():
    path=Path(os.getenv('PERSONAL_WORKSPACE_DATA_DIR','/var/lib/cling-personal-workspace')).resolve()/'practice'
    path.mkdir(parents=True,exist_ok=True);return path

def connect(tenant):
    if len(tenant)!=64 or any(c not in '0123456789abcdef'for c in tenant):raise HTTPException(401,'练习空间无效')
    path=root()/f'{tenant}.sqlite3';conn=sqlite3.connect(path,timeout=15);conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON');conn.execute('PRAGMA journal_mode=WAL')
    with SCHEMA_LOCK:
        existing={row['name']for row in conn.execute('PRAGMA table_info(products)')}
        if existing and 'category'not in existing:
            backup=root()/f'{tenant}.pre-v2.sqlite3'
            if not backup.exists():
                target=sqlite3.connect(backup)
                try:conn.backup(target)
                finally:target.close()
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE NOT NULL,name TEXT NOT NULL,price_cents INTEGER NOT NULL CHECK(price_cents>0),stock INTEGER NOT NULL CHECK(stock>=0),version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),product_id INTEGER NOT NULL REFERENCES products(id),quantity INTEGER NOT NULL CHECK(quantity>0),unit_price_cents INTEGER NOT NULL,total_cents INTEGER NOT NULL,status TEXT NOT NULL,request_key TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,request_key));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS addresses(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,recipient TEXT NOT NULL,phone TEXT NOT NULL,region TEXT NOT NULL,detail TEXT NOT NULL,is_default INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS shopping_carts(user_id INTEGER PRIMARY KEY,revision INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS cart_items(user_id INTEGER NOT NULL,product_id INTEGER NOT NULL,quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 99),PRIMARY KEY(user_id,product_id));
        CREATE TABLE IF NOT EXISTS commerce_orders(id TEXT PRIMARY KEY,number TEXT UNIQUE NOT NULL,user_id INTEGER NOT NULL,status TEXT NOT NULL,subtotal_cents INTEGER NOT NULL,shipping_cents INTEGER NOT NULL,total_cents INTEGER NOT NULL,address_json TEXT NOT NULL,remark TEXT NOT NULL DEFAULT '',request_key TEXT NOT NULL,request_fingerprint TEXT NOT NULL,refund_reason TEXT NOT NULL DEFAULT '',refund_from TEXT,tracking_number TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,request_key));
        CREATE TABLE IF NOT EXISTS commerce_order_items(id INTEGER PRIMARY KEY,order_id TEXT NOT NULL REFERENCES commerce_orders(id) ON DELETE CASCADE,product_id INTEGER NOT NULL,sku TEXT NOT NULL,name TEXT NOT NULL,unit_price_cents INTEGER NOT NULL,quantity INTEGER NOT NULL,total_cents INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS order_events(id INTEGER PRIMARY KEY,order_id TEXT NOT NULL REFERENCES commerce_orders(id) ON DELETE CASCADE,actor TEXT NOT NULL,action TEXT NOT NULL,description TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS inventory_movements(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL,actor TEXT NOT NULL,delta INTEGER NOT NULL,balance INTEGER NOT NULL,reason TEXT NOT NULL,reference TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS commerce_order_owner_time ON commerce_orders(user_id,created_at);
        CREATE INDEX IF NOT EXISTS commerce_order_status ON commerce_orders(status);
        ''')
        columns={row['name']for row in conn.execute('PRAGMA table_info(products)')}
        for name,definition in [('category',"TEXT NOT NULL DEFAULT '办公文具'"),('description',"TEXT NOT NULL DEFAULT ''"),('status',"TEXT NOT NULL DEFAULT 'active'")]:
            if name not in columns:conn.execute(f'ALTER TABLE products ADD COLUMN {name} {definition}')
        conn.commit()
    return conn

@contextmanager
def transaction(tenant):
    conn=connect(tenant)
    try:conn.execute('BEGIN IMMEDIATE');yield conn;conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()

def seed(conn):
    conn.executemany('INSERT INTO users(id,username,password_hash,role) VALUES(?,?,?,?)',[(1,'lab_admin',hash_password(DEMO_PASSWORD),'admin'),(2,'learner',hash_password(DEMO_PASSWORD),'customer')])
    conn.executemany('INSERT INTO products(id,sku,name,price_cents,stock,category,description) VALUES(?,?,?,?,?,?,?)',[(1,'NOTE-001','练习手账本',2900,20,'办公文具','记录学习过程、测试观察与灵感。'),(2,'LAMP-002','桌面阅读灯',12900,5,'桌面数码','多档亮度调节，为桌面提供柔和照明。'),(3,'BAG-003','轻便通勤包',8900,0,'出行配件','轻便分区，适合日常通勤。')])

def clear_commerce(conn):
    for table in ['order_events','commerce_order_items','commerce_orders','cart_items','shopping_carts','addresses','inventory_movements']:conn.execute(f'DELETE FROM {table}')

def upgrade(conn):
    gen=generation(conn);old=conn.execute("SELECT value FROM meta WHERE key='commerce_generation'").fetchone()
    if old and old['value']==gen:return
    # Old-version reset changes generation; do not revive stale v2 shopping data.
    if old:clear_commerce(conn)
    for username,role in [('warehouse','warehouse'),('buyer_two','customer'),('_auto_customer','customer'),('_auto_customer_two','customer')]:
        if not conn.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone():conn.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(username,hash_password(DEMO_PASSWORD),role))
    for sku,category,description in [('NOTE-001','办公文具','记录学习过程、测试观察与灵感。'),('LAMP-002','桌面数码','多档亮度调节，为桌面提供柔和照明。'),('BAG-003','出行配件','轻便分区，适合日常通勤。')]:
        conn.execute("UPDATE products SET category=?,description=? WHERE sku=? AND category='办公文具' AND description=''",(category,description,sku))
    for _,sku,name,price,stock,category,description in EXTRA_PRODUCTS:
        conn.execute('INSERT OR IGNORE INTO products(sku,name,price_cents,stock,category,description) VALUES(?,?,?,?,?,?)',(sku,name,price,stock,category,description))
    for row in conn.execute("SELECT id FROM users WHERE role='customer'").fetchall():
        if not conn.execute('SELECT id FROM addresses WHERE user_id=?',(row['id'],)).fetchone():conn.execute("INSERT INTO addresses(user_id,recipient,phone,region,detail,is_default) VALUES(?, '练习收件人','19900000000','测试省 / 练习市','自动化测试路1号',1)",(row['id'],))
    conn.execute("INSERT OR REPLACE INTO meta VALUES('seed_version',?)",(SEED_VERSION,));conn.execute("INSERT OR REPLACE INTO meta VALUES('commerce_generation',?)",(gen,))

def initialize(tenant):
    with transaction(tenant)as conn:
        if not conn.execute("SELECT value FROM meta WHERE key='generation'").fetchone():seed(conn);conn.execute("INSERT INTO meta VALUES('generation',?)",(uuid4().hex,))
        upgrade(conn)

def generation(conn):
    row=conn.execute("SELECT value FROM meta WHERE key='generation'").fetchone()
    if not row:raise HTTPException(401,'请先初始化练习空间')
    return row['value']

def reset(tenant):
    with transaction(tenant)as conn:
        clear_commerce(conn)
        for table in ['orders','products','users','audit']:conn.execute(f'DELETE FROM {table}')
        seed(conn);conn.execute("UPDATE meta SET value=? WHERE key='generation'",(uuid4().hex,));upgrade(conn)
        conn.execute("INSERT INTO audit(actor,action,detail) VALUES('workspace-owner','reset','恢复v2固定测试数据，旧会话失效')")
