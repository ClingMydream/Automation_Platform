"""Read-only branch selection and Jenkins preview synchronization APIs."""

import os
import re
import subprocess
import tempfile
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_any_menu, require_menu
from app.core.config import get_settings


router = APIRouter(
    prefix="/v1/online-preview",
    tags=["在线预览"],
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


def _validate_branch(value: str) -> str:
    branch = value.strip().removeprefix("origin/")
    if not branch or not BRANCH_PATTERN.fullmatch(branch):
        raise HTTPException(400, "分支名称格式不合法")
    return branch


def _remote_revision(branch: str) -> dict:
    """Fetch only the selected branch metadata without checking out project files."""
    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="cling-revision-") as directory:
        askpass = Path(directory) / "askpass.sh"
        askpass.write_text(
            '#!/bin/sh\ncase "$1" in *Username*) printf \'%s\\n\' "$CODEUP_USERNAME" ;; *) printf \'%s\\n\' "$CODEUP_PASSWORD" ;; esac\n',
            encoding="utf-8",
        )
        askpass.chmod(0o700)
        env = os.environ.copy()
        env.update({
            "GIT_ASKPASS": str(askpass),
            "GIT_TERMINAL_PROMPT": "0",
            "CODEUP_USERNAME": settings.codeup_username,
            "CODEUP_PASSWORD": settings.codeup_password,
        })
        commands = [
            ["git", "init", "-q", directory],
            ["git", "-C", directory, "remote", "add", "origin", REPOSITORY_URL],
            ["git", "-C", directory, "fetch", "-q", "--depth=1", "--filter=blob:none", "origin", f"refs/heads/{branch}"],
            ["git", "-C", directory, "show", "-s", "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%s", "FETCH_HEAD"],
        ]
        try:
            for command in commands[:-1]:
                subprocess.run(command, env=env, check=True, capture_output=True, text=True, timeout=30)
            output = subprocess.run(commands[-1], env=env, check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        except (subprocess.SubprocessError, OSError) as exc:
            raise HTTPException(502, "读取分支最新提交信息失败") from exc
    sha, author, email, committed_at, subject = output.split("\x1f", 4)
    return {"branch": branch, "sha": sha, "author": author, "email": email, "committed_at": committed_at, "subject": subject}


def _jenkins_job_status(job_name: str) -> dict:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.jenkins_url}/job/{job_name}/lastBuild/api/json",
            params={"tree": "number,result,building,timestamp,duration,description,actions[parameters[name,value],lastBuiltRevision[SHA1]]"},
            auth=_jenkins_auth(),
            timeout=10,
        )
        if response.status_code == 404:
            return {"number": None, "result": "NOT_BUILT", "building": False, "branch": None, "commit_sha": None}
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "无法读取 Jenkins 任务状态") from exc
    branch = None
    action_sha = None
    for action in data.get("actions", []):
        if action.get("lastBuiltRevision"):
            action_sha = action["lastBuiltRevision"].get("SHA1")
        for parameter in action.get("parameters", []):
            if parameter.get("name") == "BRANCH":
                branch = parameter.get("value")
    description = data.get("description") or ""
    sha_match = re.search(r"SHA[：:]\s*([0-9a-f]{40})", description, re.I)
    stages: list[dict] = []
    # Pipeline Stage View's compact API makes Jenkins progress understandable
    # without granting users direct access to Jenkins or its console logs.
    if data.get("number"):
        try:
            stage_response = httpx.get(
                f"{settings.jenkins_url}/job/{job_name}/{data['number']}/wfapi/describe",
                auth=_jenkins_auth(), timeout=8,
            )
            if stage_response.is_success:
                for stage in stage_response.json().get("stages", []):
                    stages.append({
                        "name": stage.get("name") or "未命名阶段",
                        "status": stage.get("status") or "NOT_EXECUTED",
                        "start_time": stage.get("startTimeMillis"),
                        "duration": stage.get("durationMillis"),
                    })
        except httpx.HTTPError:
            # Stage View is optional in Jenkins. The regular build status remains usable.
            pass
    return {
        "number": data.get("number"), "result": data.get("result"), "building": data.get("building", False),
        "branch": branch, "commit_sha": sha_match.group(1) if sha_match else action_sha,
        "timestamp": data.get("timestamp"), "duration": data.get("duration"), "description": description,
        "stages": stages,
    }


def _deployed_revision() -> dict | None:
    """Read the immutable revision manifest published with the preview assets."""
    try:
        response = httpx.get("http://emote-preview/.cling-preview-revision.json", timeout=5)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        if not isinstance(data.get("sha"), str) or not isinstance(data.get("branch"), str):
            return None
        return data
    except (httpx.HTTPError, ValueError):
        return None


@router.get("/branches", dependencies=[Depends(require_any_menu("online_preview", "jenkins", "emote_ui_automation"))])
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


@router.get("/revision", dependencies=[Depends(require_any_menu("online_preview", "jenkins", "emote_ui_automation"))])
def branch_revision(branch: str):
    return _remote_revision(_validate_branch(branch))


@router.get("/status", dependencies=[Depends(require_any_menu("online_preview", "emote_ui_automation"))])
def preview_status():
    result = _jenkins_job_status("emote-preview")
    result["deployed_revision"] = _deployed_revision()
    return result


@router.get("/comparison", dependencies=[Depends(require_any_menu("online_preview", "emote_ui_automation"))])
def preview_comparison(branch: str):
    """Compare Codeup's selected branch HEAD with the revision actually served online."""
    remote = _remote_revision(_validate_branch(branch))
    deployed = _deployed_revision()
    same_branch = bool(deployed and deployed.get("branch") == remote["branch"])
    same_revision = bool(same_branch and deployed and deployed.get("sha") == remote["sha"])
    return {
        "branch": remote["branch"], "remote": remote, "deployed": deployed,
        "matches": same_revision,
        "message": "线上预览已与远程最新代码一致" if same_revision else (
            "线上预览属于其他分支" if deployed and not same_branch else "线上预览尚未同步到远程最新提交"
        ),
    }


@router.get("/apk-status", dependencies=[Depends(require_menu("jenkins"))])
def apk_build_status():
    return _jenkins_job_status("emote-apk")


@router.post("/sync", status_code=202, dependencies=[Depends(require_any_menu("online_preview", "emote_ui_automation"))])
def synchronize_preview(payload: PreviewSyncRequest):
    branch = _validate_branch(payload.branch)
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
    queue_match = re.search(r"/queue/item/(\d+)/", response.headers.get("Location", ""))
    return {"message": "已提交同步任务", "branch": branch, "queue_id": queue_match.group(1) if queue_match else None}
