"""Independent per-person SQLite business sandbox; transactions serialize inventory mutations."""
import hashlib
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from app.core.auth import hash_password

SEED_VERSION = 'orders-inventory-v1'
DEMO_PASSWORD = 'Practice123!'


def tenant_id(username):
    return hashlib.sha256(username.encode()).hexdigest()


def root():
    path = Path(os.getenv('PERSONAL_WORKSPACE_DATA_DIR', '/var/lib/cling-personal-workspace')).resolve() / 'practice'
    path.mkdir(parents=True, exist_ok=True)
    return path


def connect(tenant):
    if len(tenant) != 64 or any(c not in '0123456789abcdef' for c in tenant):
        raise HTTPException(401, '练习空间无效')
    conn = sqlite3.connect(root() / f'{tenant}.sqlite3', timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE NOT NULL,name TEXT NOT NULL,price_cents INTEGER NOT NULL CHECK(price_cents>0),stock INTEGER NOT NULL CHECK(stock>=0),version INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),product_id INTEGER NOT NULL REFERENCES products(id),quantity INTEGER NOT NULL CHECK(quantity>0),unit_price_cents INTEGER NOT NULL,total_cents INTEGER NOT NULL,status TEXT NOT NULL,request_key TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,request_key));
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    ''')
    return conn


@contextmanager
def transaction(tenant):
    conn = connect(tenant)
    try:
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def seed(conn):
    conn.executemany('INSERT INTO users(id,username,password_hash,role) VALUES(?,?,?,?)', [
        (1, 'lab_admin', hash_password(DEMO_PASSWORD), 'admin'),
        (2, 'learner', hash_password(DEMO_PASSWORD), 'customer'),
    ])
    conn.executemany('INSERT INTO products(id,sku,name,price_cents,stock) VALUES(?,?,?,?,?)', [
        (1, 'NOTE-001', '练习手账本', 2900, 20),
        (2, 'LAMP-002', '桌面阅读灯', 12900, 5),
        (3, 'BAG-003', '轻便通勤包', 8900, 0),
    ])


def initialize(tenant):
    with transaction(tenant) as conn:
        if not conn.execute("SELECT value FROM meta WHERE key='generation'").fetchone():
            seed(conn)
            conn.execute("INSERT INTO meta VALUES('generation',?)", (uuid4().hex,))
            conn.execute("INSERT INTO meta VALUES('seed_version',?)", (SEED_VERSION,))


def generation(conn):
    row = conn.execute("SELECT value FROM meta WHERE key='generation'").fetchone()
    if not row:
        raise HTTPException(401, '请先初始化练习空间')
    return row['value']


def reset(tenant):
    with transaction(tenant) as conn:
        for table in ['orders', 'products', 'users', 'audit']:
            conn.execute(f'DELETE FROM {table}')
        seed(conn)
        conn.execute("UPDATE meta SET value=? WHERE key='generation'", (uuid4().hex,))
        conn.execute("INSERT INTO audit(actor,action,detail) VALUES('workspace-owner','reset','恢复固定测试数据，旧会话失效')")
