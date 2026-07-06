"""Result center routes for collected execution evidence and attachments."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.db import get_db
from app.models.entities import ExecutionBatch, TestAttachment, TestResult, TestTask
from app.modules.result_center.schemas import AttachmentRead, ResultBatchUpload, TestResultRead
from app.modules.result_center.service import attachment_dir, create_result_row, refresh_batch_statistics, resolve_or_create_batch, save_attachment_file


router = APIRouter(tags=["结果中心"])


@router.get("/v1/execution-batches", summary="查询执行批次列表")
def list_execution_batches(_: AuthContext = Depends(require_menu("results")), db: Session = Depends(get_db)):
    """List execution batches from manual, CI, API, or scheduled triggers."""
    return db.query(ExecutionBatch).order_by(ExecutionBatch.id.desc()).limit(200).all()


@router.get("/v1/test-results", response_model=list[TestResultRead], summary="查询测试结果列表")
def list_test_results(
    status: str | None = Query(default=None, description="可选状态过滤"),
    result_type: str | None = Query(default=None, description="可选结果类型过滤"),
    _: AuthContext = Depends(require_menu("results")),
    db: Session = Depends(get_db),
):
    """List collected result rows for the result center page."""
    query = db.query(TestResult)
    if status:
        query = query.filter(TestResult.status == status)
    if result_type:
        query = query.filter(TestResult.result_type == result_type)
    return query.order_by(TestResult.id.desc()).limit(500).all()


@router.get("/v1/test-results/{result_id}", response_model=TestResultRead, summary="查询测试结果详情")
def get_test_result(result_id: int, _: AuthContext = Depends(require_menu("results")), db: Session = Depends(get_db)):
    """Return one collected test result with request, response, assertion, and metric details."""
    result = db.get(TestResult, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@router.post("/v1/test-tasks/{task_id}/results/batch", summary="批量回传任务结果")
def upload_task_results(task_id: int, payload: ResultBatchUpload, _: AuthContext = Depends(require_menu("results")), db: Session = Depends(get_db)):
    """Accept batch results from external automation scripts, CI jobs, pytest, Playwright, or JMeter."""
    task = db.get(TestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    batch = resolve_or_create_batch(db, task, payload)
    results = [create_result_row(db, batch, task.id, item) for item in payload.results]
    batch = refresh_batch_statistics(db, batch)
    return {"batch": batch, "result_count": len(results)}


@router.post("/v1/test-results/batch", summary="批量回传独立结果")
def upload_standalone_results(payload: ResultBatchUpload, _: AuthContext = Depends(require_menu("results")), db: Session = Depends(get_db)):
    """Accept batch results that are not tied to a predefined task."""
    batch = resolve_or_create_batch(db, None, payload)
    results = [create_result_row(db, batch, None, item) for item in payload.results]
    batch = refresh_batch_statistics(db, batch)
    return {"batch": batch, "result_count": len(results)}


@router.post("/v1/attachments", response_model=AttachmentRead, summary="上传测试附件")
def upload_attachment(
    file: UploadFile = File(...),
    result_id: int | None = Form(default=None),
    batch_id: int | None = Form(default=None),
    attachment_type: str = Form(default="log"),
    _: AuthContext = Depends(require_menu("results")),
    db: Session = Depends(get_db),
):
    """Upload screenshots, recordings, logs, HAR files, or report artifacts."""
    return save_attachment_file(db, file, result_id, batch_id, attachment_type)


@router.get("/v1/attachments/{attachment_id}/download", summary="下载测试附件")
def download_attachment(attachment_id: int, _: AuthContext = Depends(require_menu("results")), db: Session = Depends(get_db)):
    """Download a stored test attachment."""
    item = db.get(TestAttachment, attachment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = attachment_dir() / item.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Attachment file is missing")
    return FileResponse(path=path, media_type=item.content_type or "application/octet-stream", filename=item.original_name)
