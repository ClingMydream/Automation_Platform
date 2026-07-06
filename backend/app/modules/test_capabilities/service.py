"""Business helpers for test capability records."""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.target_guard import validate_public_http_url
from app.models.entities import ApiScenario, Environment, PerformanceScenario, Project, RunnerAgent


def ensure_project(db: Session, project_id: int | None) -> None:
    """Validate optional project relation."""
    if project_id is not None and db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


def ensure_environment(db: Session, environment_id: int | None) -> None:
    """Validate optional environment relation."""
    if environment_id is not None and db.get(Environment, environment_id) is None:
        raise HTTPException(status_code=404, detail="Environment not found")


def ensure_unique_code(db: Session, model, code: str, exclude_id: int | None = None, message: str = "Code already exists") -> None:
    """Validate unique code for scenario-like records."""
    query = db.query(model).filter(model.code == code)
    if exclude_id is not None:
        query = query.filter(model.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=400, detail=message)


def validate_performance_target(url: str) -> None:
    """Reuse target guard so performance scenarios cannot point at private infrastructure."""
    validate_public_http_url(url)


def validate_runner_url(url: str | None) -> None:
    """Validate optional runner callback URL."""
    if url:
        validate_public_http_url(url)


def mark_runner_seen(runner: RunnerAgent) -> None:
    """Update runner heartbeat fields in one place."""
    runner.status = "online"
    runner.last_seen_at = datetime.utcnow()
