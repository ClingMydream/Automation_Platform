from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, verify_admin
from app.core.config import get_settings
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import ApiCase, Environment, Project, TestRun, UiCase
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
    case = ApiCase(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/ui-cases", response_model=list[UiCaseRead])
def list_ui_cases(_: str = Depends(verify_admin), db: Session = Depends(get_db)):
    return db.query(UiCase).order_by(UiCase.id.desc()).all()


@router.post("/ui-cases", response_model=UiCaseRead)
def create_ui_case(payload: UiCaseCreate, _: str = Depends(verify_admin), db: Session = Depends(get_db)):
    for step in payload.steps:
        if step.action == "goto" and step.value:
            validate_public_http_url(step.value)
    case = UiCase(project_id=payload.project_id, name=payload.name, steps=[step.model_dump() for step in payload.steps])
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


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
