"""Visual case management, execution orchestration and authenticated artifacts."""

from datetime import datetime, timedelta
from pathlib import Path
import base64
import hashlib
import json
import random
import secrets
import shutil

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, require_menu
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import UiAutomationArtifact, UiAutomationCase, UiAutomationDataSet, UiAutomationFeature, UiAutomationRequirement, UiAutomationRun
from app.modules.online_preview.router import _jenkins_job_status, _remote_revision, _validate_branch

router = APIRouter(prefix="/v1/ui-automation", tags=["Emote UI 自动化"])
guard = Depends(require_menu("emote_ui_automation"))

FEATURES = [
    ("login", "登录"), ("register", "注册"), ("post", "发帖"), ("delete_post", "删帖"),
    ("like", "点赞"), ("comment", "评论"), ("favorite", "收藏"), ("friend", "添加好友"),
    ("chat", "聊天"), ("daily_task", "每日任务"), ("profile", "修改资料"),
]
LOGIN_TEMPLATE_STEPS = [
    {"action": "goto", "value": "/"},
    {"action": "assert_visible", "locator_type": "role", "role": "heading", "locator": "欢迎来到 Emote"},
    {"action": "click", "locator_type": "role", "role": "button", "locator": "同意并继续"},
    {"action": "click", "locator_type": "role", "role": "button", "locator": "登录"},
    {"action": "assert_visible", "locator_type": "role", "role": "heading", "locator": "登录"},
    {"action": "fill", "locator_type": "css", "locator": "div[style*='pointer-events: auto'] input[type='tel'][placeholder='手机号']", "value": "${account_a.username}"},
    {"action": "fill", "locator_type": "css", "locator": "div[style*='pointer-events: auto'] input[type='password']", "value": "${account_a.password}"},
    {"action": "click", "locator_type": "css", "locator": "form button[type='button']:has(+ p):visible"},
    {"action": "click", "locator_type": "role", "role": "button", "locator": "进入心灵花园"},
]
REGISTER_TEMPLATE_STEPS = [
    {"action": "goto", "value": "/"},
    {"action": "assert_visible", "locator_type": "role", "role": "heading", "locator": "欢迎来到 Emote"},
    {"action": "click", "locator_type": "role", "role": "button", "locator": "同意并继续"},
    {"action": "click", "locator_type": "role", "role": "button", "locator": "注册"},
    {"action": "assert_visible", "locator_type": "text", "locator": "注册"},
    {"action": "fill", "locator_type": "css", "locator": "div[style*='pointer-events: auto'] input[type='text']", "value": "AUTO-${run_id}"},
    {"action": "fill", "locator_type": "css", "locator": "div[style*='pointer-events: auto'] input[placeholder='手机号']", "value": "${registration.phone}"},
    {"action": "fill", "locator_type": "css", "locator": "div[style*='pointer-events: auto'] input[placeholder='验证码']", "value": "${registration.code}"},
    {"action": "screenshot"},
]


def _authenticated_steps(*feature_steps):
    """Every business case shows the complete login precondition before its own flow."""
    return [dict(step) for step in LOGIN_TEMPLATE_STEPS] + [dict(step) for step in feature_steps]


FEATURE_TEMPLATE_STEPS = {
    "login": LOGIN_TEMPLATE_STEPS,
    "register": REGISTER_TEMPLATE_STEPS,
    "post": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "发布心情"},
        {"action": "assert_visible", "locator_type": "text", "locator": "发布"},
        {"action": "screenshot"},
    ),
    "delete_post": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "我的"},
        {"action": "assert_visible", "locator_type": "text", "locator": "我的记录"},
        {"action": "screenshot"},
    ),
    "like": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "原野"},
        {"action": "assert_visible", "locator_type": "text", "locator": "原野"},
        {"action": "screenshot"},
    ),
    "comment": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "原野"},
        {"action": "assert_visible", "locator_type": "text", "locator": "添加评论..."},
        {"action": "screenshot"},
    ),
    "favorite": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "我的"},
        {"action": "click", "locator_type": "text", "locator": "收藏夹"},
        {"action": "assert_visible", "locator_type": "text", "locator": "珍藏回声"},
    ),
    "friend": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "连接"},
        {"action": "assert_visible", "locator_type": "text", "locator": "好友"},
        {"action": "assert_visible", "locator_type": "text", "locator": "灵魂推荐"},
    ),
    "chat": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "连接"},
        {"action": "assert_visible", "locator_type": "text", "locator": "好友"},
        {"action": "screenshot"},
    ),
    "daily_task": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "我的"},
        {"action": "click", "locator_type": "text", "locator": "每日任务"},
        {"action": "assert_visible", "locator_type": "text", "locator": "每日任务"},
    ),
    "profile": _authenticated_steps(
        {"action": "click", "locator_type": "text", "locator": "我的"},
        {"action": "click", "locator_type": "text", "locator": "编辑资料"},
        {"action": "assert_visible", "locator_type": "text", "locator": "个性签名"},
        {"action": "screenshot"},
    ),
}
SAFE_ACTIONS = {"goto", "click", "fill", "select", "check", "uncheck", "press", "wait", "assert_visible", "assert_text", "assert_url", "assert_count", "screenshot", "switch_account"}
SAFE_LOCATOR_TYPES = {"testid", "role", "label", "placeholder", "text", "alt", "title", "id", "css", "xpath"}


