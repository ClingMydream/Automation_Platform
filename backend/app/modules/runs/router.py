"""Execution run routes for creating tasks and reading run results."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_current_user, require_menu
from app.db import get_db
from app.models.entities import ApiCase, TestRun, UiCase
from app.schemas.entities import RunCreate, RunRead
from app.services.queue import enqueue_run


router = APIRouter()

# 执行任务：创建任务后进入 Redis 队列，worker 异步执行并回写结果。
@router.get("/runs", response_model=list[RunRead])
def list_runs(_: AuthContext = Depends(require_menu("runs")), db: Session = Depends(get_db)):
    """List recent test execution records."""
    return db.query(TestRun).order_by(TestRun.id.desc()).limit(100).all()


@router.post("/runs", response_model=RunRead)
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


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(run_id: int, _: AuthContext = Depends(require_menu("runs")), db: Session = Depends(get_db)):
    """Return one test run with its report details."""
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
