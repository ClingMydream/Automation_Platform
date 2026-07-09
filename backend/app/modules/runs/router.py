"""Execution run routes for creating tasks and reading run results."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_current_user, require_menu
from app.db import get_db
from app.models.entities import ApiCase, TestRun, UiCase
from app.modules.reports.service import result_id_for_run
from app.schemas.entities import RunCreate, RunRead
from app.services.queue import enqueue_run


router = APIRouter(tags=["执行记录"])

# 执行任务：创建任务后进入 Redis 队列，worker 异步执行并回写结果。
@router.get(
    "/runs",
    response_model=list[RunRead],
    summary="查询执行记录列表",
    description="读取最近 100 条执行记录，包含状态、耗时、错误信息和 worker 回写的报告内容。",
)
def list_runs(_: AuthContext = Depends(require_menu("runs")), db: Session = Depends(get_db)):
    """List recent test execution records."""
    runs = db.query(TestRun).order_by(TestRun.id.desc()).limit(100).all()
    return [run_read_payload(db, run) for run in runs]


@router.post(
    "/runs",
    response_model=RunRead,
    summary="创建自动化执行任务",
    description=(
        "提交 case_type 和 case_id 后创建 queued 状态任务，并推送到 Redis 队列。"
        "JMeter 压测可重点观察该接口的吞吐、错误率，以及后续 /api/runs/{run_id} 轮询耗时。"
    ),
)
def create_run(payload: RunCreate, current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a test run and enqueue it for worker execution."""
    required_menu = "api" if payload.case_type == "api" else "ui"
    # Creating a run is allowed only for the matching test module permission.
    if not current_user.is_admin and required_menu not in current_user.menu_permissions:
        raise HTTPException(status_code=403, detail="Menu permission required")
    model = ApiCase if payload.case_type == "api" else UiCase
    if db.get(model, payload.case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    run = TestRun(case_type=payload.case_type, case_id=payload.case_id, status="queued", report={})
    db.add(run)
    db.commit()
    db.refresh(run)
    # The backend returns quickly; the worker consumes the Redis job and updates this run later.
    enqueue_run(run.id)
    return run


@router.get(
    "/runs/{run_id}",
    response_model=RunRead,
    summary="查询单条执行记录",
    description="按执行 ID 查询任务状态和报告详情，前端执行后会轮询该接口直到任务结束。",
)
def get_run(run_id: int, _: AuthContext = Depends(require_menu("runs")), db: Session = Depends(get_db)):
    """Return one test run with its report details."""
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_read_payload(db, run)


def run_read_payload(db: Session, run: TestRun) -> dict:
    """Serialize a run and include its linked result-center row when available."""
    return {
        "id": run.id,
        "batch_id": run.batch_id,
        "task_id": run.task_id,
        "result_id": result_id_for_run(db, run),
        "case_type": run.case_type,
        "case_id": run.case_id,
        "status": run.status,
        "duration_ms": run.duration_ms,
        "logs": run.logs,
        "error": run.error,
        "report": run.report or {},
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }
