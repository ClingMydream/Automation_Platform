"""WeChat identity, approval forms, employee requests, and administrator decisions."""

import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, create_access_token, get_current_user, hash_password, verify_admin, verify_password
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import AppUser, MiniProgramAccount, OaAccountReviewer, OaApprovalAction, OaApprovalRequest, OaApprovalTemplate
from app.modules.oa.service import request_number, request_response, seed_templates, template_response


router = APIRouter(prefix="/oa", tags=["小程序 OA"])


class WeChatCode(BaseModel):
    code: str = Field(min_length=1, max_length=256)


class DevLogin(BaseModel):
    display_name: str = Field(default="体验同事", min_length=1, max_length=80)


class AccountLogin(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=160)


class CreateRequest(BaseModel):
    template_key: str = Field(min_length=1, max_length=60)
    form_data: dict = Field(default_factory=dict)


class DecideRequest(BaseModel):
    action: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=500)

class AccountCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=160)
    display_name: str = Field(min_length=1, max_length=80)
    family_role: str = Field(default="家庭成员", min_length=1, max_length=40)
    is_enabled: bool = True
    approver_account_ids: list[int] = Field(default_factory=list)


class AccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    family_role: str | None = Field(default=None, min_length=1, max_length=40)
    password: str | None = Field(default=None, min_length=6, max_length=160)
    is_enabled: bool
    approver_account_ids: list[int] = Field(default_factory=list)

class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    family_role: str = Field(default="家庭成员", min_length=1, max_length=40)


def _is_reviewer(db: Session, user: AppUser) -> bool:
    account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == user.id).first()
    return bool(user.is_admin or (account and db.query(OaAccountReviewer).filter(OaAccountReviewer.reviewer_account_id == account.id).first()))


def _profile_data(db: Session, user: AppUser, is_reviewer: bool | None = None) -> dict:
    account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == user.id).first()
    return {
        "name": user.display_name or user.username,
        "avatar_url": account.avatar_url if account else "",
        "family_role": (account.department or "家庭成员") if account else "家庭成员",
        "is_admin": user.is_admin,
        "is_reviewer": _is_reviewer(db, user) if is_reviewer is None else is_reviewer,
    }


def _account_token(db: Session, user: AppUser, is_reviewer: bool = False) -> dict:
    return {"access_token": create_access_token(user.username, is_admin=user.is_admin), "user": _profile_data(db, user, is_reviewer)}


def _validate_reviewer_accounts(db: Session, account_id: int, reviewer_account_ids: list[int]) -> list[int]:
    """Validate a person's independently selected reviewer list."""
    selected_ids = list(dict.fromkeys(reviewer_account_ids))
    if account_id in selected_ids:
        raise HTTPException(status_code=422, detail="不能将自己设为自己的审核人")
    accounts = {item.id: item for item in db.query(MiniProgramAccount).all()}
    if any(item not in accounts or not accounts[item].is_enabled for item in selected_ids):
        raise HTTPException(status_code=422, detail="审核人必须是已启用的小程序用户")
    return selected_ids


def _replace_reviewers(db: Session, account_id: int, reviewer_account_ids: list[int]) -> None:
    selected_ids = _validate_reviewer_accounts(db, account_id, reviewer_account_ids)
    db.query(OaAccountReviewer).filter(OaAccountReviewer.account_id == account_id).delete(synchronize_session=False)
    for reviewer_account_id in selected_ids:
        db.add(OaAccountReviewer(account_id=account_id, reviewer_account_id=reviewer_account_id))


def _avatar_directory() -> Path:
    directory = Path(get_settings().file_transfer_dir) / "oa-avatars"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


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


