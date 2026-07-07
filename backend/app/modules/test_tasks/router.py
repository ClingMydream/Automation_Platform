"""Test task routes for execution scheduling and batch creation."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_any_menu, require_menu
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import ExecutionBatch, TestTask
from app.modules.test_tasks.schemas import ExecutionBatchRead, TaskRunRequest, TestTaskCreate, TestTaskRead
from app.modules.test_tasks.service import create_api_task_runs, create_execution_batch, ensure_task_relations, ensure_unique_task_code, failed_api_case_ids_from_batch, task_by_code, task_payload_data, validate_api_task_cases
from app.services.queue import enqueue_run


router = APIRouter(tags=["测试任务"])


def _ensure_external_trigger_token(x_automation_token: str | None) -> None:
    """Validate the shared CI/API trigger token without exposing it in responses."""
    expected_token = get_settings().external_trigger_token
    if not expected_token:
        raise HTTPException(status_code=503, detail="External trigger token is not configured")
    if not x_automation_token or x_automation_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid trigger token")


def _start_task_batch(db: Session, task: TestTask, payload: TaskRunRequest) -> ExecutionBatch:
    """Create a batch and enqueue platform-executable cases for one task."""
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
    return _start_task_batch(db, task, payload)


@router.post("/v1/test-tasks/by-code/{task_code}/trigger", response_model=ExecutionBatchRead, summary="通过任务编号触发 CI/API 执行")
def trigger_task_by_code(
    task_code: str,
    payload: TaskRunRequest,
    x_automation_token: str | None = Header(default=None, alias="X-Automation-Token"),
    db: Session = Depends(get_db),
):
    """Allow CI jobs or external systems to trigger a task by code with a shared token."""
    _ensure_external_trigger_token(x_automation_token)
    task = task_by_code(db, task_code)
    trigger_payload = payload.model_copy(update={"trigger_type": payload.trigger_type if payload.trigger_type in {"ci", "api"} else "api"})
    summary = {**(trigger_payload.summary or {}), "source": "external_api", "task_code": task_code}
    return _start_task_batch(db, task, trigger_payload.model_copy(update={"summary": summary}))


@router.post("/v1/execution-batches/{batch_id}/retry", response_model=ExecutionBatchRead, summary="重试失败的接口用例")
def retry_failed_batch(batch_id: int, payload: TaskRunRequest, _: AuthContext = Depends(require_any_menu("test_tasks", "results")), db: Session = Depends(get_db)):
    """Create a new batch that reruns only failed API cases from a previous batch."""
    source_batch = db.get(ExecutionBatch, batch_id)
    if source_batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    if source_batch.task_id is None:
        raise HTTPException(status_code=400, detail="Only task batches can be retried")
    task = db.get(TestTask, source_batch.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.task_type != "api":
        raise HTTPException(status_code=400, detail="Only API task batches can be retried now")
    case_ids = failed_api_case_ids_from_batch(db, source_batch)
    if not case_ids:
        raise HTTPException(status_code=400, detail="No failed API cases to retry")
    environment_id = payload.environment_id or source_batch.environment_id or task.environment_id
    summary = {
        **(payload.summary or {}),
        "source": "retry",
        "retried_from_batch_id": source_batch.id,
        "retried_from_batch_no": source_batch.batch_no,
        "api_case_ids": case_ids,
    }
    batch = create_execution_batch(db, task, payload.trigger_type, environment_id, summary)
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
