from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models.entities import (
    LearningMasteryLesson, LearningMasteryProgress, LearningMasteryStage, LearningNote,
)
from app.modules.learning.mastery_course import LESSONS, STAGES
from app.modules.learning.mastery_router import save_progress
from app.modules.learning.mastery_service import backup_and_clear_learning, ensure_mastery_seed
from app.modules.learning.schemas import MasteryProgressInput


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'mastery.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_mastery_seed_is_structured_complete_and_idempotent(db):
    ensure_mastery_seed(db); ensure_mastery_seed(db)
    assert db.query(LearningMasteryStage).count() == len(STAGES) == 8
    assert db.query(LearningMasteryLesson).count() == len(LESSONS) >= 30
    progress = db.scalars(select(LearningMasteryProgress).order_by(LearningMasteryProgress.id)).all()
    assert len(progress) == len(LESSONS)
    assert progress[0].status == "available"
    assert all(row.status == "locked" for row in progress[1:])
    for lesson in db.scalars(select(LearningMasteryLesson)).all():
        assert {"why", "mental_model", "annotated_code", "follow_steps", "rewrite_task", "exercise", "quiz"} <= set(lesson.content)


def test_four_mastery_gates_are_enforced_and_unlock_next_lesson(db):
    ensure_mastery_seed(db)
    lesson = db.scalar(select(LearningMasteryLesson).order_by(LearningMasteryLesson.sort_order))
    with pytest.raises(HTTPException, match="还需要完成"):
        save_progress(lesson.id, MasteryProgressInput(complete=True), db)

    result = save_progress(lesson.id, MasteryProgressInput(
        run_confirmed=True,
        run_output="python hello.py -> 你好，接口自动化",
        modified_code='print("我正在学习请求和响应")',
        exercise_answer="我创建了 about_me.py 并在终端运行成功。",
        quiz_answers=[lesson.content["quiz"][0]["answer"]],
        explanation="VS Code 用来编辑文件，真正逐行执行代码的是 Python 解释器。",
        current_step=8,
        complete=True,
    ), db)
    assert result["progress"]["status"] == "mastered"
    next_lesson = db.scalar(select(LearningMasteryLesson).where(
        LearningMasteryLesson.sort_order > lesson.sort_order).order_by(LearningMasteryLesson.sort_order))
    next_progress = db.scalar(select(LearningMasteryProgress).where(LearningMasteryProgress.lesson_id == next_lesson.id))
    assert next_progress.status == "available"
    assert db.scalar(select(LearningNote).where(LearningNote.import_fingerprint == f"mastery:{lesson.slug}")) is not None


def test_reset_creates_recoverable_backup_and_clean_route(db, tmp_path, monkeypatch):
    ensure_mastery_seed(db)
    db.add(LearningNote(title="旧学习笔记", content_markdown="需要备份", tags=[])); db.commit()
    monkeypatch.setattr("app.modules.learning.mastery_service.get_settings",
        lambda: SimpleNamespace(learning_data_dir=str(tmp_path / "learning-data")))

    backup_path = backup_and_clear_learning(db)
    assert (tmp_path / "learning-data" / "backups").exists()
    assert (Path(backup_path) / "learning-data.json").exists()
    assert db.query(LearningNote).count() == 0
    assert db.query(LearningMasteryLesson).count() == len(LESSONS)
    progress = db.scalars(select(LearningMasteryProgress).order_by(LearningMasteryProgress.id)).all()
    assert progress[0].status == "available" and all(row.status == "locked" for row in progress[1:])