def _ensure_account_login_record(db: Session, user: AppUser) -> AppUser:
    """Register a platform-account sign-in as a Mini Program OA user on first use."""
    account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == user.id).first()
    if account is None:
        # `openid` predates account sign-in and is non-null in existing installations.
        # A namespaced internal identity keeps the one-account-per-user constraint intact.
        account = MiniProgramAccount(app_user_id=user.id, openid=f"account:{user.id}", is_enabled=True)
        db.add(account)
        db.commit()
    if not account.is_enabled:
        raise HTTPException(status_code=403, detail="该小程序账号已停用，请联系管理员")
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
    user = _get_or_create_wechat_user(db, result["openid"])
    return _account_token(db, user, _is_reviewer(db, user))


@router.post("/auth/account-login", summary="账号密码登录 OA 小程序")
def account_login(payload: AccountLogin, db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.username == payload.username.strip()).first()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    user = _ensure_account_login_record(db, user)
    return _account_token(db, user, _is_reviewer(db, user))


@router.post("/auth/dev-login", summary="开发者工具体验登录")
def dev_login(payload: DevLogin, db: Session = Depends(get_db)):
    if get_settings().app_env == "production":
        raise HTTPException(status_code=404, detail="体验登录仅在开发环境可用")
    user = _get_or_create_wechat_user(db, f"dev:{payload.display_name.strip()}", payload.display_name.strip())
    return _account_token(db, user, _is_reviewer(db, user))


@router.get("/templates", summary="读取可发起的审批模板")
def list_templates(_: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    seed_templates(db)
    templates = db.query(OaApprovalTemplate).filter(OaApprovalTemplate.is_active.is_(True)).order_by(OaApprovalTemplate.sort_order).all()
    return [template_response(item) for item in templates]

@router.get("/profile", summary="读取小程序个人资料")
def get_profile(current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    return _profile_data(db, user)

@router.put("/profile", summary="修改小程序个人资料")
def update_profile(payload: ProfileUpdate, current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == user.id).first()
    user.display_name = payload.display_name.strip()
    if account:
        account.department = payload.family_role.strip()
    db.commit()
    return _account_token(db, user, _is_reviewer(db, user))


@router.post("/profile/avatar", summary="上传小程序头像")
async def upload_profile_avatar(file: UploadFile = File(...), current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="头像仅支持 JPG、PNG 或 WebP 图片")
    content = await file.read(2 * 1024 * 1024 + 1)
    if not content or len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="头像图片不能超过 2MB")
    user = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="小程序账号不存在")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[file.content_type]
    filename = f"{account.id}-{uuid4().hex}.{extension}"
    (_avatar_directory() / filename).write_bytes(content)
    account.avatar_url = f"{get_settings().public_base_url.rstrip('/')}/api/oa/avatars/{filename}"
    db.commit()
    return {"avatar_url": account.avatar_url}


