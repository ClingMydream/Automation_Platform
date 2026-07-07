"""Business helpers for result collection, batch statistics, and attachments."""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import ExecutionBatch, TestAttachment, TestResult, TestTask
from app.modules.integrations.service import notify_batch_finished
from app.modules.result_center.schemas import ResultBatchUpload, TestResultCreate
from app.modules.test_tasks.service import create_execution_batch


def attachment_dir() -> Path:
    """Return the configured attachment directory and create it if needed."""
    path = Path(get_settings().result_attachment_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def refresh_batch_statistics(db: Session, batch: ExecutionBatch) -> ExecutionBatch:
    """Recalculate batch status and counts from stored result rows."""
    rows = db.query(TestResult).filter(TestResult.batch_id == batch.id).all()
    total = len(rows)
    passed = len([row for row in rows if row.status == "passed"])
    failed = len([row for row in rows if row.status in {"failed", "error"}])
    skipped = len([row for row in rows if row.status == "skipped"])
    batch.total_count = total
    batch.passed_count = passed
    batch.failed_count = failed
    batch.skipped_count = skipped
    batch.duration_ms = sum(row.duration_ms or 0 for row in rows) if rows else None
    batch.status = "failed" if failed else ("passed" if total and passed + skipped == total else "running")
    db.commit()
    db.refresh(batch)
    if batch.task_id:
        task = db.get(TestTask, batch.task_id)
        if task is not None:
            task.last_status = batch.status
            db.commit()
    notify_batch_finished(db, batch)
    return batch


def create_result_row(db: Session, batch: ExecutionBatch, task_id: int | None, payload: TestResultCreate) -> TestResult:
    """Persist one uploaded result row and attach it to the current batch."""
    data = payload.model_dump()
    result = TestResult(batch_id=batch.id, task_id=task_id, **data)
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def resolve_or_create_batch(db: Session, task: TestTask | None, payload: ResultBatchUpload) -> ExecutionBatch:
    """Find an existing batch by batch number or create a new upload batch."""
    if payload.batch_no:
        batch = db.query(ExecutionBatch).filter(ExecutionBatch.batch_no == payload.batch_no).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        return batch
    environment_id = payload.environment_id or (task.environment_id if task else None)
    return create_execution_batch(db, task, payload.trigger_type, environment_id, payload.summary)


def save_attachment_file(db: Session, file: UploadFile, result_id: int | None, batch_id: int | None, attachment_type: str) -> TestAttachment:
    """Store an uploaded attachment on disk and persist its metadata."""
    settings = get_settings()
    max_bytes = settings.result_attachment_max_mb * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Attachment is too large")
    if not content:
        raise HTTPException(status_code=400, detail="Attachment is empty")
    if result_id is not None and db.get(TestResult, result_id) is None:
        raise HTTPException(status_code=404, detail="Result not found")
    if batch_id is not None and db.get(ExecutionBatch, batch_id) is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    original_name = file.filename or "attachment"
    stored_name = f"{uuid4().hex}-{Path(original_name).name[:120]}"
    path = attachment_dir() / stored_name
    path.write_bytes(content)
    item = TestAttachment(
        result_id=result_id,
        batch_id=batch_id,
        attachment_type=attachment_type,
        original_name=original_name,
        stored_name=stored_name,
        content_type=file.content_type,
        size_bytes=len(content),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
