"""WeChat identity, approval forms, employee requests, and administrator decisions."""

import hashlib
import json
import secrets
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, create_access_token, get_current_user, hash_password, verify_admin
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import AppUser, MiniProgramAccount, OaApprovalAction, OaApprovalRequest, OaApprovalTemplate
from app.modules.oa.service import request_number, request_response, seed_templates, template_response


router = APIRouter(prefix="/oa", tags=["小程序 OA"])


class WeChatCode(BaseModel):
    code: str = Field(min_length=1, max_length=256)


class DevLogin(BaseModel):
    display_name: str = Field(default="体验同事", min_length=1, max_length=80)


class CreateRequest(BaseModel):
    template_key: str = Field(min_length=1, max_length=60)
    form_data: dict = Field(default_factory=dict)


class DecideRequest(BaseModel):
    action: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=500)

class AccountUpdate(BaseModel):
    is_enabled: bool
    is_reviewer: bool

class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


def _account_token(user: AppUser) -> dict:
    return {"access_token": create_access_token(user.username, is_admin=user.is_admin), "user": {"name": user.display_name or user.username, "is_admin": user.is_admin, "is_reviewer": user.is_admin or "oa_reviewer" in (user.menu_permissions or [])}}


def _get_or_create_wechat_user(db: Session, openid: str, display_name: str = "微信同事") -> AppUser:
    account = db.query(MiniProgramAccount).filter(MiniProgramAccount.openid == openid).first()
    if account:
        user = db.get(AppUser, account.app_user_id)
        if not account.is_enabled or not user or not user.is_active:
            raise HTTPException(status_code=403, detail="该小程序账号已停用，请联系管理员")
        return user
    username = f"wx_{hashlib.sha256(openid.encode()).hexdigest()[:24]}"
    user = AppUser(username=username, display_name=display_name, password_hash=hash_password(secrets.token_urlsafe(32)), is_admin=False, is_active=True, menu_permissions=[])
    db.add(user)
    db.flush()
    db.add(MiniProgramAccount(app_user_id=user.id, openid=openid, is_enabled=True))
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/wechat-login", summary="微信 code 换取 OA 小程序会话")
def wechat_login(payload: WeChatCode, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.wechat_miniprogram_app_id or not settings.wechat_miniprogram_app_secret:
        raise HTTPException(status_code=503, detail="小程序微信授权尚未配置")
    query = urlencode({"appid": settings.wechat_miniprogram_app_id, "secret": settings.wechat_miniprogram_app_secret, "js_code": payload.code, "grant_type": "authorization_code"})
    try:
        with urlopen(f"https://api.weixin.qq.com/sns/jscode2session?{query}", timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
    except OSError as exc:
        raise HTTPException(status_code=502, detail="微信授权服务暂不可用") from exc
    if not result.get("openid"):
        raise HTTPException(status_code=401, detail=result.get("errmsg", "微信授权失败"))
    return _account_token(_get_or_create_wechat_user(db, result["openid"]))


@router.post("/auth/dev-login", summary="开发者工具体验登录")
def dev_login(payload: DevLogin, db: Session = Depends(get_db)):
    if get_settings().app_env == "production":
        raise HTTPException(status_code=404, detail="体验登录仅在开发环境可用")
    return _account_token(_get_or_create_wechat_user(db, f"dev:{payload.display_name.strip()}", payload.display_name.strip()))


@router.get("/templates", summary="读取可发起的审批模板")
def list_templates(_: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    seed_templates(db)
    templates = db.query(OaApprovalTemplate).filter(OaApprovalTemplate.is_active.is_(True)).order_by(OaApprovalTemplate.sort_order).all()
    return [template_response(item) for item in templates]

@router.get("/profile", summary="读取小程序个人资料")
def get_profile(current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == user.id).first()
    return {"name": user.display_name or user.username, "department": account.department if account else "", "is_reviewer": user.is_admin or "oa_reviewer" in (user.menu_permissions or [])}

@router.put("/profile", summary="修改小程序个人资料")
def update_profile(payload: ProfileUpdate, current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    user.display_name = payload.display_name.strip()
    db.commit()
    return _account_token(user)


@router.post("/requests", summary="提交审批申请")
def create_request(payload: CreateRequest, current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    seed_templates(db)
    template = db.query(OaApprovalTemplate).filter(OaApprovalTemplate.key == payload.template_key, OaApprovalTemplate.is_active.is_(True)).first()
    if not template:
        raise HTTPException(status_code=404, detail="审批模板不存在或已停用")
    missing = [field["label"] for field in template.fields if field.get("required") and not str(payload.form_data.get(field["key"], "")).strip()]
    if missing:
        raise HTTPException(status_code=422, detail=f"请填写：{'、'.join(missing)}")
    requester = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    approver = next((item for item in db.query(AppUser).filter(AppUser.is_active.is_(True)).order_by(AppUser.id).all() if item.is_admin or "oa_reviewer" in (item.menu_permissions or [])), None)
    request = OaApprovalRequest(template_id=template.id, requester_user_id=requester.id, request_no=request_number(), title=template.name, form_data=payload.form_data, current_approver_user_id=approver.id if approver else None)
    db.add(request)
    db.flush()
    db.add(OaApprovalAction(request_id=request.id, actor_user_id=requester.id, action="submitted", comment="已提交申请"))
    db.commit()
    return {"id": request.id, "request_no": request.request_no, "status": request.status}


@router.get("/requests", summary="查询我的申请或管理员待办")
def list_requests(scope: str = "mine", current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    query = db.query(OaApprovalRequest)
    if scope == "pending" and current_user.is_admin:
        query = query.filter(OaApprovalRequest.status == "pending")
    else:
        query = query.filter(OaApprovalRequest.requester_user_id == user.id)
    rows = query.order_by(OaApprovalRequest.created_at.desc()).all()
    templates = {item.id: item for item in db.query(OaApprovalTemplate).all()}
    users = {item.id: item for item in db.query(AppUser).all()}
    actions = db.query(OaApprovalAction).filter(OaApprovalAction.request_id.in_([item.id for item in rows] or [-1])).order_by(OaApprovalAction.created_at).all()
    grouped = {item.id: [] for item in rows}
    for action in actions: grouped.setdefault(action.request_id, []).append(action)
    return [request_response(item, templates[item.template_id], users[item.requester_user_id], grouped[item.id], users) for item in rows]


@router.post("/requests/{request_id}/decision", summary="审核人审批申请")
def decide_request(request_id: int, payload: DecideRequest, current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    request = db.get(OaApprovalRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="申请单不存在")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="该申请已处理")
    actor = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    if not actor.is_admin and "oa_reviewer" not in (actor.menu_permissions or []):
        raise HTTPException(status_code=403, detail="需要审核人权限")
    request.status = payload.action
    request.current_approver_user_id = actor.id
    request.completed_at = datetime.utcnow()
    db.add(OaApprovalAction(request_id=request.id, actor_user_id=actor.id, action=payload.action, comment=payload.comment.strip()))
    db.commit()
    return {"id": request.id, "status": request.status}


@router.get("/admin/accounts", summary="管理员查询小程序账号")
def list_mini_accounts(_: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    accounts = db.query(MiniProgramAccount).order_by(MiniProgramAccount.created_at.desc()).all()
    users = {item.id: item for item in db.query(AppUser).all()}
    return [{"id": item.id, "name": (users[item.app_user_id].display_name or users[item.app_user_id].username), "department": item.department, "is_enabled": item.is_enabled, "is_reviewer": users[item.app_user_id].is_admin or "oa_reviewer" in (users[item.app_user_id].menu_permissions or []), "created_at": item.created_at.isoformat()} for item in accounts if item.app_user_id in users]

@router.put("/admin/accounts/{account_id}", summary="设置小程序账号和审核人权限")
def update_mini_account(account_id: int, payload: AccountUpdate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    account = db.get(MiniProgramAccount, account_id)
    if not account: raise HTTPException(status_code=404, detail="小程序账号不存在")
    user = db.get(AppUser, account.app_user_id)
    account.is_enabled = payload.is_enabled
    permissions = set(user.menu_permissions or [])
    if payload.is_reviewer: permissions.add("oa_reviewer")
    else: permissions.discard("oa_reviewer")
    user.menu_permissions = list(permissions)
    db.commit()
    return {"status": "ok"}
