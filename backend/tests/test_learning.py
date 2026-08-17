from datetime import date
from pathlib import Path
import zipfile

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models.entities import LearningCheckin, LearningNote, LearningPlan, LearningProfile, LearningTask
from app.modules.learning.router import complete_learning_day, delete_plan, list_tasks, overview, save_checkin
from app.modules.learning.schemas import CheckinInput
from app.modules.learning.importer import import_zip
from app.modules.learning.service import TOPICS, ensure_seed, stats


@pytest.fixture()
def db(tmp_path):
    engine=create_engine(f"sqlite:///{tmp_path/'learning.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session: yield session


def test_seed_is_complete_and_idempotent(db):
    ensure_seed(db); ensure_seed(db)
    assert db.query(LearningProfile).count()==1
    assert db.query(LearningPlan).count()==1
    tasks=db.scalars(select(LearningTask)).all()
    assert len(TOPICS)==40 and len(tasks)==80
    assert {t.day_number for t in tasks}==set(range(1,41))
    assert all(1 <= len([t for t in tasks if t.day_number==day]) <= 4 for day in range(1,41))


def test_stats_updates_checkin_and_completion(db):
    ensure_seed(db); task=db.scalar(select(LearningTask)); task.status="completed"
    db.add(LearningCheckin(checkin_date=date(2026,7,22),actual_minutes=300,gains="完成首个接口")); db.commit()
    result=stats(db,"2026-07")
    assert result["total_minutes"]==300
    assert result["days"]["2026-07-22"]["completed"]==1
    assert result["days"]["2026-07-22"]["checked_in"] is True


def test_zero_minute_checkin_still_appears_on_calendar(db):
    ensure_seed(db)
    db.add(LearningCheckin(checkin_date=date(2026,7,23),actual_minutes=0,gains="",blockers="临时有事")); db.commit()
    result=stats(db,"2026-07")
    assert result["checkin_days"]==1
    assert result["days"]["2026-07-23"]["checked_in"] is True
    assert result["days"]["2026-07-23"]["minutes"]==0


def test_next_learning_day_and_review_note_are_linked(db):
    ensure_seed(db)
    day_one = db.scalars(select(LearningTask).where(LearningTask.day_number == 1)).all()
    for task in day_one:
        task.status = "completed"
    db.commit()

    current = overview(db)
    assert current["next_task"]["day_number"] == 2
    assert {task["day_number"] for task in current["today_tasks"]} == {2}

    save_checkin(date(2026, 7, 22), CheckinInput(learning_day=1, actual_minutes=180, gains="完成预约", blockers="暂无", tomorrow_focus="学习接口"), db)
    note = db.scalar(select(LearningNote).where(LearningNote.title == "Day 1 · 每日复盘"))
    assert note is not None and "完成预约" in note.content_markdown
    tasks = list_tasks(db=db)
    assert any(task["day_number"] == 1 and task["day_checkin"]["actual_minutes"] == 180 for task in tasks)


def test_complete_learning_day_submits_tasks_checkin_and_note(db):
    ensure_seed(db)
    result = complete_learning_day(1, CheckinInput(actual_minutes=90, gains="学会查询接口", blockers="暂无", tomorrow_focus="学习断言"), db)

    day_tasks = db.scalars(select(LearningTask).where(LearningTask.day_number == 1)).all()
    note = db.scalar(select(LearningNote).where(LearningNote.title == "Day 1 · 每日复盘"))
    checkin = db.scalar(select(LearningCheckin).where(LearningCheckin.learning_day == 1))
    assert result["completed_tasks"] == len(day_tasks)
    assert all(task.status == "completed" for task in day_tasks)
    assert checkin.actual_minutes == 90
    assert "学会查询接口" in note.content_markdown


def test_delete_archived_plan_preserves_notes_and_checkins(db):
    ensure_seed(db)
    plan = db.scalar(select(LearningPlan))
    task = db.scalar(select(LearningTask).where(LearningTask.plan_id == plan.id))
    plan.status = "archived"
    note = LearningNote(title="历史笔记", content_markdown="复习内容", tags=[], linked_task_id=task.id)
    db.add_all([note, LearningCheckin(checkin_date=date(2026, 7, 24), actual_minutes=60)])
    db.commit()

    result = delete_plan(plan.id, db)

    assert result["ok"] is True
    assert db.get(LearningPlan, plan.id) is None
    assert db.query(LearningTask).count() == 0
    assert db.query(LearningCheckin).count() == 1
    assert db.get(LearningNote, note.id).linked_task_id is None


def test_import_rejects_path_traversal(db,tmp_path):
    archive=tmp_path/"bad.zip"
    with zipfile.ZipFile(archive,"w") as zf: zf.writestr("../escape.md","bad")
    with pytest.raises(ValueError,match="路径穿越"):
        import_zip(db,archive,"bad.zip",tmp_path,{"entries":5000,"expanded":1024**3,"attachment":20*1024**2})


def test_import_is_idempotent_and_preserves_folder(db,tmp_path):
    archive=tmp_path/"notes.zip"
    with zipfile.ZipFile(archive,"w") as zf: zf.writestr("接口学习/day1.md","# Day 1")
    limits={"entries":5000,"expanded":1024**3,"attachment":20*1024**2}
    first=import_zip(db,archive,"notes.zip",tmp_path,limits); second=import_zip(db,archive,"notes.zip",tmp_path,limits)
    assert len(first["success"])==1 and len(second["duplicates"])==1