@router.get("/avatars/{filename}", summary="读取小程序头像")
def get_profile_avatar(filename: str):
    if Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="头像不存在")
    path = _avatar_directory() / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="头像不存在")
    media_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower())
    if not media_type:
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(path, media_type=media_type, content_disposition_type="inline")


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
    requester_account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == requester.id).first()
    reviewer_links = db.query(OaAccountReviewer).filter(OaAccountReviewer.account_id == requester_account.id).all() if requester_account else []
    reviewer_accounts = db.query(MiniProgramAccount).filter(MiniProgramAccount.id.in_([item.reviewer_account_id for item in reviewer_links] or [-1]), MiniProgramAccount.is_enabled.is_(True)).all()
    reviewer_users = {item.id: item for item in db.query(AppUser).filter(AppUser.id.in_([item.app_user_id for item in reviewer_accounts] or [-1]), AppUser.is_active.is_(True)).all()}
    approver = next((reviewer_users.get(item.app_user_id) for item in reviewer_accounts if reviewer_users.get(item.app_user_id)), None)
    if not approver:
        raise HTTPException(status_code=422, detail="请先在后台为该账号选择审核人")
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
    if scope == "pending" and _is_reviewer(db, user):
        if not user.is_admin:
            reviewer_account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == user.id).first()
            requester_accounts = db.query(OaAccountReviewer.account_id).filter(OaAccountReviewer.reviewer_account_id == reviewer_account.id).all() if reviewer_account else []
            requester_user_ids = [item.app_user_id for item in db.query(MiniProgramAccount).filter(MiniProgramAccount.id.in_([item[0] for item in requester_accounts] or [-1])).all()]
            query = query.filter(OaApprovalRequest.status == "pending", OaApprovalRequest.requester_user_id.in_(requester_user_ids or [-1]))
        else:
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
    requester_account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == request.requester_user_id).first()
    actor_account = db.query(MiniProgramAccount).filter(MiniProgramAccount.app_user_id == actor.id).first()
    allowed = actor.is_admin or (requester_account and actor_account and db.query(OaAccountReviewer).filter(OaAccountReviewer.account_id == requester_account.id, OaAccountReviewer.reviewer_account_id == actor_account.id).first())
    if not allowed:
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
    reviewer_map: dict[int, list[int]] = {}
    for link in db.query(OaAccountReviewer).all(): reviewer_map.setdefault(link.account_id, []).append(link.reviewer_account_id)
    return {"accounts": [{"id": item.id, "name": (users[item.app_user_id].display_name or users[item.app_user_id].username), "username": users[item.app_user_id].username, "login_method": "账号登录" if item.openid.startswith("account:") else "微信一键登录", "family_role": item.department or "家庭成员", "is_enabled": item.is_enabled, "approver_account_ids": reviewer_map.get(item.id, []), "created_at": item.created_at.isoformat()} for item in accounts if item.app_user_id in users]}


@router.post("/admin/accounts", summary="管理员新增小程序账号")
def create_mini_account(payload: AccountCreate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    username = payload.username.strip()
    if db.query(AppUser).filter(AppUser.username == username).first():
        raise HTTPException(status_code=409, detail="登录账号已存在")
    user = AppUser(username=username, display_name=payload.display_name.strip(), password_hash=hash_password(payload.password), is_admin=False, is_active=True, menu_permissions=[])
    db.add(user)
    db.flush()
    account = MiniProgramAccount(app_user_id=user.id, openid=f"account:{uuid4().hex}", department=payload.family_role.strip(), is_enabled=payload.is_enabled)
    db.add(account)
    db.flush()
    _replace_reviewers(db, account.id, payload.approver_account_ids)
    db.commit()
    return {"id": account.id, "status": "created"}

@router.put("/admin/accounts/{account_id}", summary="管理员修改小程序账号")
def update_mini_account(account_id: int, payload: AccountUpdate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    account = db.get(MiniProgramAccount, account_id)
    if not account: raise HTTPException(status_code=404, detail="小程序账号不存在")
    user = db.get(AppUser, account.app_user_id)
    if not user: raise HTTPException(status_code=404, detail="关联用户不存在")
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.family_role is not None:
        account.department = payload.family_role.strip()
    if payload.password is not None:
        if not account.openid.startswith("account:"):
            raise HTTPException(status_code=422, detail="微信一键登录账号不支持设置密码")
        user.password_hash = hash_password(payload.password)
    account.is_enabled = payload.is_enabled
    _replace_reviewers(db, account.id, payload.approver_account_ids)
    if not payload.is_enabled:
        db.query(OaAccountReviewer).filter(OaAccountReviewer.reviewer_account_id == account.id).delete(synchronize_session=False)
    db.commit()
    return {"status": "ok"}


@router.delete("/admin/accounts/{account_id}", summary="管理员删除小程序账号")
def delete_mini_account(account_id: int, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    account = db.get(MiniProgramAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="小程序账号不存在")
    user = db.get(AppUser, account.app_user_id)
    if user and user.is_admin:
        raise HTTPException(status_code=422, detail="系统管理员账号不能在这里删除")
    # Preserve historical approval records while removing the OA identity and
    # preventing either account or WeChat login from recreating it.
    if user:
        user.is_active = False
    db.delete(account)
    db.commit()
    return {"status": "deleted"}
