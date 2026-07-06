"""API test case management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import ApiCase, Environment, Project, TestRun
from app.schemas.entities import ApiCaseCreate, ApiCaseRead, RunRead
from app.services.queue import enqueue_run


router = APIRouter(tags=["接口测试"])


def validate_api_case_target(db: Session, payload: ApiCaseCreate) -> None:
    """Validate project, optional environment, and final request target."""
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.environment_id is None:
        validate_public_http_url(payload.url)
        return
    environment = db.get(Environment, payload.environment_id)
    if environment is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    if environment.project_id != payload.project_id:
        raise HTTPException(status_code=400, detail="Environment does not belong to selected project")
    validate_public_http_url(environment.base_url)
    if payload.url.startswith(("http://", "https://")):
        validate_public_http_url(payload.url)
        return
    if not payload.url.startswith("/"):
        raise HTTPException(status_code=400, detail="Relative URL must start with / when environment is selected")


def create_debug_run(db: Session, case_id: int) -> TestRun:
    """Create one queued API run for the debug drawer without touching old execution flow."""
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    run = TestRun(case_type="api", case_id=case_id, status="queued", logs="API debug queued", report={})
    db.add(run)
    db.commit()
    db.refresh(run)
    enqueue_run(run.id)
    return run

# 接口测试用例：这里只保存用例配置，真正执行由 worker 完成。
@router.get(
    "/api-cases",
    response_model=list[ApiCaseRead],
    summary="查询接口用例列表",
    description="读取接口自动化用例配置，包含请求方法、URL、请求头、请求体和断言。",
)
def list_api_cases(_: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """List API test cases."""
    return db.query(ApiCase).order_by(ApiCase.id.desc()).all()


@router.post(
    "/api-cases",
    response_model=ApiCaseRead,
    summary="新增接口用例",
    description="保存接口自动化用例，并在入库前校验目标 URL，避免访问服务器内网或敏感地址。",
)
def create_api_case(payload: ApiCaseCreate, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Create an API test case after validating the target URL."""
    # Block private or local targets before they can be saved and executed by the worker.
    validate_api_case_target(db, payload)
    case = ApiCase(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.post(
    "/api-cases/{case_id}/debug",
    response_model=RunRead,
    summary="调试接口用例",
    description=(
        "创建一次接口调试执行任务，复用 worker 中的 pytest + requests + allure 执行链路。"
        "前端接口测试页可轮询调试结果并直接展示请求、响应、断言和错误信息。"
    ),
)
@router.post(
    "/v1/api-cases/{case_id}/debug",
    response_model=RunRead,
    include_in_schema=False,
)
def debug_api_case(case_id: int, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Create and enqueue one API debug run for the selected case."""
    return create_debug_run(db, case_id)


@router.put(
    "/api-cases/{case_id}",
    response_model=ApiCaseRead,
    summary="修改接口用例",
    description="更新接口自动化用例配置，URL 会重新执行公网安全校验。",
)
def update_api_case(case_id: int, payload: ApiCaseCreate, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Update an API test case after validating the target URL."""
    # Re-validate on update so an existing case cannot be changed to a private target.
    validate_api_case_target(db, payload)
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    # Copy every validated schema field into the existing SQLAlchemy model.
    for key, value in payload.model_dump().items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return case


@router.get(
    "/api-cases/debug-runs/{run_id}",
    response_model=RunRead,
    summary="查询接口调试结果",
    description="按调试运行 ID 查询接口调试结果，只允许读取接口类型运行，供接口测试页内联展示。",
)
@router.get(
    "/v1/api-cases/debug-runs/{run_id}",
    response_model=RunRead,
    include_in_schema=False,
)
def get_api_debug_run(run_id: int, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Return one API debug run without requiring the run-history menu permission."""
    run = db.get(TestRun, run_id)
    if run is None or run.case_type != "api":
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.delete(
    "/api-cases/{case_id}",
    summary="删除接口用例",
    description="删除接口用例及其执行记录，避免页面继续展示失效报告。",
)
def delete_api_case(case_id: int, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    """Delete an API test case and its run history."""
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    db.query(TestRun).filter(TestRun.case_type == "api", TestRun.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"status": "ok"}
