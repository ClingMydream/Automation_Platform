"""Optional Jira Cloud adapter for deduplicated UI-automation failures."""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db import engine
from app.models.entities import ExternalIssueLink, UiAutomationArtifact, UiAutomationRun


SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(authorization|cookie|token|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b\d{11}\b"),
    re.compile(r"\b[A-Fa-f0-9]{24,}\b"),
)


def redact_text(value: object) -> str:
    text = str(value or "")
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text[:1600]


def normalise_failure(run: UiAutomationRun) -> tuple[str, str, str]:
    failure = (run.result_summary or {}).get("failure") or {}
    kind = str(failure.get("reason") or run.error_message or "自动化执行失败")
    detail = redact_text(failure.get("technical_detail") or failure.get("suggestion") or run.error_message)
    # Dynamic IDs, timestamps, phone-like values and long tokens must not create new bugs.
    stable = re.sub(r"\b\d{4,}\b", "#", f"{kind}\n{detail}")
    stable = re.sub(r"\s+", " ", stable).strip()
    return kind[:240], detail, stable[:1000]


def failure_fingerprint(run: UiAutomationRun) -> str:
    kind, _, stable = normalise_failure(run)
    material = "|".join(["ui-automation", ",".join(map(str, sorted(run.case_ids or []))), run.branch or "", kind, stable])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def jira_ready(settings: Settings) -> bool:
    return bool(settings.jira_enabled and settings.jira_base_url and settings.jira_user_email and settings.jira_api_token and settings.jira_project_key)


class JiraCloudAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = (settings.jira_base_url or "").rstrip("/")
        self.auth = (settings.jira_user_email or "", settings.jira_api_token or "")

    def _request(self, method: str, path: str, **kwargs):
        with httpx.Client(base_url=self.base_url, auth=self.auth, timeout=httpx.Timeout(10, connect=3), follow_redirects=False) as client:
            response = client.request(method, path, headers={"Accept": "application/json"}, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}

    def test_connection(self) -> dict:
        identity = self._request("GET", "/rest/api/3/myself")
        project = self._request("GET", f"/rest/api/3/project/{self.settings.jira_project_key}")
        return {"account": identity.get("displayName", "connected"), "project": project.get("key"), "issue_type": self.settings.jira_issue_type}

    def find_open_issue_by_fingerprint(self, fingerprint: str):
        escaped = fingerprint.replace('"', "\\\"")
        data = self._request("GET", "/rest/api/3/search/jql", params={"jql": f'project = "{self.settings.jira_project_key}" AND text ~ "{escaped}"', "maxResults": 1, "fields": "key,status"})
        issues = data.get("issues") or []
        return issues[0] if issues else None

    def create_issue(self, fields: dict) -> dict:
        return self._request("POST", "/rest/api/3/issue", json={"fields": fields})

    def append_execution_record(self, issue_key: str, text: str) -> None:
        self._request("POST", f"/rest/api/3/issue/{issue_key}/comment", json={"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": text[:3000]}]}]}})

    def get_issue_url(self, issue_key: str) -> str:
        return f"{self.base_url}/browse/{issue_key}"


def _report_url(run: UiAutomationRun, settings: Settings) -> str:
    return f"{settings.public_base_url.rstrip('/')}/emote-ui-automation/run/{run.id}"


def _description(run: UiAutomationRun, fingerprint: str, settings: Settings, db: Session) -> str:
    kind, detail, _ = normalise_failure(run)
    artifacts = db.scalars(select(UiAutomationArtifact).where(UiAutomationArtifact.run_id == run.id)).all()
    evidence = ", ".join(sorted({item.kind for item in artifacts})) or "无附件"
    return "\n".join([
        f"测试批次：#{run.id}", f"分支：{run.branch}", f"用例：{', '.join(map(str, run.case_ids or [])) or '未标记'}",
        f"失败类型：{kind}", f"错误摘要：{detail or '无'}", f"失败指纹：{fingerprint}",
        f"平台报告（需登录）：{_report_url(run, settings)}", f"平台证据类型：{evidence}",
    ])


def sync_failed_run(run_id: int) -> None:
    """Best-effort sidecar sync. Never re-raise into the execution result callback."""
    settings = get_settings()
    if not (jira_ready(settings) and settings.jira_auto_create_on_failure):
        return
    with Session(engine) as db:
        run = db.get(UiAutomationRun, run_id)
        if not run or run.status != "failed":
            return
        fingerprint = failure_fingerprint(run)
        link = db.scalar(select(ExternalIssueLink).where(ExternalIssueLink.provider == "jira", ExternalIssueLink.failure_fingerprint == fingerprint))
        if link and link.sync_status == "synced" and link.issue_key:
            try:
                JiraCloudAdapter(settings).append_execution_record(link.issue_key, f"再次发生：执行批次 #{run.id}，报告：{_report_url(run, settings)}")
                link.last_synced_at = datetime.utcnow()
                db.commit()
            except Exception as exc:
                link.sync_status, link.retry_count, link.last_error_summary = "retryable", link.retry_count + 1, redact_text(exc)
                db.commit()
            return
        link = link or ExternalIssueLink(provider="jira", project_key=settings.jira_project_key or "", run_id=run.id, failure_fingerprint=fingerprint)
        db.add(link)
        adapter = JiraCloudAdapter(settings)
        for attempt in range(3):
            try:
                existing = adapter.find_open_issue_by_fingerprint(fingerprint)
                if existing:
                    issue_key = existing["key"]
                    adapter.append_execution_record(issue_key, f"关联执行批次 #{run.id}，报告：{_report_url(run, settings)}")
                else:
                    created = adapter.create_issue({"project": {"key": settings.jira_project_key}, "issuetype": {"name": settings.jira_issue_type}, "summary": f"[自动化失败] {normalise_failure(run)[0]}"[:255], "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": _description(run, fingerprint, settings, db)}]}]}})
                    issue_key = created["key"]
                link.issue_key, link.issue_url, link.sync_status = issue_key, adapter.get_issue_url(issue_key), "synced"
                link.first_synced_at = link.first_synced_at or datetime.utcnow(); link.last_synced_at = datetime.utcnow(); link.last_error_summary = ""
                db.commit(); return
            except Exception as exc:
                link.retry_count, link.last_error_summary = attempt + 1, redact_text(exc)
                link.sync_status = "retryable" if attempt < 2 else "manual_action_required"
                db.commit()
                if attempt < 2: time.sleep(2 ** attempt)
