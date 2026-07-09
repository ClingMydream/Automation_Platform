"""Test report routes built from completed execution runs and batches."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import ExecutionBatch, TestRun
from app.modules.reports.service import batch_report_summary, case_name_for_run, report_summary


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
    batches = db.query(ExecutionBatch).order_by(ExecutionBatch.id.desc()).limit(100).all()
    batch_reports = [batch_report_summary(db, batch) for batch in batches]
    run_reports = [report_summary(db, run, case_name_for_run(db, run)) for run in runs]
    return [*batch_reports, *run_reports]


@router.get(
    "/reports/batches/{batch_id}",
    summary="查询批次测试报告",
    description="按执行批次 ID 汇总测试报告，包含批次统计、结果明细、请求响应、断言和失败原因。",
)
def get_batch_report(batch_id: int, _: AuthContext = Depends(require_menu("reports")), db: Session = Depends(get_db)):
    """Return one batch report by execution batch ID."""
    batch = db.get(ExecutionBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch report not found")
    return batch_report_summary(db, batch)


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
    return report_summary(db, run, case_name_for_run(db, run))
