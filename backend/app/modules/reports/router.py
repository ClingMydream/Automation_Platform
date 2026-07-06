"""Test report routes built from completed execution runs."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import TestRun
from app.modules.reports.service import case_name_for_run, report_summary


router = APIRouter(tags=["测试报告"])

# 测试报告：从执行记录中汇总报告字段，供页面查看和导出。
@router.get(
    "/reports",
    summary="查询测试报告列表",
    description="从执行记录中汇总最近 200 条报告，返回用例名称、状态、耗时、日志和错误摘要。",
)
def list_reports(_: AuthContext = Depends(require_menu("reports")), db: Session = Depends(get_db)):
    """List test report summaries."""
    runs = db.query(TestRun).order_by(TestRun.id.desc()).limit(200).all()
    return [report_summary(run, case_name_for_run(db, run)) for run in runs]


@router.get(
    "/reports/{run_id}",
    summary="查询单份测试报告",
    description="按执行 ID 查看单份测试报告，适合后续扩展为 Allure 报告跳转或导出 PDF。",
)
def get_report(run_id: int, _: AuthContext = Depends(require_menu("reports")), db: Session = Depends(get_db)):
    """Return one test report by run ID."""
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report_summary(run, case_name_for_run(db, run))
