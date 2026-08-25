"""Read-only branch selection and Jenkins preview synchronization APIs."""

import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_menu
from app.core.config import get_settings


router = APIRouter(
    prefix="/v1/online-preview",
    tags=["在线预览"],
    dependencies=[Depends(require_menu("online_preview"))],
)

REPOSITORY_URL = "https://codeup.aliyun.com/6523ca864bb5eb36db2f603e/emote-app2.git"
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")


class PreviewSyncRequest(BaseModel):
    branch: str


def _jenkins_auth() -> tuple[str, str]:
    settings = get_settings()
    if not settings.jenkins_admin_password:
        raise HTTPException(503, "Jenkins 管理凭据未配置")
    return settings.jenkins_admin_user, settings.jenkins_admin_password


def _parse_git_refs(content: bytes) -> list[str]:
    """Parse Git smart-HTTP pkt-lines and return remote branch names."""
    branches: list[str] = []
    offset = 0
    while offset + 4 <= len(content):
        try:
            length = int(content[offset:offset + 4], 16)
        except ValueError:
            break
        offset += 4
        if length == 0:
            continue
        payload_length = length - 4
        if payload_length < 0 or offset + payload_length > len(content):
            break
        payload = content[offset:offset + payload_length]
        offset += payload_length
        line = payload.split(b"\0", 1)[0].decode("utf-8", errors="ignore")
        if " refs/heads/" in line:
            branches.append(line.split(" refs/heads/", 1)[1].strip())
    return sorted(set(branches), reverse=True)


@router.get("/branches")
def list_preview_branches():
    settings = get_settings()
    try:
        response = httpx.get(
            REPOSITORY_URL + "/info/refs",
            params={"service": "git-upload-pack"},
            auth=(settings.codeup_username, settings.codeup_password),
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "读取远程分支失败，请检查 Codeup 只读凭据") from exc
    branches = _parse_git_refs(response.content)
    if not branches:
        raise HTTPException(502, "远程仓库没有返回可用分支")
    return branches


@router.get("/status")
def preview_status():
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.jenkins_url}/job/emote-preview/lastBuild/api/json",
            params={"tree": "number,result,building,timestamp,duration,description,actions[parameters[name,value]]"},
            auth=_jenkins_auth(),
            timeout=10,
        )
        if response.status_code == 404:
            return {"number": None, "result": "NOT_BUILT", "building": False, "branch": None}
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "无法读取 Jenkins 预览任务状态") from exc
    branch = None
    for action in data.get("actions", []):
        for parameter in action.get("parameters", []):
            if parameter.get("name") == "BRANCH":
                branch = parameter.get("value")
    return {
        "number": data.get("number"),
        "result": data.get("result"),
        "building": data.get("building", False),
        "branch": branch,
        "timestamp": data.get("timestamp"),
        "duration": data.get("duration"),
        "description": data.get("description"),
    }


@router.post("/sync", status_code=202)
def synchronize_preview(payload: PreviewSyncRequest):
    branch = payload.branch.strip().removeprefix("origin/")
    if not branch or not BRANCH_PATTERN.fullmatch(branch):
        raise HTTPException(400, "分支名称格式不合法")
    settings = get_settings()
    auth = _jenkins_auth()
    try:
        with httpx.Client(auth=auth, timeout=15) as client:
            crumb_response = client.get(f"{settings.jenkins_url}/crumbIssuer/api/json")
            crumb_response.raise_for_status()
            crumb_data = crumb_response.json()
            response = client.post(
                f"{settings.jenkins_url}/job/emote-preview/buildWithParameters",
                data={"BRANCH": branch},
                headers={crumb_data["crumbRequestField"]: crumb_data["crumb"]},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "触发 Jenkins 预览同步失败") from exc
    return {"message": "已提交同步任务", "branch": branch}