class RequirementInput(BaseModel):
    feature_id: int | None = None
    content: str = Field(min_length=2, max_length=5000)


class FeatureInput(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,59}$")
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    sort_order: int = 0


class CaseInput(BaseModel):
    feature_id: int
    requirement_id: int | None = None
    name: str = Field(min_length=2, max_length=200)
    priority: str = "P1"
    tags: list[str] = Field(default_factory=list)
    preconditions: str = ""
    cleanup_note: str = "保留测试数据"
    steps: list[dict] = Field(default_factory=list)
    enabled: bool = False


class RunInput(BaseModel):
    mode: str = "regression"
    branch: str = "dev-20260811-1.9.1"
    viewport: str = "mobile"
    case_ids: list[int] = Field(default_factory=list)
    smoke_count: int = Field(default=10, ge=1, le=50)
    random_seed: str | None = None
    data_set_id: int | None = None
    credentials: dict = Field(default_factory=dict)


class DataSetInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_default: bool = False
    credentials: dict = Field(default_factory=dict)


class RunnerUpdate(BaseModel):
    status: str
    current_step: str = ""
    progress: int = 0
    result_summary: dict = Field(default_factory=dict)
    error_message: str = ""
    artifacts: list[dict] = Field(default_factory=list)


def _seed(db: Session):
    if db.query(UiAutomationFeature).count():
        # Upgrade only the untouched first-version login template. User-edited cases
        # are never overwritten by this idempotent seed migration.
        login_feature = db.query(UiAutomationFeature).filter_by(key="login").first()
        login_case = db.query(UiAutomationCase).filter_by(feature_id=login_feature.id).order_by(UiAutomationCase.id).first() if login_feature else None
        legacy_steps = [{"value": "/", "action": "goto"}, {"action": "assert_visible", "locator": "登录", "locator_type": "text"}]
        changed = False
        if login_case and login_case.steps == legacy_steps:
            login_case.steps = LOGIN_TEMPLATE_STEPS
            login_case.preconditions = "运行前填写账号 A 的手机号和密码；脚本会逐步打开登录页、填写表单、勾选协议并点击登录。"
            changed = True
        elif login_case and len(login_case.steps or []) == 6 and (login_case.steps[2].get("locator") in {
            "input[type='tel']", "input[type='tel'][placeholder='手机号']:visible"
        } or "placeholder='请输入密码'" in login_case.steps[3].get("locator", "")):
            # Refine the first full-login template: hidden register/reset inputs also
            # exist in the DOM, so automation must target only the visible sign-in form.
            login_case.steps = LOGIN_TEMPLATE_STEPS
            changed = True
        for feature in db.query(UiAutomationFeature).all():
            case = db.query(UiAutomationCase).filter_by(feature_id=feature.id).order_by(UiAutomationCase.id).first()
            if case and case.steps == legacy_steps:
                case.steps = FEATURE_TEMPLATE_STEPS[feature.key]
                case.preconditions = "按页面提示填写运行时账号；脚本从登录或注册开始连续执行，每一步都会截图并生成本用例录像。"
                case.enabled = True
                changed = True
            elif (case and case.name == f"{feature.name}基础流程" and (
                  not any(step.get("locator") == "同意并继续" for step in (case.steps or []))
                  or (len(case.steps or []) > 1 and case.steps[1].get("locator") == "欢迎来到 Emote"
                      and case.steps[1].get("locator_type") == "text")
                  or (feature.key != "register" and not any(
                      step.get("action") == "click" and step.get("locator") == "登录" for step in (case.steps or [])
                  )) or any(step.get("action") == "assert_visible" and step.get("locator") == "登录"
                            and step.get("locator_type") == "text" for step in (case.steps or [])))):
                case.steps = FEATURE_TEMPLATE_STEPS[feature.key]
                changed = True
        if changed:
            db.commit()
        return
    for order, (key, name) in enumerate(FEATURES, 1):
        feature = UiAutomationFeature(key=key, name=name, description=f"Emote {name}核心流程", sort_order=order)
        db.add(feature)
        db.flush()
        db.add(UiAutomationCase(
            feature_id=feature.id, name=f"{name}基础流程", priority="P1", tags=["smoke", "regression"],
            preconditions="运行前填写所需测试账号；请根据当前页面补充定位步骤。", cleanup_note="保留测试数据",
            steps=FEATURE_TEMPLATE_STEPS[key],
            enabled=True,
        ))
    db.commit()


