from datetime import datetime, timedelta
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Integer, String, Text, DateTime, UniqueConstraint, select
from sqlalchemy.orm import Session, Mapped, mapped_column
from app.core.auth import AuthContext, get_current_user
from app.db import Base, get_db
from .router import router, WorkspaceRecord, serialized
from .curriculum import LESSONS


class LessonProgress(Base):
    __tablename__ = 'personal_learning_progress'
    __table_args__ = (UniqueConstraint('owner', 'lesson_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(120), index=True)
    lesson_id: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default='reading')
    evidence: Mapped[str] = mapped_column(Text, default='')
    note_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProgressInput(BaseModel):
    status: Literal['reading', 'practiced', 'verified']
    evidence: str = Field(default='', max_length=10000)
    note_id: int | None = None
    run_id: int | None = None


@router.get('/lessons')
def lessons(user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = {row.lesson_id: row for row in db.scalars(select(LessonProgress).where(LessonProgress.owner == user.username)).all()}
    return [{**lesson, 'progress': {name:getattr(rows[lesson['id']], name) for name in ['status','evidence','note_id','run_id']} if lesson['id'] in rows else None} for lesson in LESSONS]


@router.put('/lessons/{lesson_id}')
def save_progress(lesson_id: str, payload: ProgressInput, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = next((item for item in LESSONS if item['id'] == lesson_id), None)
    if not lesson:
        raise HTTPException(404, '学习任务不存在')
    if payload.note_id:
        note = db.scalar(select(WorkspaceRecord).where(WorkspaceRecord.id == payload.note_id, WorkspaceRecord.owner == user.username, WorkspaceRecord.kind == 'note', WorkspaceRecord.deleted_at.is_(None)))
        if not note:
            raise HTTPException(404, '关联笔记不存在')
    if payload.status in {'practiced','verified'} and len(payload.evidence.strip()) < 10:
        raise HTTPException(422, '请记录至少10字的练习过程或运行结果')
    if payload.status == 'verified':
        from app.modules.practice_lab.execution import PracticeRun
        run = db.scalar(select(PracticeRun).where(PracticeRun.id == payload.run_id, PracticeRun.owner == user.username, PracticeRun.status == 'passed'))
        if not lesson['suite'] or not run or run.suite != lesson['suite']:
            raise HTTPException(422, '已验证需要关联对应类型且通过的真实执行记录；基础任务使用已练习状态')
    row = db.scalar(select(LessonProgress).where(LessonProgress.owner == user.username, LessonProgress.lesson_id == lesson_id))
    if not row:
        row = LessonProgress(owner=user.username, lesson_id=lesson_id); db.add(row)
    for key,value in payload.model_dump().items():setattr(row,key,value)
    row.updated_at=datetime.utcnow();db.commit()
    return {'ok':True}


@router.get('/summary')
def summary(user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.modules.practice_lab.execution import PracticeRun
    active = select(WorkspaceRecord).where(WorkspaceRecord.owner == user.username, WorkspaceRecord.deleted_at.is_(None))
    tasks = db.scalars(active.where(WorkspaceRecord.kind=='task', WorkspaceRecord.status!='done').order_by(WorkspaceRecord.due_at.asc(),WorkspaceRecord.id.desc())).all()
    notes = db.scalars(active.where(WorkspaceRecord.kind=='note').order_by(WorkspaceRecord.updated_at.desc()).limit(3)).all()
    progress = db.scalar(select(LessonProgress).where(LessonProgress.owner==user.username).order_by(LessonProgress.updated_at.desc()))
    runs = db.scalars(select(PracticeRun).where(PracticeRun.owner==user.username).order_by(PracticeRun.id.desc()).limit(3)).all()
    reminders=db.scalars(active.where(WorkspaceRecord.kind.in_(['task','memo']),WorkspaceRecord.status!='done',WorkspaceRecord.due_at<=datetime.utcnow()+timedelta(hours=24)).order_by(WorkspaceRecord.due_at).limit(8)).all()
    return {'tasks':[serialized(row) for row in tasks[:12]], 'open_tasks':len(tasks), 'overdue':sum(bool(row.due_at and row.due_at < datetime.utcnow()) for row in tasks),
        'notes':[serialized(row) for row in notes], 'continue_lesson':progress.lesson_id if progress else LESSONS[0]['id'],
        'runs':[{'id':row.id,'suite':row.suite,'status':row.status} for row in runs], 'reminders':[serialized(row) for row in reminders]}
