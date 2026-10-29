"""Learning evidence is owned, attributable and checked against chapter goals."""
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Integer, String, Text, DateTime, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
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


class LearningNoteInput(ProgressInput):
    client_request_id: str = Field(min_length=8, max_length=64)


def lesson_for(identifier):
    lesson = next((item for item in LESSONS if item['id'] == identifier), None)
    if not lesson: raise HTTPException(404, '学习任务不存在')
    return lesson


def verification(lesson, run):
    if not lesson['suite'] or not run or run.suite != lesson['suite'] or run.status != 'passed': return False
    result = run.result or {}
    if lesson['suite'] == 'performance':
        metrics = result.get('performance') or {}
        try: return int(metrics.get('Request Count', 0)) > 0 and int(metrics.get('Failure Count', -1)) == 0
        except (ValueError, TypeError): return False
    passed = {case.get('name', '').split('[')[0] for case in result.get('tests', []) if case.get('status') == 'passed'}
    return bool(lesson['checks']) and all(check['name'] in passed for check in lesson['checks'])


def validate_progress(db, user, lesson, payload):
    from app.modules.practice_lab.execution import PracticeRun
    if payload.note_id:
        note = db.scalar(select(WorkspaceRecord).where(WorkspaceRecord.id == payload.note_id, WorkspaceRecord.owner == user.username, WorkspaceRecord.kind == 'note', WorkspaceRecord.deleted_at.is_(None)))
        if not note: raise HTTPException(404, '关联笔记不存在')
    run = None
    if payload.run_id is not None:
        run = db.scalar(select(PracticeRun).where(PracticeRun.id == payload.run_id, PracticeRun.owner == user.username))
        if not run or run.suite != lesson['suite']: raise HTTPException(422, '执行不存在或不属于本章对应的个人工程')
        if run.status in {'queued', 'running'}: raise HTTPException(422, '请等待执行结束后再关联结果')
    if payload.status in {'practiced', 'verified'} and len(payload.evidence.strip()) < 10:
        raise HTTPException(422, '请记录至少10字的练习过程或运行结果')
    if payload.status == 'verified' and not verification(lesson, run):
        raise HTTPException(422, '已验证需要自己的通过记录，并覆盖本章全部检查目标；基础任务使用已练习状态')
    return run


def progress_row(db, user, identifier):
    row = db.scalar(select(LessonProgress).where(LessonProgress.owner == user.username, LessonProgress.lesson_id == identifier))
    if not row:
        row = LessonProgress(owner=user.username, lesson_id=identifier)
        db.add(row)
    return row


def commit(db):
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '学习记录已发生变化，请刷新核对；当前输入仍保留')


def lesson_rows(db, user):
    from app.modules.practice_lab.execution import PracticeRun
    rows = {row.lesson_id: row for row in db.scalars(select(LessonProgress).where(LessonProgress.owner == user.username)).all()}
    notes = set(db.scalars(select(WorkspaceRecord.id).where(WorkspaceRecord.owner == user.username, WorkspaceRecord.kind == 'note', WorkspaceRecord.deleted_at.is_(None), WorkspaceRecord.id.in_([row.note_id for row in rows.values() if row.note_id]))).all())
    runs = {row.id: row for row in db.scalars(select(PracticeRun).where(PracticeRun.owner == user.username, PracticeRun.id.in_([row.run_id for row in rows.values() if row.run_id]))).all()}
    result = []
    for lesson in LESSONS:
        row = rows.get(lesson['id'])
        progress = {name: getattr(row, name) for name in ['status', 'evidence', 'note_id', 'run_id']} if row else None
        eligible = verification(lesson, runs.get(row.run_id)) if row else False
        completed = bool(row and row.note_id in notes and len(row.evidence.strip()) >= 10 and (row.status == 'verified' and eligible if lesson['suite'] else row.status == 'practiced'))
        result.append({**lesson, 'progress': progress, 'completed': completed, 'verification_eligible': eligible, 'note_available': bool(row and row.note_id in notes)})
    return result


