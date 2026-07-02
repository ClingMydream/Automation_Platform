import json
import os
from contextlib import closing
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import pymysql


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
    assignments = ", ".join(f"{key}=%s" for key in keys)
    values = [json.dumps(value, ensure_ascii=False) if key == "report" else value for key, value in fields.items()]
    with closing(connect_db()) as conn, conn.cursor() as cur:
        cur.execute(f"UPDATE test_runs SET {assignments}, updated_at=NOW() WHERE id=%s", [*values, run_id])


def fetch_run_case(run_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a test run and its related API or UI case from the database."""
    with closing(connect_db()) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM test_runs WHERE id=%s", [run_id])
        run = cur.fetchone()
        table = "api_cases" if run["case_type"] == "api" else "ui_cases"
        cur.execute(f"SELECT * FROM {table} WHERE id=%s", [run["case_id"]])
        case = cur.fetchone()
    return run, case
