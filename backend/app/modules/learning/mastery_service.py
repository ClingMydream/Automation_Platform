"""Mastery curriculum seeding, progress gates, notes, timers, and safe reset helpers."""

import json
import shutil
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import (
    LearningAttachment, LearningCheckin, LearningImport, LearningMasteryLesson,
    LearningMasteryProgress, LearningMasteryStage, LearningNote, LearningNoteFolder,
    LearningPlan, LearningProfile, LearningScheduleShift, LearningStudyTimer, LearningTask,
)
from app.modules.learning.mastery_course import LESSONS, SEED_VERSION, STAGES
from app.modules.learning.mastery_answers import REFERENCE_CODE


OLD_MODELS = (LearningAttachment, LearningNote, LearningNoteFolder, LearningCheckin,
              LearningStudyTimer, LearningScheduleShift, LearningTask, LearningPlan,
              LearningImport, LearningProfile)
MASTERY_MODELS = (LearningMasteryProgress, LearningMasteryLesson, LearningMasteryStage)


def row_data(row):
    values = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    return {key: value.isoformat() if isinstance(value, (date, datetime)) else value for key, value in values.items()}


def ensure_mastery_seed(db: Session):
    existing = db.scalar(select(LearningMasteryStage).where(LearningMasteryStage.seed_version == SEED_VERSION))
    if existing:
        return
    stage_by_key = {}
    for index, (key, icon, title, objective) in enumerate(STAGES, 1):
        stage = LearningMasteryStage(seed_version=SEED_VERSION, key=key, icon=icon, title=title,
            objective=objective, sort_order=index)
        db.add(stage); db.flush(); stage_by_key[key] = stage
    for index, item in enumerate(LESSONS, 1):
        stage = stage_by_key[item["stage"]]
        lesson_row = LearningMasteryLesson(stage_id=stage.id, slug=item["slug"], title=item["title"],
            outcome=item["outcome"], estimated_minutes=75, sort_order=index, content=item["content"])
        db.add(lesson_row); db.flush()
        db.add(LearningMasteryProgress(lesson_id=lesson_row.id,
            status="available" if index == 1 else "locked", evidence={}, blockers=[]))
    db.commit()


def elapsed_seconds(progress: LearningMasteryProgress):
    value = progress.elapsed_seconds
    if progress.timer_status == "running" and progress.timer_started_at:
        value += max(0, int((datetime.utcnow() - progress.timer_started_at).total_seconds()))
    return value


def progress_data(progress: LearningMasteryProgress):
    return {**row_data(progress), "elapsed_seconds": elapsed_seconds(progress)}


def public_content(lesson: LearningMasteryLesson, evidence: dict):
    content = dict(lesson.content or {})
    reference_code = REFERENCE_CODE.get(lesson.slug)
    if not reference_code:
        raise ValueError(f"Missing reviewed reference code for lesson: {lesson.slug}")
    exercise = dict(content.get("exercise") or {})
    actions = content.get("follow_steps") or []
    action_path = " → ".join(actions)
    exercise["reference_answer"] = (
        f"参考思路：按“{action_path}”完成并保存实际结果。"
        f"针对题目“{exercise.get('prompt', '')}”，先复用本关示例的输入、处理和输出结构，"
        "再只修改一个条件运行第二次，对比两次结果并解释原因。"
    )
    exercise["reference_code"] = reference_code["exercise"]
    content["exercise"] = exercise
    content["rewrite_reference_answer"] = (
        f"参考改写：{content.get('rewrite_task', '')}"
        "保留原示例的核心执行顺序，只替换题目要求的变量、参数或业务内容；"
        "运行后记录改了哪里、结果是什么，以及为什么其余部分不需要修改。"
    )
    content["rewrite_reference_code"] = reference_code["rewrite"]
    content["explanation_reference_answer"] = (
        f"参考表达：这一关要解决的是“{lesson.outcome}”。"
        f"我把它理解为：{content.get('mental_model', '')}"
        "实际操作时，先准备题目要求的输入，按示例完成处理，再通过输出或断言确认结果是否符合预期。"
    )
    answered = evidence.get("quiz_answers") or []
    quiz = []
    for index, question in enumerate(content.get("quiz", [])):
        row = {key: value for key, value in question.items() if key not in {"answer", "explanation"}}
        answer_index = question["answer"]
        row["reference_answer"] = question["options"][answer_index]
        row["reference_explanation"] = question["explanation"]
        if index < len(answered):
            row["is_correct"] = answered[index] == question["answer"]
            row["explanation"] = question["explanation"]
        quiz.append(row)
    content["quiz"] = quiz
    return content


def lesson_payload(db: Session, lesson: LearningMasteryLesson):
    progress = db.scalar(select(LearningMasteryProgress).where(LearningMasteryProgress.lesson_id == lesson.id))
    stage = db.get(LearningMasteryStage, lesson.stage_id)
    return {**row_data(lesson), "stage": row_data(stage), "content": public_content(lesson, progress.evidence or {}),
        "progress": progress_data(progress), "gates": mastery_gates(lesson, progress.evidence or {})}


def mastery_gates(lesson: LearningMasteryLesson, evidence: dict):
    answers = evidence.get("quiz_answers") or []
    quiz = lesson.content.get("quiz", [])
    quiz_correct = len(answers) == len(quiz) and all(answers[index] == row["answer"] for index, row in enumerate(quiz))
    explanation = (evidence.get("explanation") or "").strip()
    return {
        "run": bool(evidence.get("run_confirmed") and (evidence.get("run_output") or "").strip()),
        "rewrite": bool((evidence.get("modified_code") or "").strip()),
        "exercise": bool((evidence.get("exercise_answer") or "").strip()),
        "understanding": bool(quiz_correct and len(explanation) >= 20),
    }


def save_mastery_note(db: Session, lesson: LearningMasteryLesson, evidence: dict):
    fingerprint = f"mastery:{lesson.slug}"
    note = db.scalar(select(LearningNote).where(LearningNote.import_fingerprint == fingerprint))
    content = evidence.get("explanation") or "待补充"
    if note:
        note.content_markdown = content
    else:
        db.add(LearningNote(title=f"关卡笔记 · {lesson.title}", content_markdown=content,
            tags=["能力关卡", lesson.slug], import_fingerprint=fingerprint))


def unlock_next(db: Session, lesson: LearningMasteryLesson):
    next_lesson = db.scalar(select(LearningMasteryLesson).where(
        LearningMasteryLesson.sort_order > lesson.sort_order).order_by(LearningMasteryLesson.sort_order))
    if next_lesson:
        progress = db.scalar(select(LearningMasteryProgress).where(LearningMasteryProgress.lesson_id == next_lesson.id))
        if progress.status == "locked":
            progress.status = "available"


def backup_and_clear_learning(db: Session):
    settings = get_settings()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = Path(settings.learning_data_dir) / "backups" / f"mastery-reset-{stamp}"
    backup_root.mkdir(parents=True, exist_ok=False)
    snapshot = {}
    for model in (*OLD_MODELS, *MASTERY_MODELS):
        snapshot[model.__tablename__] = [row_data(row) for row in db.scalars(select(model)).all()]
    (backup_root / "learning-data.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    source = Path(settings.learning_data_dir) / "attachments"
    if source.exists():
        shutil.copytree(source, backup_root / "attachments")
        shutil.rmtree(source)
    source.mkdir(parents=True, exist_ok=True)
    for model in (*MASTERY_MODELS, *OLD_MODELS):
        db.execute(delete(model))
    db.commit()
    ensure_mastery_seed(db)
    return str(backup_root)