@router.get('/lessons')
def lessons(user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    return lesson_rows(db, user)


@router.put('/lessons/{lesson_id}')
def save_progress(lesson_id: str, payload: ProgressInput, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = lesson_for(lesson_id)
    validate_progress(db, user, lesson, payload)
    row = progress_row(db, user, lesson_id)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    commit(db)
    return {'ok': True}


def note_content(lesson, payload, run):
    lines = [f"# {lesson['title']}", '', '学习状态：' + payload.status, '', '## 本章目标', lesson['goal'], '', '## 我的练习与心得', payload.evidence.strip(), '', '## 参考示例', f"```{lesson.get('language', 'python')}", lesson['example'], '```', '', '## 验证范围', lesson['verification_scope']]
    if run:
        lines += ['', '## 实际执行记录', f'执行 #{run.id} · 工程 {run.suite} · 状态 {run.status}', f'[查看本次结果](/?module=practice_lab&run={run.id}&lesson={lesson["id"]})']
        for case in (run.result or {}).get('tests', []): lines.append(f"- {case.get('name', '未命名检查')}：{case.get('status', 'unknown')}")
        metrics = (run.result or {}).get('performance')
        if metrics:
            for key, label in [('Request Count', '请求数'), ('Failure Count', '失败数'), ('Requests/s', 'RPS'), ('95%', 'P95（毫秒）')]: lines.append(f'- {label}：{metrics.get(key, "未提供")}')
    lines += ['', '## 返回学习章节', f'[继续本章](/?module=learning_route&lesson={lesson["id"]})']
    return '\n'.join(lines)


@router.post('/lessons/{lesson_id}/notebook', status_code=201)
def create_learning_note(lesson_id: str, payload: LearningNoteInput, user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = lesson_for(lesson_id)
    run = validate_progress(db, user, lesson, payload)
    if len(payload.evidence.strip()) < 10: raise HTTPException(422, '请先写下至少10字自己的观察或心得，再生成笔记')
    key = sha256(('learning-note:' + lesson_id + ':' + payload.client_request_id).encode()).hexdigest()
    content = note_content(lesson, payload, run)
    previous = db.scalar(select(WorkspaceRecord).where(WorkspaceRecord.owner == user.username, WorkspaceRecord.client_request_id == key))
    if previous:
        if previous.deleted_at or previous.kind != 'note' or previous.content != content:
            raise HTTPException(409, '该笔记已被修改或放入回收站，请先核对；不会覆盖原笔记')
        return {'note': serialized(previous), 'reused': True}
    note = WorkspaceRecord(owner=user.username, kind='note', title='学习笔记｜' + lesson['title'], content=content, status='done', tags=['笔记本:测试学习', '学习路线', '课题:' + lesson_id], client_request_id=key)
    db.add(note)
    try: db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '同一次笔记生成正在完成，请稍后用原请求编号重试')
    row = progress_row(db, user, lesson_id)
    row.status, row.evidence, row.run_id, row.note_id, row.updated_at = payload.status, payload.evidence, payload.run_id, note.id, datetime.utcnow()
    commit(db); db.refresh(note)
    return {'note': serialized(note), 'reused': False}


@router.get('/summary')
def summary(user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.modules.practice_lab.execution import PracticeRun
    active = select(WorkspaceRecord).where(WorkspaceRecord.owner == user.username, WorkspaceRecord.deleted_at.is_(None))
    tasks = db.scalars(active.where(WorkspaceRecord.kind=='task', WorkspaceRecord.status!='done').order_by(WorkspaceRecord.due_at.asc(),WorkspaceRecord.id.desc())).all()
    notes = db.scalars(active.where(WorkspaceRecord.kind=='note').order_by(WorkspaceRecord.updated_at.desc()).limit(3)).all()
    runs = db.scalars(select(PracticeRun).where(PracticeRun.owner==user.username).order_by(PracticeRun.id.desc()).limit(3)).all()
    reminders = db.scalars(active.where(WorkspaceRecord.kind.in_(['task','memo']),WorkspaceRecord.status!='done',WorkspaceRecord.due_at<=datetime.utcnow()+timedelta(hours=24)).order_by(WorkspaceRecord.due_at).limit(8)).all()
    route = lesson_rows(db, user)
    next_lesson = next((lesson for lesson in route if not lesson['completed']), route[-1])
    return {'tasks':[serialized(row) for row in tasks[:12]], 'open_tasks':len(tasks), 'overdue':sum(bool(row.due_at and row.due_at < datetime.utcnow()) for row in tasks),
        'notes':[serialized(row) for row in notes], 'continue_lesson':next_lesson['id'], 'learning':{'completed':sum(row['completed'] for row in route),'total':len(route),'next_title':next_lesson['title']},
        'runs':[{'id':row.id,'suite':row.suite,'status':row.status} for row in runs], 'reminders':[serialized(row) for row in reminders]}
