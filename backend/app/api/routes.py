import secrets
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, verify_admin
from app.core.config import get_settings
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import ApiCase, Environment, FileTransfer, Project, TestRun, UiCase
from app.schemas.entities import (
    ApiCaseCreate,
    ApiCaseRead,
    EnvironmentCreate,
    EnvironmentRead,
    LoginRequest,
    ProjectCreate,
    ProjectRead,
    RunCreate,
    RunRead,
    TokenResponse,
    UiCaseCreate,
    UiCaseRead,
)
from app.services.queue import enqueue_run


router = APIRouter()


def _transfer_dir() -> Path:
    settings = get_settings()
    path = Path(settings.file_transfer_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clean_filename(name: str) -> str:
    cleaned = Path(name or "file").name.strip().replace("\x00", "")
    return cleaned[:255] or "file"


def _file_response(item: FileTransfer) -> dict:
    settings = get_settings()
    base_url = settings.public_base_url.rstrip("/")
    return {
        "id": item.id,
        "token": item.token,
        "original_name": item.original_name,
        "content_type": item.content_type,
        "size_bytes": item.size_bytes,
        "source": item.source,
        "parent_token": item.parent_token,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "expires_at": item.expires_at,
        "download_url": f"{base_url}/api/file-transfers/public/{item.token}/download",
        "preview_url": f"{base_url}/api/file-transfers/public/{item.token}/preview",
        "share_url": f"{base_url}/?transferToken={item.token}",
    }


def _cleanup_expired(db: Session) -> None:
    now = datetime.utcnow()
    expired = db.query(FileTransfer).filter(FileTransfer.expires_at <= now).all()
    if not expired:
        return
    directory = _transfer_dir()
    for item in expired:
        path = directory / item.stored_name
        if path.exists():
            path.unlink()
        db.delete(item)
    db.commit()


def _save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> int:
    size = 0
    with destination.open("wb") as output:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File is too large")
            output.write(chunk)
    return size


def _create_transfer(
    db: Session,
    upload: UploadFile,
    *,
    source: str,
    parent_token: str | None = None,
    expires_at: datetime | None = None,
) -> FileTransfer:
    settings = get_settings()
    max_bytes = settings.file_transfer_max_mb * 1024 * 1024
    token = secrets.token_urlsafe(24)
    original_name = _clean_filename(upload.filename or "file")
    stored_name = f"{token}-{original_name}"
    destination = _transfer_dir() / stored_name
    size = _save_upload(upload, destination, max_bytes)
    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="File is empty")
    item = FileTransfer(
        token=token,
        original_name=original_name,
        stored_name=stored_name,
        content_type=upload.content_type,
        size_bytes=size,
        source=source,
        parent_token=parent_token,
        expires_at=expires_at or (datetime.utcnow() + timedelta(hours=settings.file_transfer_default_hours)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    settings = get_settings()
    if payload.username != settings.admin_username or payload.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(payload.username))


@router.post("/auth/logout")
def logout(_: str = Depends(verify_admin)):
    return {"status": "ok"}


@router.get("/auth/me")
def me(username: str = Depends(verify_admin)):
    return {"username": username}


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(_: str = Depends(verify_admin), db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id.desc()).all()


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in payload.model_dump().items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    api_ids = [row[0] for row in db.query(ApiCase.id).filter(ApiCase.project_id == project_id).all()]
    ui_ids = [row[0] for row in db.query(UiCase.id).filter(UiCase.project_id == project_id).all()]
    if api_ids:
        db.query(TestRun).filter(TestRun.case_type == "api", TestRun.case_id.in_(api_ids)).delete(synchronize_session=False)
        db.query(ApiCase).filter(ApiCase.id.in_(api_ids)).delete(synchronize_session=False)
    if ui_ids:
        db.query(TestRun).filter(TestRun.case_type == "ui", TestRun.case_id.in_(ui_ids)).delete(synchronize_session=False)
        db.query(UiCase).filter(UiCase.id.in_(ui_ids)).delete(synchronize_session=False)
    db.delete(project)
    db.commit()
    return {"status": "ok"}


@router.get("/environments", response_model=list[EnvironmentRead])
def list_environments(_: str = Depends(verify_admin), db: Session = Depends(get_db)):
    return db.query(Environment).order_by(Environment.id.desc()).all()


@router.post("/environments", response_model=EnvironmentRead)
def create_environment(payload: EnvironmentCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    validate_public_http_url(payload.base_url)
    environment = Environment(**payload.model_dump())
    db.add(environment)
    db.commit()
    db.refresh(environment)
    return environment


@router.get("/api-cases", response_model=list[ApiCaseRead])
def list_api_cases(_: str = Depends(verify_admin), db: Session = Depends(get_db)):
    return db.query(ApiCase).order_by(ApiCase.id.desc()).all()


@router.post("/api-cases", response_model=ApiCaseRead)
def create_api_case(payload: ApiCaseCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    validate_public_http_url(payload.url)
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    case = ApiCase(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.put("/api-cases/{case_id}", response_model=ApiCaseRead)
def update_api_case(case_id: int, payload: ApiCaseCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    validate_public_http_url(payload.url)
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    for key, value in payload.model_dump().items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/api-cases/{case_id}")
def delete_api_case(case_id: int, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    db.query(TestRun).filter(TestRun.case_type == "api", TestRun.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"status": "ok"}


@router.get("/ui-cases", response_model=list[UiCaseRead])
def list_ui_cases(_: str = Depends(verify_admin), db: Session = Depends(get_db)):
    return db.query(UiCase).order_by(UiCase.id.desc()).all()


@router.post("/ui-cases", response_model=UiCaseRead)
def create_ui_case(payload: UiCaseCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for step in payload.steps:
        if step.action == "goto" and step.value:
            validate_public_http_url(step.value)
    case = UiCase(project_id=payload.project_id, name=payload.name, steps=[step.model_dump() for step in payload.steps])
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.put("/ui-cases/{case_id}", response_model=UiCaseRead)
def update_ui_case(case_id: int, payload: UiCaseCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for step in payload.steps:
        if step.action == "goto" and step.value:
            validate_public_http_url(step.value)
    case = db.get(UiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    case.project_id = payload.project_id
    case.name = payload.name
    case.steps = [step.model_dump() for step in payload.steps]
    db.commit()
    db.refresh(case)
    return case


@router.delete("/ui-cases/{case_id}")
def delete_ui_case(case_id: int, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    case = db.get(UiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    db.query(TestRun).filter(TestRun.case_type == "ui", TestRun.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"status": "ok"}


@router.get("/file-transfers")
def list_file_transfers(_: str = Depends(verify_admin), db: Session = Depends(get_db)):
    _cleanup_expired(db)
    items = db.query(FileTransfer).order_by(FileTransfer.id.desc()).limit(100).all()
    return [_file_response(item) for item in items]


@router.post("/file-transfers")
def upload_file_transfer(
    file: UploadFile = File(...),
    expires_hours: int = Query(default=24, ge=1, le=168),
    _: str = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    _cleanup_expired(db)
    item = _create_transfer(
        db,
        file,
        source="admin",
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )
    return _file_response(item)


@router.delete("/file-transfers/{transfer_id}")
def delete_file_transfer(transfer_id: int, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    item = db.get(FileTransfer, transfer_id)
    if item is None:
        raise HTTPException(status_code=404, detail="File not found")
    path = _transfer_dir() / item.stored_name
    if path.exists():
        path.unlink()
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.get("/file-transfers/public/{token}")
def get_public_file_transfer(token: str, db: Session = Depends(get_db)):
    _cleanup_expired(db)
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    return _file_response(item)


@router.get("/file-transfers/public/{token}/download")
def download_public_file_transfer(token: str, db: Session = Depends(get_db)):
    _cleanup_expired(db)
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    path = _transfer_dir() / item.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return FileResponse(
        path=path,
        media_type=item.content_type or "application/octet-stream",
        filename=item.original_name,
    )


@router.get("/file-transfers/public/{token}/preview")
def preview_public_file_transfer(token: str, db: Session = Depends(get_db)):
    _cleanup_expired(db)
    item = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if item is None:
        raise HTTPException(status_code=404, detail="File not found or expired")
    content_type = item.content_type or "application/octet-stream"
    if not (content_type.startswith("image/") or content_type.startswith("video/")):
        raise HTTPException(status_code=415, detail="Preview only supports images and videos")
    path = _transfer_dir() / item.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return FileResponse(
        path=path,
        media_type=content_type,
        filename=item.original_name,
        content_disposition_type="inline",
    )


@router.post("/file-transfers/public/{token}/upload")
def upload_public_file_transfer(token: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _cleanup_expired(db)
    parent = db.query(FileTransfer).filter(FileTransfer.token == token).first()
    if parent is None:
        raise HTTPException(status_code=404, detail="Transfer link not found or expired")
    item = _create_transfer(
        db,
        file,
        source="public",
        parent_token=token,
        expires_at=parent.expires_at,
    )
    return _file_response(item)


@router.get("/runs", response_model=list[RunRead])
def list_runs(_: str = Depends(verify_admin), db: Session = Depends(get_db)):
    return db.query(TestRun).order_by(TestRun.id.desc()).limit(100).all()


@router.post("/runs", response_model=RunRead)
def create_run(payload: RunCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    model = ApiCase if payload.case_type == "api" else UiCase
    if db.get(model, payload.case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    run = TestRun(case_type=payload.case_type, case_id=payload.case_id, status="queued", report={})
    db.add(run)
    db.commit()
    db.refresh(run)
    enqueue_run(run.id)
    return run


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(run_id: int, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/reports/{run_id}")
def get_report(run_id: int, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return run.report or {}