def _case_dict(case: UiAutomationCase):
    return {"id": case.id, "feature_id": case.feature_id, "requirement_id": case.requirement_id, "name": case.name,
            "priority": case.priority, "tags": case.tags, "preconditions": case.preconditions,
            "cleanup_note": case.cleanup_note, "steps": case.steps, "enabled": case.enabled,
            "updated_at": case.updated_at.isoformat() if case.updated_at else None}


def _run_dict(run: UiAutomationRun, db: Session):
    artifacts = db.query(UiAutomationArtifact).filter_by(run_id=run.id).order_by(UiAutomationArtifact.id).all()
    return {"id": run.id, "mode": run.mode, "branch": run.branch, "commit_sha": run.commit_sha,
            "viewport": run.viewport, "random_seed": run.random_seed, "status": run.status,
            "case_ids": run.case_ids, "current_step": run.current_step, "progress": run.progress,
            "result_summary": run.result_summary, "error_message": run.error_message,
            "started_at": run.started_at, "finished_at": run.finished_at, "created_at": run.created_at,
            "artifacts": [{"id": x.id, "kind": x.kind, "name": x.name,
                           "url": f"/v1/ui-automation/artifacts/{x.id}"} for x in artifacts]}


def _cleanup(db: Session):
    cutoff = datetime.utcnow() - timedelta(days=7)
    root = Path(get_settings().ui_automation_data_dir).resolve()
    for item in db.query(UiAutomationArtifact).filter(UiAutomationArtifact.created_at < cutoff).all():
        path = (root / item.stored_name).resolve()
        if path.is_relative_to(root):
            path.unlink(missing_ok=True)
        db.delete(item)
    db.commit()


def _validate_steps(steps: list[dict]):
    for index, step in enumerate(steps, 1):
        if step.get("action") not in SAFE_ACTIONS:
            raise HTTPException(400, f"第 {index} 步动作不允许")
        if step.get("action") == "fill" and not step.get("value") and not step.get("variable"):
            raise HTTPException(400, f"第 {index} 步缺少输入值或变量")
        locator_type = step.get("locator_type")
        if locator_type and locator_type not in SAFE_LOCATOR_TYPES:
            raise HTTPException(400, f"第 {index} 步定位方式不支持")
        if step.get("match") not in {None, "first", "last", "nth"}:
            raise HTTPException(400, f"第 {index} 步匹配方式不支持")
        if step.get("match") == "nth" and not isinstance(step.get("index"), int):
            raise HTTPException(400, f"第 {index} 步 nth 匹配需要填写从 0 开始的序号")


def _data_cipher() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().app_secret_key.encode()).digest())
    return Fernet(key)


def _encrypt_credentials(value: dict) -> str:
    return _data_cipher().encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()


def _decrypt_credentials(value: str) -> dict:
    try:
        return json.loads(_data_cipher().decrypt(value.encode()).decode())
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "测试数据集无法解密，请重新保存") from exc


def _data_set_dict(item: UiAutomationDataSet):
    data = _decrypt_credentials(item.encrypted_data)
    def masked(group):
        values = data.get(group, {}) if isinstance(data.get(group), dict) else {}
        return {key: ("******" if key in {"password", "code"} and value else value) for key, value in values.items()}
    return {"id": item.id, "name": item.name, "is_default": item.is_default,
            "credentials": {key: masked(key) for key in ("account_a", "account_b", "registration")},
            "updated_at": item.updated_at}


