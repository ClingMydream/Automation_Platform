import secrets
import shutil
from base64 import b64encode
from datetime import datetime, timedelta
from html import escape
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, create_access_token, ensure_admin_user, get_current_user, hash_password, require_menu, verify_admin, verify_password
from app.core.config import get_settings
from app.core.menu import ADMIN_MENU, ADMIN_MENU_KEYS, ALL_MENU_KEYS, MENU_OPTIONS
from app.core.target_guard import validate_public_http_url
from app.db import get_db
from app.models.entities import ApiCase, AppUser, Environment, FileTransfer, Project, TestRun, UiCase
from app.schemas.entities import (
    ApiCaseCreate,
    ApiCaseRead,
    EnvironmentCreate,
    EnvironmentRead,
    LoginRequest,
    MeResponse,
    ProjectCreate,
    ProjectRead,
    RunCreate,
    RunRead,
    TokenResponse,
    UiCaseCreate,
    UiCaseRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.queue import enqueue_run


router = APIRouter()


IMAGE_FORMATS = {
    "png": {"label": "PNG", "mime": "image/png", "ext": "png", "pillow": "PNG"},
    "jpeg": {"label": "JPEG", "mime": "image/jpeg", "ext": "jpg", "pillow": "JPEG"},
    "webp": {"label": "WEBP", "mime": "image/webp", "ext": "webp", "pillow": "WEBP"},
    "gif": {"label": "GIF", "mime": "image/gif", "ext": "gif", "pillow": "GIF"},
    "bmp": {"label": "BMP", "mime": "image/bmp", "ext": "bmp", "pillow": "BMP"},
    "tiff": {"label": "TIFF", "mime": "image/tiff", "ext": "tiff", "pillow": "TIFF"},
    "svg": {"label": "SVG", "mime": "image/svg+xml", "ext": "svg", "pillow": None},
}


class ImageGenerateRequest(BaseModel):
    width: int = Field(default=1080, ge=32, le=8192)
    height: int = Field(default=1080, ge=32, le=8192)
    background_color: str = "#ffffff"
    text: str = ""
    text_color: str = "#17202a"
    font_size: int = Field(default=72, ge=8, le=512)
    format: str = "png"
    quality: int = Field(default=92, ge=1, le=100)
    max_kb: int | None = Field(default=None, ge=10, le=1024 * 20)


def _transfer_dir() -> Path:
    settings = get_settings()
    path = Path(settings.file_transfer_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clean_filename(name: str) -> str:
    cleaned = Path(name or "file").name.strip().replace("\x00", "")
    return cleaned[:255] or "file"


def _normalize_menu_permissions(values: list[str]) -> list[str]:
    seen = []
    for value in values or []:
        if value in ALL_MENU_KEYS and value != "users" and value not in seen:
            seen.append(value)
    if ("api" in seen or "ui" in seen) and "projects" not in seen:
        seen.insert(0, "projects")
    return seen


def _user_response(user: AppUser) -> dict:
    permissions = ADMIN_MENU_KEYS if user.is_admin else list(user.menu_permissions or [])
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "menu_permissions": permissions,
        "created_at": user.created_at,
    }


def _case_name_for_run(db: Session, run: TestRun) -> str:
    model = ApiCase if run.case_type == "api" else UiCase
    case = db.get(model, run.case_id)
    return case.name if case else f"已删除用例 #{run.case_id}"


def _report_summary(run: TestRun, case_name: str) -> dict:
    report = run.report or {}
    checks = report.get("checks") or []
    events = report.get("events") or []
    screenshots = report.get("screenshots") or []
    return {
        "id": run.id,
        "case_type": run.case_type,
        "case_id": run.case_id,
        "case_name": case_name,
        "status": run.status,
        "passed": report.get("passed") if report else run.status == "passed",
        "duration_ms": run.duration_ms,
        "logs": run.logs,
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "check_count": len(checks),
        "event_count": len(events),
        "screenshot_count": len(screenshots),
        "summary": {
            "request": report.get("request"),
            "response_status": (report.get("response") or {}).get("status_code"),
            "current_step": report.get("current_step"),
            "total_steps": report.get("total_steps"),
        },
        "report": report,
    }


def _image_format(format_name: str) -> dict:
    key = (format_name or "png").lower().strip()
    if key == "jpg":
        key = "jpeg"
    config = IMAGE_FORMATS.get(key)
    if config is None:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    return {**config, "key": key}


def _safe_color(value: str, fallback: str) -> str:
    value = (value or "").strip()
    if value.startswith("#") and len(value) in {4, 7}:
        return value
    return fallback


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default(size=size)


def _draw_center_text(image: Image.Image, text: str, color: str, font_size: int) -> None:
    if not text:
        return
    draw = ImageDraw.Draw(image)
    font = _font(font_size)
    lines = text.splitlines() or [text]
    spacing = max(6, font_size // 4)
    boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    widths = [box[2] - box[0] for box in boxes]
    heights = [box[3] - box[1] for box in boxes]
    total_height = sum(heights) + spacing * (len(lines) - 1)
    y = max(0, (image.height - total_height) / 2)
    for line, width, height in zip(lines, widths, heights):
        x = max(0, (image.width - width) / 2)
        draw.text((x, y), line, fill=color, font=font)
        y += height + spacing


def _svg_response(width: int, height: int, background: str, text: str, text_color: str, font_size: int) -> bytes:
    lines = text.splitlines() or [""]
    spacing = max(8, font_size // 3)
    total_height = font_size * len(lines) + spacing * (len(lines) - 1)
    first_y = height / 2 - total_height / 2 + font_size
    text_nodes = []
    for index, line in enumerate(lines):
        y = first_y + index * (font_size + spacing)
        text_nodes.append(
            f'<text x="50%" y="{y:.1f}" text-anchor="middle" font-family="Arial, Noto Sans CJK SC, sans-serif" '
            f'font-size="{font_size}" fill="{escape(text_color)}">{escape(line)}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="{escape(background)}"/>'
        f'{"".join(text_nodes)}</svg>'
    )
    return svg.encode("utf-8")


def _image_as_svg(image: Image.Image, filename: str) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    data = b64encode(buffer.getvalue()).decode("ascii")
    name = escape(filename)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{image.width}" height="{image.height}" '
        f'viewBox="0 0 {image.width} {image.height}">'
        f'<title>{name}</title>'
        f'<image width="{image.width}" height="{image.height}" href="data:image/png;base64,{data}"/></svg>'
    ).encode("utf-8")


def _serialize_image(image: Image.Image, format_name: str, quality: int, max_kb: int | None, filename: str) -> Response:
    config = _image_format(format_name)
    if config["key"] == "svg":
        payload = _image_as_svg(image, filename)
    else:
        save_image = image
        if config["key"] in {"jpeg", "bmp"} and save_image.mode in {"RGBA", "LA", "P"}:
            background = Image.new("RGB", save_image.size, "#ffffff")
            if save_image.mode == "P":
                save_image = save_image.convert("RGBA")
            background.paste(save_image, mask=save_image.split()[-1] if save_image.mode in {"RGBA", "LA"} else None)
            save_image = background
        elif config["key"] == "gif":
            save_image = save_image.convert("P", palette=Image.Palette.ADAPTIVE)
        elif save_image.mode not in {"RGB", "RGBA"}:
            save_image = save_image.convert("RGBA")

        payload = b""
        quality_values = [quality]
        if max_kb and config["key"] in {"jpeg", "webp"}:
            quality_values = list(range(quality, 19, -8))
        for current_quality in quality_values:
            buffer = BytesIO()
            kwargs = {"format": config["pillow"]}
            if config["key"] in {"jpeg", "webp"}:
                kwargs.update({"quality": current_quality, "optimize": True})
            elif config["key"] == "png":
                kwargs.update({"optimize": True})
            save_image.save(buffer, **kwargs)
            payload = buffer.getvalue()
            if not max_kb or len(payload) <= max_kb * 1024:
                break

    headers = {"Content-Disposition": f'attachment; filename="{filename}.{config["ext"]}"'}
    return Response(content=payload, media_type=config["mime"], headers=headers)


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


# 基础健康检查：Docker 和反向代理用它判断后端是否可用。
@router.get("/health")
def health():
    return {"status": "ok"}


# 登录认证：只负责登录、退出、当前用户信息，不放业务功能。
@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    if payload.username == settings.admin_username and payload.password == settings.admin_password:
        admin = ensure_admin_user(db)
        return TokenResponse(access_token=create_access_token(admin.username, is_admin=True))
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user.username, is_admin=user.is_admin))


