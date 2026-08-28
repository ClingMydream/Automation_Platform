"""Mastery-gated Python, HTTP, and API automation learning APIs."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_menu, verify_admin
from app.db import get_db
from app.models.entities import LearningMasteryLesson, LearningMasteryProgress, LearningMasteryStage
from app.modules.learning.mastery_service import (
    backup_and_clear_learning, elapsed_seconds, ensure_mastery_seed, lesson_payload,
    mastery_gates, progress_data, row_data, save_mastery_note, unlock_next,
)
from app.modules.learning.schemas import MasteryBlockerInput, MasteryProgressInput, MasteryResetInput, MasteryTimerInput

router = APIRouter(prefix="/v1/learning/mastery", tags=["learning-mastery"],
    dependencies=[Depends(require_menu("learning"))])


def get_lesson_or_404(db: Session, lesson_id: int):
    lesson = db.get(LearningMasteryLesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "学习关卡不存在")
    return lesson


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    ensure_mastery_seed(db)
    stages = db.scalars(select(LearningMasteryStage).order_by(LearningMasteryStage.sort_order)).all()
    lessons = db.scalars(select(LearningMasteryLesson).order_by(LearningMasteryLesson.sort_order)).all()
    progress_rows = db.scalars(select(LearningMasteryProgress)).all()
    progress_by_lesson = {row.lesson_id: row for row in progress_rows}
    lesson_rows = [{**row_data(lesson), "progress": progress_data(progress_by_lesson[lesson.id])} for lesson in lessons]
    current = next((lesson for lesson in lessons if progress_by_lesson[lesson.id].status in {"available", "in_progress"}), lessons[-1])
    mastered = sum(row.status == "mastered" for row in progress_rows)
    return {
        "title": "Python、HTTP 与接口自动化能力路线",
        "principle": "不赶进度：运行、改写、小题、理解四项都完成后再进入下一关。",
        "stages": [{**row_data(stage), "lessons": [row for row in lesson_rows if row["stage_id"] == stage.id]} for stage in stages],
        "current_lesson_id": current.id, "mastered": mastered, "total": len(lessons),
        "total_seconds": sum(elapsed_seconds(row) for row in progress_rows),
    }


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    ensure_mastery_seed(db)
    lesson = get_lesson_or_404(db, lesson_id)
    progress = db.scalar(select(LearningMasteryProgress).where(LearningMasteryProgress.lesson_id == lesson.id))
    if progress.status == "locked":
        raise HTTPException(403, "请先完成前一关的四项学习证据")
    if progress.status == "available":
        progress.status = "in_progress"; db.commit()
    return lesson_payload(db, lesson)


@router.put("/lessons/{lesson_id}/progress")
def save_progress(lesson_id: int, payload: MasteryProgressInput, db: Session = Depends(get_db)):
    lesson = get_lesson_or_404(db, lesson_id)
    progress = db.scalar(select(LearningMasteryProgress).where(LearningMasteryProgress.lesson_id == lesson.id))
    if progress.status == "locked":
        raise HTTPException(403, "当前关卡尚未解锁")
    evidence = payload.model_dump(exclude={"current_step", "complete"})
    progress.evidence = evidence
    progress.current_step = payload.current_step
    progress.status = "in_progress" if progress.status != "mastered" else progress.status
    gates = mastery_gates(lesson, evidence)
    if payload.complete:
        missing = [name for name, passed in gates.items() if not passed]
        if missing:
            labels = {"run": "运行结果", "rewrite": "改写代码", "exercise": "独立小题", "understanding": "理解问答和个人解释"}
            raise HTTPException(400, "还需要完成：" + "、".join(labels[name] for name in missing))
        progress.status = "mastered"; progress.mastered_at = progress.mastered_at or datetime.utcnow()
        unlock_next(db, lesson)
    save_mastery_note(db, lesson, evidence)
    db.commit(); db.refresh(progress)
    result = lesson_payload(db, lesson)
    result["message"] = "本关已掌握，下一关已解锁" if payload.complete else "学习证据已保存"
    return result


@router.post("/lessons/{lesson_id}/blockers")
def add_blocker(lesson_id: int, payload: MasteryBlockerInput, db: Session = Depends(get_db)):
    lesson = get_lesson_or_404(db, lesson_id)
    progress = db.scalar(select(LearningMasteryProgress).where(LearningMasteryProgress.lesson_id == lesson.id))
    rows = list(progress.blockers or [])
    rows.append({"content": payload.content, "created_at": datetime.utcnow().isoformat(timespec="seconds")})
    progress.blockers = rows; db.commit(); db.refresh(progress)
    return progress_data(progress)


@router.post("/lessons/{lesson_id}/timer")
def change_timer(lesson_id: int, payload: MasteryTimerInput, db: Session = Depends(get_db)):
    lesson = get_lesson_or_404(db, lesson_id)
    progress = db.scalar(select(LearningMasteryProgress).where(LearningMasteryProgress.lesson_id == lesson.id))
    now = datetime.utcnow()
    if payload.action == "start":
        if progress.timer_status != "running": progress.timer_status = "running"; progress.timer_started_at = now
    elif payload.action in {"pause", "stop"}:
        if progress.timer_status == "running" and progress.timer_started_at:
            progress.elapsed_seconds += max(0, int((now - progress.timer_started_at).total_seconds()))
        progress.timer_started_at = None; progress.timer_status = "paused" if payload.action == "pause" else "stopped"
    else:
        raise HTTPException(400, "计时操作只支持 start、pause、stop")
    db.commit(); db.refresh(progress); return progress_data(progress)


@router.post("/reset", dependencies=[Depends(verify_admin)])
def reset_learning(payload: MasteryResetInput, db: Session = Depends(get_db)):
    if payload.confirm_text != "彻底重置学习空间":
        raise HTTPException(400, "确认文字不正确")
    backup_path = backup_and_clear_learning(db)
    return {"ok": True, "backup_path": backup_path, "message": "旧学习数据已备份，能力关卡课程已重新初始化"}