@router.get("/data-sets", dependencies=[guard])
def list_data_sets(db: Session = Depends(get_db)):
    return [_data_set_dict(item) for item in db.query(UiAutomationDataSet).order_by(UiAutomationDataSet.is_default.desc(), UiAutomationDataSet.id).all()]


@router.post("/data-sets", dependencies=[guard])
def create_data_set(payload: DataSetInput, db: Session = Depends(get_db)):
    if db.query(UiAutomationDataSet).filter_by(name=payload.name.strip()).first(): raise HTTPException(409, "数据集名称已存在")
    if payload.is_default: db.query(UiAutomationDataSet).update({UiAutomationDataSet.is_default: False})
    item = UiAutomationDataSet(name=payload.name.strip(), is_default=payload.is_default,
                               encrypted_data=_encrypt_credentials(payload.credentials))
    db.add(item); db.commit(); db.refresh(item)
    return _data_set_dict(item)


@router.put("/data-sets/{data_set_id}", dependencies=[guard])
def update_data_set(data_set_id: int, payload: DataSetInput, db: Session = Depends(get_db)):
    item = db.get(UiAutomationDataSet, data_set_id)
    if not item: raise HTTPException(404, "测试数据集不存在")
    old = _decrypt_credentials(item.encrypted_data)
    incoming = payload.credentials
    for group in ("account_a", "account_b", "registration"):
        for key, value in (incoming.get(group, {}) or {}).items():
            if value == "******": incoming[group][key] = (old.get(group, {}) or {}).get(key, "")
    if payload.is_default: db.query(UiAutomationDataSet).update({UiAutomationDataSet.is_default: False})
    item.name, item.is_default, item.encrypted_data = payload.name.strip(), payload.is_default, _encrypt_credentials(incoming)
    db.commit(); db.refresh(item)
    return _data_set_dict(item)


@router.delete("/data-sets/{data_set_id}", dependencies=[guard])
def delete_data_set(data_set_id: int, db: Session = Depends(get_db)):
    item = db.get(UiAutomationDataSet, data_set_id)
    if not item: raise HTTPException(404, "测试数据集不存在")
    db.delete(item); db.commit()
    return {"message": "测试数据集已删除"}


@router.get("/overview", dependencies=[guard])
def overview(db: Session = Depends(get_db)):
    _seed(db); _cleanup(db)
    features = db.query(UiAutomationFeature).order_by(UiAutomationFeature.sort_order).all()
    cases = db.query(UiAutomationCase).order_by(UiAutomationCase.id).all()
    requirements = db.query(UiAutomationRequirement).order_by(UiAutomationRequirement.id.desc()).all()
    runs = db.query(UiAutomationRun).order_by(UiAutomationRun.id.desc()).limit(30).all()
    return {"features": [{"id": x.id, "key": x.key, "name": x.name, "description": x.description} for x in features],
            "cases": [_case_dict(x) for x in cases],
            "requirements": [{"id": x.id, "feature_id": x.feature_id, "content": x.content, "status": x.status, "created_at": x.created_at} for x in requirements],
            "runs": [_run_dict(x, db) for x in runs]}


@router.post("/requirements", dependencies=[guard])
def create_requirement(payload: RequirementInput, db: Session = Depends(get_db)):
    item = UiAutomationRequirement(**payload.model_dump(), status="draft")
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "status": item.status}


@router.put("/requirements/{requirement_id}", dependencies=[guard])
def update_requirement(requirement_id: int, payload: RequirementInput, db: Session = Depends(get_db)):
    item = db.get(UiAutomationRequirement, requirement_id)
    if not item: raise HTTPException(404, "测试需求不存在")
    item.feature_id, item.content = payload.feature_id, payload.content
    db.commit()
    return {"id": item.id, "status": item.status}


@router.delete("/requirements/{requirement_id}", dependencies=[guard])
def delete_requirement(requirement_id: int, db: Session = Depends(get_db)):
    item = db.get(UiAutomationRequirement, requirement_id)
    if not item: raise HTTPException(404, "测试需求不存在")
    if db.query(UiAutomationCase).filter_by(requirement_id=item.id).first():
        raise HTTPException(409, "该需求已关联测试用例，不能删除")
    db.delete(item); db.commit()
    return {"message": "草稿已删除"}


