from datetime import date
from pathlib import Path
import zipfile

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models.entities import LearningCheckin, LearningPlan, LearningProfile, LearningTask
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
