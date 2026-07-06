"""Low-code UI test case management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import Project, TestRun, UiCase
from app.schemas.entities import UiCaseCreate, UiCaseRead


router = APIRouter(tags=["UI测试"])

# UI 测试用例：保存低代码步骤 JSON，执行时由 worker 调用 Playwright。
@router.get(
    "/ui-cases",
    response_model=list[UiCaseRead],
    summary="查询 UI 用例列表",
    description="读取低代码 UI 自动化用例，步骤由 goto、click、fill、wait、assert_text、screenshot 等动作组成。",
)
def list_ui_cases(_: AuthContext = Depends(require_menu("ui")), db: Session = Depends(get_db)):
    """List UI test cases."""
    return db.query(UiCase).order_by(UiCase.id.desc()).all()


@router.post(
    "/ui-cases",
    response_model=UiCaseRead,
    summary="新增 UI 用例",
    description="保存 UI 自动化步骤，并校验 goto 步骤的目标地址，避免访问 localhost、内网和云元数据地址。",
)
def create_ui_case(payload: UiCaseCreate, _: AuthContext = Depends(require_menu("ui")), db: Session = Depends(get_db)):
    """Create a UI test case after validating step target URLs."""
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    # Only goto steps can open network targets, so those values are safety-checked.
    for step in payload.steps:
        if step.action == "goto" and step.value:
            validate_public_http_url(step.value)
    case = UiCase(project_id=payload.project_id, name=payload.name, steps=[step.model_dump() for step in payload.steps])
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.put(
    "/ui-cases/{case_id}",
    response_model=UiCaseRead,
    summary="修改 UI 用例",
    description="更新 UI 自动化步骤，所有 goto 目标地址都会重新执行安全校验。",
)
def update_ui_case(case_id: int, payload: UiCaseCreate, _: AuthContext = Depends(require_menu("ui")), db: Session = Depends(get_db)):
    """Update a UI test case after validating step target URLs."""
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    # Re-check goto targets on every edit to prevent unsafe saved steps.
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


@router.delete(
    "/ui-cases/{case_id}",
    summary="删除 UI 用例",
    description="删除 UI 用例及其执行记录。",
)
def delete_ui_case(case_id: int, _: AuthContext = Depends(require_menu("ui")), db: Session = Depends(get_db)):
    """Delete a UI test case and its run history."""
    case = db.get(UiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    db.query(TestRun).filter(TestRun.case_type == "ui", TestRun.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"status": "ok"}
