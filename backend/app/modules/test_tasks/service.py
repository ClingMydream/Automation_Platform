"""Business helpers for test tasks and execution batches."""

from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Environment, ExecutionBatch, Project, TestObject, TestTask
from app.modules.test_tasks.schemas import TestTaskCreate


def ensure_task_relations(db: Session, payload: TestTaskCreate) -> None:
    """Validate optional project, environment, and test object references."""
    if payload.project_id is not None and db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.environment_id is not None and db.get(Environment, payload.environment_id) is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    if payload.test_object_id is not None and db.get(TestObject, payload.test_object_id) is None:
        raise HTTPException(status_code=404, detail="Test object not found")


def ensure_unique_task_code(db: Session, code: str, exclude_id: int | None = None) -> None:
    """Keep task codes globally unique so CI and external scripts can reference them safely."""
    query = db.query(TestTask).filter(TestTask.code == code)
    if exclude_id is not None:
        query = query.filter(TestTask.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=400, detail="Task code already exists")


def task_payload_data(payload: TestTaskCreate) -> dict:
    """Convert a validated request schema into ORM-ready data."""
    data = payload.model_dump()
    data["code"] = data["code"].strip()
    data["name"] = data["name"].strip()
    data["schedule_cron"] = data["schedule_cron"] or None
    data["owner"] = data["owner"] or None
    data["description"] = data["description"] or None
    return data


def create_execution_batch(db: Session, task: TestTask | None, trigger_type: str, environment_id: int | None, summary: dict) -> ExecutionBatch:
    """Create a traceable execution batch for one task run or external result upload."""
    batch = ExecutionBatch(
        batch_no=f"BT-{datetime.utcnow():%Y%m%d%H%M%S}-{uuid4().hex[:8]}",
        task_id=task.id if task else None,
        trigger_type=trigger_type,
        environment_id=environment_id,
        status="running",
        started_at=datetime.utcnow(),
        summary=summary or {},
    )
    db.add(batch)
    if task is not None:
        task.last_status = "running"
        task.last_run_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    return batch
