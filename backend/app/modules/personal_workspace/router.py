"""Account-owned notes, reminders and tasks. No shared global learning state."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.auth import AuthContext, get_current_user
from app.db import Base, get_db


class WorkspaceRecord(Base):
    __tablename__ = 'personal_workspace_records'
    __table_args__ = (UniqueConstraint('owner','client_request_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(20), default='open')
    tags: Mapped[list] = mapped_column(JSON, default=list)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    client_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RecordInput(BaseModel):
    kind: Literal['task', 'memo', 'note']
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default='', max_length=100000)
    status: Literal['open', 'doing', 'done'] = 'open'
    tags: list[str] = Field(default_factory=list, max_length=20)
    due_at: datetime | None = None
    client_request_id: str | None = Field(default=None,min_length=8,max_length=64)


class RecordUpdate(RecordInput):
    revision: int = Field(ge=1)


router = APIRouter(prefix='/v1/personal-workspace', tags=['个人工作空间'])


def serialized(item):
    return {column.name: getattr(item, column.name) for column in item.__table__.columns if column.name != 'owner'}


def owned(db, user, record_id):
    item = db.scalar(select(WorkspaceRecord).where(WorkspaceRecord.id == record_id, WorkspaceRecord.owner == user.username))
    if item is None:
        raise HTTPException(404, '记录不存在')
    return item


def values(payload):
    data = payload.model_dump(exclude={'revision'})
    data['title'] = data['title'].strip()
    if not data['title']:
        raise HTTPException(422, '标题不能为空')
    if any(len(tag) > 40 for tag in data['tags']):
        raise HTTPException(422, '标签不能超过40个字符')
    data['tags'] = list(dict.fromkeys(tag.strip() for tag in data['tags'] if tag.strip()))
    if data['due_at'] and data['due_at'].tzinfo:
        from datetime import timezone
        data['due_at'] = data['due_at'].astimezone(timezone.utc).replace(tzinfo=None)
    return data


@router.get('/records')
def records(kind: Literal['task', 'memo', 'note'] | None = None, q: str = '', trash: bool = False,
            user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db),
            limit: int = Query(500, ge=1, le=1000), offset: int = Query(0, ge=0)):
    statement = select(WorkspaceRecord).where(WorkspaceRecord.owner == user.username)
    statement = statement.where(WorkspaceRecord.deleted_at.is_not(None) if trash else WorkspaceRecord.deleted_at.is_(None))
    if kind:
        statement = statement.where(WorkspaceRecord.kind == kind)
    if q:
        statement = statement.where(WorkspaceRecord.title.contains(q, autoescape=True) | WorkspaceRecord.content.contains(q, autoescape=True))
    # Direct service callers may omit FastAPI's query injection.
    limit = limit if isinstance(limit, int) else 500
    offset = offset if isinstance(offset, int) else 0
    return [serialized(item) for item in db.scalars(statement.order_by(WorkspaceRecord.updated_at.desc(), WorkspaceRecord.id.desc()).limit(limit).offset(offset)).all()]


@router.post('/records', status_code=201)
def create(payload: RecordInput, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.client_request_id:
        previous=db.scalar(select(WorkspaceRecord).where(WorkspaceRecord.owner==user.username,WorkspaceRecord.client_request_id==payload.client_request_id))
        if previous:
            if any(getattr(previous,key)!=value for key,value in values(payload).items()):raise HTTPException(409,'相同创建编号已有不同内容，请刷新核对，当前输入仍保留')
            return serialized(previous)
    item = WorkspaceRecord(owner=user.username, **values(payload))
    db.add(item)
    try:db.commit()
    except __import__('sqlalchemy').exc.IntegrityError:
        db.rollback();raise HTTPException(409,'记录已创建，请刷新核对后再操作')
    db.refresh(item)
    return serialized(item)


@router.get('/records/{record_id}')
def record(record_id:int,user:AuthContext=Depends(get_current_user),db:Session=Depends(get_db)):
    return serialized(owned(db,user,record_id))


@router.put('/records/{record_id}')
def save(record_id: int, payload: RecordUpdate, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    item = owned(db, user, record_id)
    if item.deleted_at:
        raise HTTPException(409, '记录已在回收站，请先恢复')
    result = db.execute(update(WorkspaceRecord).where(WorkspaceRecord.id == record_id, WorkspaceRecord.owner == user.username,
        WorkspaceRecord.revision == payload.revision, WorkspaceRecord.deleted_at.is_(None)).values(**values(payload),
        revision=payload.revision + 1, updated_at=datetime.utcnow()))
    if result.rowcount != 1:
        db.rollback(); raise HTTPException(409, '记录已被修改，请保留当前输入并重新加载')
    db.commit(); db.refresh(item)
    return serialized(item)


@router.delete('/records/{record_id}')
def remove(record_id: int, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    owned(db, user, record_id)
    db.execute(update(WorkspaceRecord).where(WorkspaceRecord.id==record_id, WorkspaceRecord.owner==user.username, WorkspaceRecord.deleted_at.is_(None)).values(deleted_at=datetime.utcnow(),revision=WorkspaceRecord.revision+1))
    db.commit()
    return {'ok': True}


@router.post('/records/{record_id}/restore')
def restore(record_id: int, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    item = owned(db, user, record_id)
    db.execute(update(WorkspaceRecord).where(WorkspaceRecord.id==record_id, WorkspaceRecord.owner==user.username, WorkspaceRecord.deleted_at.is_not(None)).values(deleted_at=None,revision=WorkspaceRecord.revision+1,updated_at=datetime.utcnow()))
    db.commit(); db.refresh(item)
    return serialized(item)
