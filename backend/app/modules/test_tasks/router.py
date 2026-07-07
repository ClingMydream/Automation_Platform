"""Test task routes for execution scheduling and batch creation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import TestTask
from app.modules.test_tasks.schemas import ExecutionBatchRead, TaskRunRequest, TestTaskCreate, TestTaskRead
from app.modules.test_tasks.service import create_api_task_runs, create_execution_batch, ensure_task_relations, ensure_unique_task_code, task_payload_data, validate_api_task_cases
from app.services.queue import enqueue_run


router = APIRouter(tags=["测试任务"])


@router.get("/v1/test-tasks", response_model=list[TestTaskRead], summary="查询测试任务列表")
def list_test_tasks(_: AuthContext = Depends(require_menu("test_tasks")), db: Session = Depends(get_db)):
    """List reusable test tasks for scheduling, CI, and manual execution."""
    return db.query(TestTask).order_by(TestTask.id.desc()).all()


@router.post("/v1/test-tasks", response_model=TestTaskRead, summary="新增测试任务")
def create_test_task(payload: TestTaskCreate, _: AuthContext = Depends(require_menu("test_tasks")), db: Session = Depends(get_db)):
    """Create a reusable task definition without touching legacy test cases."""
    ensure_task_relations(db, payload)
    data = task_payload_data(payload)
    ensure_unique_task_code(db, data["code"])
    task = TestTask(**data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/v1/test-tasks/{task_id}", response_model=TestTaskRead, summary="修改测试任务")
def update_test_task(task_id: int, payload: TestTaskCreate, _: AuthContext = Depends(require_menu("test_tasks")), db: Session = Depends(get_db)):
    """Update a reusable task definition."""
    task = db.get(TestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_task_relations(db, payload)
    data = task_payload_data(payload)
    ensure_unique_task_code(db, data["code"], exclude_id=task_id)
    for key, value in data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/v1/test-tasks/{task_id}", summary="删除测试任务")
def delete_test_task(task_id: int, _: AuthContext = Depends(require_menu("test_tasks")), db: Session = Depends(get_db)):
    """Delete one task definition while keeping historical results available."""
    task = db.get(TestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"status": "ok"}


@router.post("/v1/test-tasks/{task_id}/run", response_model=ExecutionBatchRead, summary="启动测试任务")
def run_test_task(task_id: int, payload: TaskRunRequest, _: AuthContext = Depends(require_menu("test_tasks")), db: Session = Depends(get_db)):
    """Create an execution batch for manual, CI, scheduled, or API-triggered execution."""
    task = db.get(TestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.is_active:
        raise HTTPException(status_code=400, detail="Task is disabled")
    environment_id = payload.environment_id or task.environment_id
    case_ids = validate_api_task_cases(db, task) if task.task_type == "api" else []
    batch = create_execution_batch(db, task, payload.trigger_type, environment_id, payload.summary)
    if task.task_type == "api":
        runs = create_api_task_runs(db, task, batch, case_ids)
        for run in runs:
            enqueue_run(run.id)
    return batch


@router.get("/v1/test-tasks/{task_id}/status", summary="查询任务最近状态")
def get_test_task_status(task_id: int, _: AuthContext = Depends(require_menu("test_tasks")), db: Session = Depends(get_db)):
    """Return the latest task status for CI polling and page display."""
    task = db.get(TestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task.id, "code": task.code, "last_status": task.last_status, "last_run_at": task.last_run_at}
