"""Upload and serve disposable static web previews."""

import io
import os
import re
import secrets
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.auth import AuthContext, require_menu, verify_admin


router = APIRouter(tags=["临时效果"])
ROOT = Path(os.getenv("TEMP_EFFECTS_DIR", "/var/lib/cling-temp-effects"))
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_UNPACKED_BYTES = 150 * 1024 * 1024
MAX_FILES = 1000
IDENTIFIER = re.compile(r"^[a-f0-9]{16}$")
BUILTIN_DISABLED = ".builtin-disabled"


@router.get("/effects/builtin")
def builtin_effect():
    return {"enabled": not (ROOT / BUILTIN_DISABLED).exists()}


@router.delete("/effects/builtin")
def delete_builtin_effect(_: AuthContext = Depends(verify_admin)):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / BUILTIN_DISABLED).touch()
    return {"status": "ok"}


def _items():
    if not ROOT.exists():
        return []
    return [
        {"id": entry.name, "name": (entry / ".title").read_text(encoding="utf-8"),
         "url": f"/api/effects/public/{entry.name}/index.html"}
        for entry in sorted(ROOT.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True)
        if entry.is_dir() and IDENTIFIER.fullmatch(entry.name) and (entry / ".title").is_file()
    ]


@router.get("/effects/workspace")
def list_effects(_: AuthContext = Depends(require_menu("effects"))):
    return _items()


@router.post("/effects/workspace")
async def upload_effect(file: UploadFile = File(...), _: AuthContext = Depends(verify_admin)):
    archive = await file.read(MAX_ARCHIVE_BYTES + 1)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise HTTPException(413, "压缩包超过 50 MB")
    try:
        source = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "请上传有效的 ZIP 压缩包") from exc
    with source:
        members = [member for member in source.infolist() if not member.is_dir()]
        if len(members) > MAX_FILES or sum(member.file_size for member in members) > MAX_UNPACKED_BYTES:
            raise HTTPException(413, "解压后的文件数量或体积超限")
        paths = [PurePosixPath(member.filename) for member in members]
        if any(path.is_absolute() or ".." in path.parts or "\\" in str(path) for path in paths):
            raise HTTPException(400, "压缩包包含非法路径")
        prefix = "" if any(str(path) == "index.html" for path in paths) else "dist/"
        if not any(str(path) == f"{prefix}index.html" for path in paths):
            raise HTTPException(400, "压缩包需要包含 index.html 或 dist/index.html")
        ROOT.mkdir(parents=True, exist_ok=True)
        identifier = secrets.token_hex(8)
        target = ROOT / identifier
        with tempfile.TemporaryDirectory(dir=ROOT) as staging:
            stage = Path(staging)
            for member, path in zip(members, paths):
                name = str(path)
                if prefix and not name.startswith(prefix):
                    continue
                relative = name[len(prefix):]
                if not relative or relative == ".title":
                    continue
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise HTTPException(400, "不支持符号链接")
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source.open(member) as incoming, destination.open("wb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
            title = Path(file.filename or "临时效果").stem[:80]
            (stage / ".title").write_text(title, encoding="utf-8")
            shutil.move(stage, target)
    return {"id": identifier, "name": title, "url": f"/api/effects/public/{identifier}/index.html"}


@router.delete("/effects/workspace/{identifier}")
def delete_effect(identifier: str, _: AuthContext = Depends(verify_admin)):
    if not IDENTIFIER.fullmatch(identifier) or not (ROOT / identifier / ".title").is_file():
        raise HTTPException(404, "临时效果不存在")
    shutil.rmtree(ROOT / identifier)
    return {"status": "ok"}


@router.delete("/effects/workspace")
def clear_effects(_: AuthContext = Depends(verify_admin)):
    for item in _items():
        shutil.rmtree(ROOT / item["id"])
    return {"status": "ok"}


@router.get("/effects/public/{identifier}/{asset_path:path}")
def preview_effect(identifier: str, asset_path: str):
    if not IDENTIFIER.fullmatch(identifier):
        raise HTTPException(404, "临时效果不存在")
    base = (ROOT / identifier).resolve()
    if not (base / ".title").is_file():
        raise HTTPException(404, "临时效果不存在")
    target = (base / (asset_path or "index.html")).resolve()
    if not target.is_relative_to(base) or target.name == ".title" or not target.is_file():
        raise HTTPException(404, "文件不存在")
    return FileResponse(target, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})