@router.post("/auth/logout")
def logout(_: AuthContext = Depends(get_current_user)):
    return {"status": "ok"}


@router.get("/auth/me", response_model=MeResponse)
def me(current_user: AuthContext = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "is_admin": current_user.is_admin,
        "menu_permissions": current_user.menu_permissions,
    }


# 用户管理：管理员专属，用来维护登录账号和菜单权限。
@router.get("/menu-options")
def menu_options(_: AuthContext = Depends(verify_admin)):
    return MENU_OPTIONS


@router.get("/users", response_model=list[UserRead])
def list_users(_: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    ensure_admin_user(db)
    users = db.query(AppUser).order_by(AppUser.is_admin.desc(), AppUser.id.desc()).all()
    return [_user_response(user) for user in users]


@router.post("/users", response_model=UserRead)
def create_user(payload: UserCreate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    username = payload.username.strip()
    if username == get_settings().admin_username:
        raise HTTPException(status_code=400, detail="This username is reserved")
    if db.query(AppUser).filter(AppUser.username == username).first() is not None:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = AppUser(
        username=username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        is_admin=False,
        is_active=payload.is_active,
        menu_permissions=_normalize_menu_permissions(payload.menu_permissions),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        user.display_name = payload.display_name or user.display_name
        user.is_active = True
        user.menu_permissions = ADMIN_MENU_KEYS
    else:
        user.display_name = payload.display_name
        user.is_active = payload.is_active
        user.menu_permissions = _normalize_menu_permissions(payload.menu_permissions)
    if payload.password:
        user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, _: AuthContext = Depends(verify_admin), db: Session = Depends(get_db)):
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Admin user cannot be deleted")
    db.delete(user)
    db.commit()
    return {"status": "ok"}


# 项目与环境：接口用例和 UI 用例都依赖项目，所以权限归到 projects。
@router.get("/projects", response_model=list[ProjectRead])
def list_projects(_: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id.desc()).all()


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in payload.model_dump().items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
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
def list_environments(_: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    return db.query(Environment).order_by(Environment.id.desc()).all()


@router.post("/environments", response_model=EnvironmentRead)
def create_environment(payload: EnvironmentCreate, _: AuthContext = Depends(require_menu("projects")), db: Session = Depends(get_db)):
    validate_public_http_url(payload.base_url)
    environment = Environment(**payload.model_dump())
    db.add(environment)
    db.commit()
    db.refresh(environment)
    return environment


# 接口测试用例：这里只保存用例配置，真正执行由 worker 完成。
@router.get("/api-cases", response_model=list[ApiCaseRead])
def list_api_cases(_: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    return db.query(ApiCase).order_by(ApiCase.id.desc()).all()


@router.post("/api-cases", response_model=ApiCaseRead)
def create_api_case(payload: ApiCaseCreate, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
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
def delete_api_case(case_id: int, _: AuthContext = Depends(require_menu("api")), db: Session = Depends(get_db)):
    case = db.get(ApiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    db.query(TestRun).filter(TestRun.case_type == "api", TestRun.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"status": "ok"}


# UI 测试用例：保存低代码步骤 JSON，执行时由 worker 调用 Playwright。
@router.get("/ui-cases", response_model=list[UiCaseRead])
def list_ui_cases(_: AuthContext = Depends(require_menu("ui")), db: Session = Depends(get_db)):
    return db.query(UiCase).order_by(UiCase.id.desc()).all()


@router.post("/ui-cases", response_model=UiCaseRead)
def create_ui_case(payload: UiCaseCreate, _: AuthContext = Depends(require_menu("ui")), db: Session = Depends(get_db)):
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
def update_ui_case(case_id: int, payload: UiCaseCreate, _: AuthContext = Depends(require_menu("ui")), db: Session = Depends(get_db)):
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
def delete_ui_case(case_id: int, _: AuthContext = Depends(require_menu("ui")), db: Session = Depends(get_db)):
    case = db.get(UiCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    db.query(TestRun).filter(TestRun.case_type == "ui", TestRun.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"status": "ok"}


# 文件快传：后台上传文件生成二维码，公开 token 页面用于手机下载/回传。
@router.get("/file-transfers")
def list_file_transfers(_: AuthContext = Depends(require_menu("files")), db: Session = Depends(get_db)):
    _cleanup_expired(db)
    items = db.query(FileTransfer).order_by(FileTransfer.id.desc()).limit(100).all()
    return [_file_response(item) for item in items]


@router.post("/file-transfers")
def upload_file_transfer(
    file: UploadFile = File(...),
    expires_hours: int = Query(default=24, ge=1, le=168),
    _: AuthContext = Depends(require_menu("files")),
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
def delete_file_transfer(transfer_id: int, _: AuthContext = Depends(require_menu("files")), db: Session = Depends(get_db)):
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


# 图片工具：后端负责真实图片处理，前端只负责收集参数和下载结果。
@router.get("/image-tools/formats")
def list_image_formats(_: AuthContext = Depends(require_menu("images"))):
    return [
        {
            "value": key,
            "label": value["label"],
            "mime": value["mime"],
            "extension": value["ext"],
        }
        for key, value in IMAGE_FORMATS.items()
    ]


@router.post("/image-tools/generate")
def generate_image(payload: ImageGenerateRequest, _: AuthContext = Depends(require_menu("images"))):
    config = _image_format(payload.format)
    background = _safe_color(payload.background_color, "#ffffff")
    text_color = _safe_color(payload.text_color, "#17202a")
    filename = f"generated-{payload.width}x{payload.height}"
    if config["key"] == "svg":
        svg = _svg_response(payload.width, payload.height, background, payload.text, text_color, payload.font_size)
        return Response(
            content=svg,
            media_type=config["mime"],
            headers={"Content-Disposition": f'attachment; filename="{filename}.{config["ext"]}"'},
        )
    image = Image.new("RGB", (payload.width, payload.height), background)
    _draw_center_text(image, payload.text, text_color, payload.font_size)
    return _serialize_image(image, payload.format, payload.quality, payload.max_kb, filename)


@router.post("/image-tools/process")
def process_image(
    file: UploadFile = File(...),
    crop_x: int = Form(default=0, ge=0),
    crop_y: int = Form(default=0, ge=0),
    crop_width: int | None = Form(default=None, ge=1),
    crop_height: int | None = Form(default=None, ge=1),
    output_width: int | None = Form(default=None, ge=32, le=8192),
    output_height: int | None = Form(default=None, ge=32, le=8192),
    text: str = Form(default=""),
    text_color: str = Form(default="#17202a"),
    font_size: int = Form(default=48, ge=8, le=512),
    format: str = Form(default="png"),
    quality: int = Form(default=92, ge=1, le=100),
    max_kb: int | None = Form(default=None, ge=10, le=1024 * 20),
    _: AuthContext = Depends(require_menu("images")),
):
    settings = get_settings()
    max_bytes = settings.file_transfer_max_mb * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Image is too large")
    if not content:
        raise HTTPException(status_code=400, detail="Image is empty")
    try:
        with Image.open(BytesIO(content)) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGBA")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unsupported or broken image file") from exc

    left = min(crop_x, image.width - 1)
    top = min(crop_y, image.height - 1)
    right = min(image.width, left + (crop_width or image.width - left))
    bottom = min(image.height, top + (crop_height or image.height - top))
    if right <= left or bottom <= top:
        raise HTTPException(status_code=400, detail="Invalid crop area")
    image = image.crop((left, top, right, bottom))

    if output_width or output_height:
        width = output_width or round(image.width * (output_height / image.height))
        height = output_height or round(image.height * (output_width / image.width))
        image = image.resize((width, height), Image.Resampling.LANCZOS)

    _draw_center_text(image, text, _safe_color(text_color, "#17202a"), font_size)
    original_name = Path(file.filename or "image").stem[:80] or "image"
    filename = f"{original_name}-processed"
    return _serialize_image(image, format, quality, max_kb, filename)


# 执行任务：创建任务后进入 Redis 队列，worker 异步执行并回写结果。
@router.get("/runs", response_model=list[RunRead])
def list_runs(_: AuthContext = Depends(require_menu("runs")), db: Session = Depends(get_db)):
    return db.query(TestRun).order_by(TestRun.id.desc()).limit(100).all()


@router.post("/runs", response_model=RunRead)
def create_run(payload: RunCreate, current_user: AuthContext = Depends(get_current_user), db: Session = Depends(get_db)):
    required_menu = "api" if payload.case_type == "api" else "ui"
    if not current_user.is_admin and required_menu not in current_user.menu_permissions:
        raise HTTPException(status_code=403, detail="Menu permission required")
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
def get_run(run_id: int, _: AuthContext = Depends(require_menu("runs")), db: Session = Depends(get_db)):
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# 测试报告：从执行记录中汇总报告字段，供页面查看和导出。
@router.get("/reports")
def list_reports(_: AuthContext = Depends(require_menu("reports")), db: Session = Depends(get_db)):
    runs = db.query(TestRun).order_by(TestRun.id.desc()).limit(200).all()
    return [_report_summary(run, _case_name_for_run(db, run)) for run in runs]


@router.get("/reports/{run_id}")
def get_report(run_id: int, _: AuthContext = Depends(require_menu("reports")), db: Session = Depends(get_db)):
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_summary(run, _case_name_for_run(db, run))
