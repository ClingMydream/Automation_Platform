"""API test case management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import ApiCase, Project, TestRun
from app.schemas.entities import ApiCaseCreate, ApiCaseRead


router = APIRouter()

# 接口测试用例：这里只保存用例配置，真正执行由 worker 完成。
@router.get("/api-cases", response_model=list[ApiCaseRead])
def list_api_cases(_: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """List API test cases."""
    return db.query(ApiCase).order_by(ApiCase.id.desc()).all()


@router.post("/api-cases", response_model=ApiCaseRead)
def create_api_case(payload: ApiCaseCreate, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Create an API test case after validating the target URL."""
    # Block private or local targets before they can be saved and executed by the worker.
    validate_public_http_url(payload.url)
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    case = ApiCase(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.put("/api-cases/{case_id}", response_model=ApiCaseRead)
def update_api_case(case_id: int, payload: ApiCaseCreate, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Update an API test case after validating the target URL."""
    # Re-validate on update so an existing case cannot be changed to a private target.
    validate_public_http_url(payload.url)
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    # Copy every validated schema field into the existing SQLAlchemy model.
    for key, value in payload.model_dump().items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/api-cases/{case_id}")
def delete_api_case(case_id: int, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Delete an API test case and its run history."""
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    db.query(TestRun).filter(TestRun.case_type == "api", TestRun.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"status": "ok"}
