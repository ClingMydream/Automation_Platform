"""Worker database adapter for reading cases and updating execution runs."""

import json
import os
from contextlib import closing
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import pymysql
import requests


@dataclass
class DbConfig:
    """Store database connection settings used by the worker."""
    host: str
    port: int
    user: str
    password: str
    database: str


def parse_mysql_url(url: str) -> DbConfig:
    """Parse the MySQL URL into a structured worker database config."""
    parsed = urlparse(url.replace("mysql+pymysql://", "mysql://"))
    return DbConfig(
        host=parsed.hostname or "mysql",
        port=parsed.port or 3306,
        user=parsed.username or "automation",
        password=parsed.password or "",
        database=(parsed.path or "/automation_platform").lstrip("/"),
    )


DB = parse_mysql_url(os.environ["DATABASE_URL"])
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost").rstrip("/")


def connect_db():
    """Open a new MySQL connection for worker reads and writes."""
    return pymysql.connect(
        host=DB.host,
        port=DB.port,
        user=DB.user,
        password=DB.password,
        database=DB.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def update_run(run_id: int, **fields: Any) -> None:
    """Update status, logs, report data, or errors for a test run."""
    keys = list(fields)
    # Build the SET clause from trusted internal field names supplied by worker code.
    assignments = ", ".join(f"{key}=%s" for key in keys)
    # Store report dictionaries as JSON text because the MySQL column is JSON.
    values = [json.dumps(value, ensure_ascii=False) if key == "report" else value for key, value in fields.items()]
    with closing(connect_db()) as conn, conn.cursor() as cur:
        cur.execute(f"UPDATE test_runs SET {assignments}, updated_at=NOW() WHERE id=%s", [*values, run_id])


def fetch_run_case(run_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a test run and its related API or UI case from the database."""
    with closing(connect_db()) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM test_runs WHERE id=%s", [run_id])
        run = cur.fetchone()
        # API and UI cases live in different tables, selected by the run type.
        table = "api_cases" if run["case_type"] == "api" else "ui_cases"
        cur.execute(f"SELECT * FROM {table} WHERE id=%s", [run["case_id"]])
        case = cur.fetchone()
        if run["case_type"] == "api" and case and case.get("environment_id"):
            cur.execute("SELECT id, name, base_url, variables FROM environments WHERE id=%s", [case["environment_id"]])
            environment = cur.fetchone()
            if environment:
                case["environment"] = environment
    return run, case


def _json_value(value: Any) -> str:
    """Serialize values for MySQL JSON columns."""
    return json.dumps(value or {}, ensure_ascii=False)


def _result_failure_category(status: str, report: dict[str, Any], error: str | None) -> str | None:
    """Classify common task failures for result-center filtering."""
    if status == "passed":
        return None
    if error or report.get("error"):
        return "runtime"
    return "assertion"


def persist_run_result(run_id: int, status: str, duration_ms: int | None, report: dict[str, Any], error: str | None) -> None:
    """Persist a completed batch run into the result center and refresh batch totals."""
    with closing(connect_db()) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM test_runs WHERE id=%s", [run_id])
        run = cur.fetchone()
        if not run or not run.get("batch_id"):
            return
        request_data = {**(report.get("request") or {}), "run_id": run_id}
        response_data = report.get("response") or {}
        assertions = report.get("checks") or []
        metrics = {
            "pytest_exit_code": report.get("pytest_exit_code"),
            "framework": report.get("framework"),
        }
        environment_id = request_data.get("environment_id")
        cur.execute(
            """
            INSERT INTO test_results
              (batch_id, task_id, case_type, case_id, result_type, status, duration_ms,
               request_data, response_data, assertions, metrics, logs, error,
               failure_category, environment_id, device_info, started_at, finished_at, created_at, updated_at)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW(), NOW())
            """,
            [
                run.get("batch_id"),
                run.get("task_id"),
                run.get("case_type"),
                run.get("case_id"),
                run.get("case_type") or "api",
                status,
                duration_ms,
                _json_value(request_data),
                _json_value(response_data),
                json.dumps(assertions, ensure_ascii=False),
                _json_value(metrics),
                "Run completed" if status == "passed" else "Run failed",
                error or report.get("error"),
                _result_failure_category(status, report, error),
                environment_id,
                _json_value({}),
            ],
        )
        _refresh_batch_statistics(cur, run["batch_id"], run.get("task_id"))


def _refresh_batch_statistics(cur, batch_id: int, task_id: int | None) -> None:
    """Recalculate one execution batch after a worker writes a result row."""
    cur.execute(
        """
        SELECT
          COUNT(*) AS done_count,
          SUM(CASE WHEN status='passed' THEN 1 ELSE 0 END) AS passed_count,
          SUM(CASE WHEN status IN ('failed','error') THEN 1 ELSE 0 END) AS failed_count,
          SUM(CASE WHEN status='skipped' THEN 1 ELSE 0 END) AS skipped_count,
          SUM(COALESCE(duration_ms, 0)) AS duration_ms
        FROM test_results
        WHERE batch_id=%s
        """,
        [batch_id],
    )
    stats = cur.fetchone() or {}
    done_count = int(stats.get("done_count") or 0)
    failed_count = int(stats.get("failed_count") or 0)
    cur.execute("SELECT total_count FROM execution_batches WHERE id=%s", [batch_id])
    batch = cur.fetchone() or {}
    total_count = int(batch.get("total_count") or done_count)
    final_status = "running"
    finished_sql = "NULL"
    if total_count and done_count >= total_count:
        final_status = "failed" if failed_count else "passed"
        finished_sql = "NOW()"
    cur.execute(
        f"""
        UPDATE execution_batches
        SET passed_count=%s, failed_count=%s, skipped_count=%s, duration_ms=%s,
            status=%s, finished_at={finished_sql}, updated_at=NOW()
        WHERE id=%s
        """,
        [
            int(stats.get("passed_count") or 0),
            failed_count,
            int(stats.get("skipped_count") or 0),
            int(stats.get("duration_ms") or 0),
            final_status,
            batch_id,
        ],
    )
    if task_id is not None:
        cur.execute("UPDATE test_tasks SET last_status=%s, updated_at=NOW() WHERE id=%s", [final_status, task_id])
    if final_status in {"passed", "failed"}:
        _notify_batch_finished(cur, batch_id, final_status)


def _json_from_db(value: Any, fallback: Any) -> Any:
    """Decode JSON values returned as strings by some MySQL drivers."""
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value


def _webhook_accepts_event(events: Any, event: str) -> bool:
    """Return whether a webhook subscribes to an event; empty means all events."""
    event_list = _json_from_db(events, [])
    return not event_list or event in event_list


def _webhook_message_text(event: str, payload: dict[str, Any]) -> str:
    """Build a concise text message for chat-style webhooks."""
    return (
        f"Automation Platform {event}: {payload.get('batch_no')}, "
        f"status={payload.get('status')}, failed={payload.get('failed_count')}, total={payload.get('total_count')}"
    )


def _format_webhook_payload(integration_type: str | None, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Adapt generic notification data to common DingTalk, WeCom, or Feishu webhook formats."""
    kind = (integration_type or "webhook").lower()
    text = _webhook_message_text(event, payload)
    if kind in {"dingtalk", "wechat"}:
        return {"msgtype": "text", "text": {"content": text}}
    if kind == "feishu":
        return {"msg_type": "text", "content": {"text": text}}
    return {"event": event, "integration_type": kind, "data": payload}


def _send_webhook(url: str, secret_name: str | None, integration_type: str | None, event: str, payload: dict[str, Any]) -> bool:
    """Send one webhook notification and swallow network failures."""
    headers = {"Content-Type": "application/json"}
    if secret_name and os.getenv(secret_name):
        headers["X-Automation-Secret"] = os.environ[secret_name]
    body = _format_webhook_payload(integration_type, event, payload)
    try:
        response = requests.post(url, json=body, headers=headers, timeout=5, allow_redirects=False)
        return response.status_code < 400
    except requests.RequestException:
        return False


def _notify_batch_finished(cur, batch_id: int, final_status: str) -> None:
    """Notify active webhooks after a worker-driven batch reaches a final state."""
    cur.execute("SELECT * FROM execution_batches WHERE id=%s", [batch_id])
    batch = cur.fetchone()
    if not batch:
        return
    payload = {
        "batch_id": batch.get("id"),
        "batch_no": batch.get("batch_no"),
        "task_id": batch.get("task_id"),
        "trigger_type": batch.get("trigger_type"),
        "environment_id": batch.get("environment_id"),
        "status": final_status,
        "total_count": batch.get("total_count"),
        "passed_count": batch.get("passed_count"),
        "failed_count": batch.get("failed_count"),
        "skipped_count": batch.get("skipped_count"),
        "duration_ms": batch.get("duration_ms"),
        "report_url": f"{PUBLIC_BASE_URL}/api/reports/batches/{batch_id}",
    }
    events = ["batch_finished"]
    if final_status == "failed" or int(batch.get("failed_count") or 0):
        events.extend(["task_failed", "quality_risk"])
    cur.execute("SELECT * FROM integration_webhooks WHERE is_active=1")
    for webhook in cur.fetchall() or []:
        for event in events:
            if _webhook_accepts_event(webhook.get("events"), event):
                _send_webhook(webhook["webhook_url"], webhook.get("secret_name"), webhook.get("integration_type"), event, payload)
