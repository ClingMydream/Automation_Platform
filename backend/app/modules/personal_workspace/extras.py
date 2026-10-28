import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import Integer, String, DateTime, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.core.auth import AuthContext, get_current_user
from app.db import Base, get_db
from .router import router, owned


class Attachment(Base):
    __tablename__ = 'personal_workspace_attachments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(120), index=True)
    record_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(200))
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def attachment_root():
    path = Path(os.getenv('PERSONAL_WORKSPACE_DATA_DIR', '/var/lib/cling-personal-workspace')).resolve() / 'attachments'
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get('/records/{record_id}/attachments')
def attachments(record_id: int, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    owned(db, user, record_id)
    return [{'id': row.id, 'name': row.name, 'size': row.size} for row in db.scalars(select(Attachment).where(Attachment.owner == user.username, Attachment.record_id == record_id)).all()]


@router.post('/records/{record_id}/attachments', status_code=201)
async def upload(record_id: int, file: UploadFile = File(...), user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned(db, user, record_id)
    if record.deleted_at:
        raise HTTPException(409, '请先恢复记录')
    name = Path((file.filename or 'attachment').replace('\\', '/')).name[:200]
    if Path(name).suffix.lower() not in {'.png','.jpg','.jpeg','.webp','.pdf','.txt','.md','.csv','.json','.py','.zip'}:
        raise HTTPException(422, '支持图片、PDF、文本、代码和ZIP附件')
    content = await file.read(10*1024*1024+1)
    if len(content) > 10*1024*1024:
        raise HTTPException(413, '单个附件不能超过10MB')
    identifier = uuid4().hex
    path = attachment_root()/identifier
    path.write_bytes(content)
    try:
        row = Attachment(owner=user.username, record_id=record_id, name=name, stored_name=identifier, size=len(content))
        db.add(row); db.commit(); db.refresh(row)
    except Exception:
        path.unlink(missing_ok=True); raise
    return {'id': row.id, 'name': row.name, 'size': row.size}


@router.get('/attachments/{attachment_id}')
def download(attachment_id: int, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Attachment).where(Attachment.id == attachment_id, Attachment.owner == user.username))
    if not row:
        raise HTTPException(404, '附件不存在')
    record = owned(db, user, row.record_id)
    if record.deleted_at:
        raise HTTPException(404, '请先恢复笔记再下载附件')
    path = attachment_root()/row.stored_name
    if not path.is_file():
        raise HTTPException(404, '附件文件不存在')
    return FileResponse(path, filename=row.name, media_type='application/octet-stream', headers={'X-Content-Type-Options':'nosniff'})


@router.delete('/attachments/{attachment_id}')
def delete_attachment(attachment_id: int, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Attachment).where(Attachment.id == attachment_id, Attachment.owner == user.username))
    if not row:
        raise HTTPException(404, '附件不存在')
    path = attachment_root()/row.stored_name
    db.delete(row); db.commit(); path.unlink(missing_ok=True)
    return {'ok': True}
