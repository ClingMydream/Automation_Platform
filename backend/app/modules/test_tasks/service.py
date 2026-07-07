"""Business helpers for test tasks and execution batches."""

from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import ApiCase, Environment, ExecutionBatch, Project, TestObject, TestRun, TestTask
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


def api_case_ids_from_task(task: TestTask) -> list[int]:
    """Read API case IDs from task config while supporting old and new key names."""
    config = task.config or {}
    raw_ids = config.get("api_case_ids") or config.get("case_ids") or []
    if not isinstance(raw_ids, list):
        raise HTTPException(status_code=400, detail="Task config api_case_ids must be a list")
    case_ids: list[int] = []
    for value in raw_ids:
        try:
            case_id = int(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Task config contains invalid API case ID") from exc
        if case_id not in case_ids:
            case_ids.append(case_id)
    return case_ids


def validate_api_task_cases(db: Session, task: TestTask) -> list[int]:
    """Validate that an API task has at least one existing API case."""
    case_ids = api_case_ids_from_task(task)
    if not case_ids:
        raise HTTPException(status_code=400, detail="API task config requires api_case_ids")
    cases = db.query(ApiCase).filter(ApiCase.id.in_(case_ids)).all()
    found_ids = {case.id for case in cases}
    missing_ids = [case_id for case_id in case_ids if case_id not in found_ids]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"API cases not found: {missing_ids}")
    return case_ids


def create_api_task_runs(db: Session, task: TestTask, batch: ExecutionBatch, case_ids: list[int]) -> list[TestRun]:
    """Create queued TestRun rows for every API case configured on a task."""
    runs = [
        TestRun(
            batch_id=batch.id,
            task_id=task.id,
            case_type="api",
            case_id=case_id,
            status="queued",
            logs="Task batch queued",
            report={},
        )
        for case_id in case_ids
    ]
    for run in runs:
        db.add(run)
    batch.total_count = len(runs)
    batch.summary = {**(batch.summary or {}), "api_case_ids": case_ids}
    db.commit()
    for run in runs:
        db.refresh(run)
    db.refresh(batch)
    return runs
