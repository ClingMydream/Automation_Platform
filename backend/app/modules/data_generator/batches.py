"""Private, versioned saved phone batches. Additive table only."""
import json
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, JSON, DateTime, UniqueConstraint, select, update, cast, Text, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db import Base, get_db
from app.core.auth import AuthContext, require_menu
from .router import router

class SavedBatch(Base):
    __tablename__ = 'generated_phone_batches'
    __table_args__ = (UniqueConstraint('owner', 'request_id'),)
    id = Column(Integer, primary_key=True)
    owner = Column(String(191), nullable=False, index=True)
    request_id = Column(String(64), nullable=False)
    name = Column(String(120), nullable=False)
    remark = Column(String(2000), nullable=False, default='')
    rows = Column(JSON, nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class PhoneRow(BaseModel):
    phone: str = Field(pattern=r'^(?:1[3-9][0-9]{9}|000[0-9]{8}|TEST-PHONE-[A-F0-9]{32})$')
    remark: str = Field(default='', max_length=1000)

class BatchBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    remark: str = Field(default='', max_length=2000)
    rows: list[PhoneRow] = Field(min_length=1, max_length=100)
    request_id: str = Field(min_length=1, max_length=64)
    revision: int = Field(default=1, ge=1)

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError('批次名称不能为空')
        return value.strip()

    @field_validator('rows')
    @classmethod
    def unique_phones(cls, rows):
        if len({row.phone for row in rows}) != len(rows):
            raise ValueError('同批次号码不能重复')
        return rows

def result(batch):
    return {key: getattr(batch, key) for key in ('id', 'name', 'remark', 'rows', 'request_id', 'revision', 'updated_at')}

def owned(db, batch_id, auth):
    batch = db.scalar(select(SavedBatch).where(SavedBatch.id == batch_id, SavedBatch.owner == auth.username))
    if batch is None:
        raise HTTPException(404, '批次不存在')
    return batch

@router.get('/v1/tools/data-generator/batches')
def list_batches(q: str = Query('', max_length=100), page: int = Query(1, ge=1), db: Session = Depends(get_db), auth: AuthContext = Depends(require_menu('data_generator'))):
    conditions = [SavedBatch.owner == auth.username]
    if q:
        if db.bind.dialect.name == 'sqlite':
            row_term = json.dumps(q, ensure_ascii=True)[1:-1]
        else:
            row_term = q
        row_pattern = '%' + row_term.replace('/', '//').replace('%', '/%').replace('_', '/_') + '%'
        term = q.replace("/", "//").replace("%", "/%").replace("_", "/_")
        pattern = f"%{term}%"
        conditions.append(or_(SavedBatch.name.ilike(pattern, escape="/"), SavedBatch.remark.ilike(pattern, escape="/"), cast(SavedBatch.rows, Text).ilike(row_pattern, escape="/")))
    total = db.scalar(select(func.count()).select_from(SavedBatch).where(*conditions))
    batches = db.scalars(select(SavedBatch).where(*conditions).order_by(SavedBatch.updated_at.desc(), SavedBatch.id.desc()).offset((page-1)*10).limit(10)).all()
    return {'total': total, 'items': [result(b) for b in batches]}

@router.post('/v1/tools/data-generator/batches', status_code=201)
def create_batch(body: BatchBody, db: Session = Depends(get_db), auth: AuthContext = Depends(require_menu('data_generator'))):
    previous = db.scalar(select(SavedBatch).where(SavedBatch.owner == auth.username, SavedBatch.request_id == body.request_id))
    if previous:
        return result(previous)
    batch = SavedBatch(owner=auth.username, request_id=body.request_id, name=body.name, remark=body.remark, rows=[r.model_dump() for r in body.rows])
    db.add(batch)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        batch = db.scalar(select(SavedBatch).where(SavedBatch.owner == auth.username, SavedBatch.request_id == body.request_id))
        if batch is None:
            raise
    db.refresh(batch)
    return result(batch)

@router.get('/v1/tools/data-generator/batches/{batch_id}')
def read_batch(batch_id: int, db: Session = Depends(get_db), auth: AuthContext = Depends(require_menu('data_generator'))):
    return result(owned(db, batch_id, auth))

@router.put('/v1/tools/data-generator/batches/{batch_id}')
def edit_batch(batch_id: int, body: BatchBody, db: Session = Depends(get_db), auth: AuthContext = Depends(require_menu('data_generator'))):
    owned(db, batch_id, auth)
    changed = db.execute(update(SavedBatch).where(SavedBatch.id == batch_id, SavedBatch.owner == auth.username, SavedBatch.revision == body.revision).values(name=body.name, remark=body.remark, rows=[r.model_dump() for r in body.rows], revision=body.revision+1, updated_at=datetime.now(timezone.utc)))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, '批次已在其他窗口更新，请重新打开后编辑')
    db.commit()
    return result(owned(db, batch_id, auth))

@router.delete('/v1/tools/data-generator/batches/{batch_id}')
def delete_batch(batch_id: int, revision: int = Query(..., ge=1), db: Session = Depends(get_db), auth: AuthContext = Depends(require_menu('data_generator'))):
    from sqlalchemy import delete
    owned(db, batch_id, auth)
    changed = db.execute(delete(SavedBatch).where(SavedBatch.id == batch_id, SavedBatch.owner == auth.username, SavedBatch.revision == revision))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, '批次已更新，请刷新列表')
    db.commit()
    return {'deleted': True}