@router.post("/features", dependencies=[guard])
def create_feature(payload: FeatureInput, db: Session = Depends(get_db)):
    if db.query(UiAutomationFeature).filter_by(key=payload.key).first(): raise HTTPException(409, "功能标识已存在")
    item = UiAutomationFeature(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, **payload.model_dump()}


@router.put("/features/{feature_id}", dependencies=[guard])
def update_feature(feature_id: int, payload: FeatureInput, db: Session = Depends(get_db)):
    item = db.get(UiAutomationFeature, feature_id)
    if not item: raise HTTPException(404, "功能不存在")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    db.commit()
    return {"id": item.id, **payload.model_dump()}


@router.delete("/features/{feature_id}", dependencies=[guard])
def delete_feature(feature_id: int, db: Session = Depends(get_db)):
    item = db.get(UiAutomationFeature, feature_id)
    if not item: raise HTTPException(404, "功能不存在")
    if db.query(UiAutomationCase).filter_by(feature_id=item.id).first(): raise HTTPException(409, "请先移动或删除该功能下的用例")
    db.delete(item); db.commit()
    return {"message": "功能已删除"}


@router.post("/cases", dependencies=[guard])
def create_case(payload: CaseInput, db: Session = Depends(get_db)):
    _validate_steps(payload.steps)
    item = UiAutomationCase(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return _case_dict(item)


@router.put("/cases/{case_id}", dependencies=[guard])
def update_case(case_id: int, payload: CaseInput, db: Session = Depends(get_db)):
    _validate_steps(payload.steps)
    item = db.get(UiAutomationCase, case_id)
    if not item: raise HTTPException(404, "用例不存在")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item)
    return _case_dict(item)


@router.post("/cases/{case_id}/duplicate", dependencies=[guard])
def duplicate_case(case_id: int, db: Session = Depends(get_db)):
    source = db.get(UiAutomationCase, case_id)
    if not source: raise HTTPException(404, "用例不存在")
    item = UiAutomationCase(feature_id=source.feature_id, name=source.name + "（副本）", priority=source.priority,
                            tags=source.tags, preconditions=source.preconditions, cleanup_note=source.cleanup_note,
                            steps=source.steps, enabled=False)
    db.add(item); db.commit(); db.refresh(item)
    return _case_dict(item)


@router.delete("/cases/{case_id}", dependencies=[guard])
def delete_case(case_id: int, db: Session = Depends(get_db)):
    item = db.get(UiAutomationCase, case_id)
    if not item: raise HTTPException(404, "用例不存在")
    db.delete(item); db.commit()
    return {"message": "用例已删除，历史执行证据不受影响"}


