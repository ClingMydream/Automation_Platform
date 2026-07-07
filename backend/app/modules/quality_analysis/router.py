"""Quality analysis routes for release-readiness and stability metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.modules.quality_analysis.service import build_quality_summary, build_quality_trend, build_task_quality_report


router = APIRouter(tags=["质量分析"])


@router.get("/v1/quality/summary", summary="查询质量总览")
def quality_summary(_: AuthContext = Depends(require_menu("quality")), db: Session = Depends(get_db)):
    """Return pass rate, failure distribution, and basic performance indicators."""
    return build_quality_summary(db)


@router.get("/v1/reports/quality-trend", summary="查询质量趋势")
def quality_trend(_: AuthContext = Depends(require_menu("quality")), db: Session = Depends(get_db)):
    """Return recent execution batches as a lightweight quality trend."""
    return build_quality_trend(db)


@router.get("/v1/reports/tasks/{task_id}", summary="查询任务质量报告")
def task_quality_report(task_id: int, _: AuthContext = Depends(require_menu("quality")), db: Session = Depends(get_db)):
    """Return recent batches and results for one task as a task-level report."""
    return build_task_quality_report(db, task_id)