@router.post("/runs", dependencies=[guard])
def create_run(payload: RunInput, _: AuthContext = guard, db: Session = Depends(get_db)):
    if payload.mode not in {"regression", "selected", "smoke"} or payload.viewport not in {"desktop", "mobile"}:
        raise HTTPException(400, "执行模式或视口不合法")
    branch = _validate_branch(payload.branch)
    query = db.query(UiAutomationCase).filter(UiAutomationCase.enabled.is_(True))
    cases = query.filter(UiAutomationCase.id.in_(payload.case_ids)).all() if payload.case_ids else query.all()
    seed = payload.random_seed or secrets.token_hex(6)
    if payload.mode == "smoke":
        cases = [x for x in cases if "smoke" in (x.tags or [])]
        random.Random(seed).shuffle(cases)
        cases = cases[:payload.smoke_count]
    if not cases: raise HTTPException(400, "没有可执行的已启用用例")
    credentials = payload.credentials
    if payload.data_set_id:
        data_set = db.get(UiAutomationDataSet, payload.data_set_id)
        if not data_set: raise HTTPException(404, "所选测试数据集不存在")
        credentials = _decrypt_credentials(data_set.encrypted_data)
    # UI playback and APK compilation share a small production host. Queueing here would
    # retain credentials, so ask the user to retry after the resource-heavy job finishes.
    if _jenkins_job_status("emote-preview").get("building") or _jenkins_job_status("emote-apk").get("building"):
        raise HTTPException(409, "Jenkins 正在同步预览或构建 APK，请完成后再执行 UI 自动化")
    revision = _remote_revision(branch)
    run = UiAutomationRun(mode=payload.mode, branch=branch, commit_sha=revision["sha"], viewport=payload.viewport,
                          random_seed=seed, status="queued", case_ids=[x.id for x in cases])
    db.add(run); db.commit(); db.refresh(run)
    # Go through the public preview proxy so /emote-preview/* assets (including the
    # Logo) resolve exactly as they do for a user opening the preview website.
    runner_payload = {"run_id": run.id, "base_url": "http://frontend/emote-preview/", "viewport": payload.viewport,
                      "cases": [_case_dict(x) for x in cases], "credentials": credentials}
    settings = get_settings()
    try:
        response = httpx.post(f"{settings.ui_runner_url}/execute", json=runner_payload,
                              headers={"X-Runner-Token": settings.ui_runner_token or ""}, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        run.status = "failed"; run.error_message = "UI Runner 不可用"; run.finished_at = datetime.utcnow(); db.commit()
        raise HTTPException(502, "UI Runner 不可用，任务未执行") from exc
    return _run_dict(run, db)


@router.get("/runs/{run_id}", dependencies=[guard])
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(UiAutomationRun, run_id)
    if not run: raise HTTPException(404, "执行记录不存在")
    return _run_dict(run, db)


@router.get("/artifacts/{artifact_id}", dependencies=[guard])
def artifact(artifact_id: int, db: Session = Depends(get_db)):
    item = db.get(UiAutomationArtifact, artifact_id)
    if not item: raise HTTPException(404, "执行产物不存在")
    root = Path(get_settings().ui_automation_data_dir).resolve(); path = (root / item.stored_name).resolve()
    if not path.is_relative_to(root) or not path.is_file(): raise HTTPException(404, "执行产物文件不存在")
    return FileResponse(path, media_type=item.content_type, filename=item.name)


@router.delete("/maintenance/execution-data", dependencies=[guard])
def clear_execution_data(db: Session = Depends(get_db)):
    """Delete UI execution evidence and history while preserving cases and data sets."""
    active = db.query(UiAutomationRun).filter(UiAutomationRun.status.in_(["queued", "running"])).count()
    if active:
        raise HTTPException(409, "当前仍有自动化任务正在执行，请结束后再清理")
    root = Path(get_settings().ui_automation_data_dir).resolve()
    artifact_count = db.query(UiAutomationArtifact).count()
    run_count = db.query(UiAutomationRun).count()
    released_bytes = sum(value or 0 for (value,) in db.query(UiAutomationArtifact.size_bytes).all())
    # Resolve and inspect every child before deletion; never remove the configured
    # volume root itself, only the run directories/files beneath it.
    if root.is_dir():
        for child in root.iterdir():
            target = child.resolve()
            if not target.is_relative_to(root) or target == root:
                continue
            if target.is_dir(): shutil.rmtree(target)
            else: target.unlink(missing_ok=True)
    db.query(UiAutomationArtifact).delete(synchronize_session=False)
    db.query(UiAutomationRun).delete(synchronize_session=False)
    db.commit()
    return {"message": "自动化执行数据已清空", "runs": run_count,
            "artifacts": artifact_count, "released_bytes": released_bytes}


def _internal_auth(token: str | None):
    expected = get_settings().ui_runner_token
    if not expected or not secrets.compare_digest(token or "", expected): raise HTTPException(403, "Runner 凭据无效")


@router.put("/internal/runs/{run_id}")
def runner_update(run_id: int, payload: RunnerUpdate, x_runner_token: str | None = Header(None), db: Session = Depends(get_db)):
    _internal_auth(x_runner_token)
    run = db.get(UiAutomationRun, run_id)
    if not run: raise HTTPException(404, "执行记录不存在")
    run.status, run.current_step, run.progress = payload.status, payload.current_step[:300], max(0, min(100, payload.progress))
    run.result_summary, run.error_message = payload.result_summary, payload.error_message[:5000]
    if payload.status == "running" and not run.started_at: run.started_at = datetime.utcnow()
    if payload.status in {"passed", "failed", "interrupted"}: run.finished_at = datetime.utcnow()
    for artifact in payload.artifacts:
        if not db.query(UiAutomationArtifact).filter_by(stored_name=artifact["stored_name"]).first():
            db.add(UiAutomationArtifact(run_id=run.id, kind=artifact["kind"], name=artifact["name"],
                                        stored_name=artifact["stored_name"], content_type=artifact["content_type"],
                                        size_bytes=artifact.get("size_bytes", 0)))
    db.commit()
    return {"status": "ok"}
