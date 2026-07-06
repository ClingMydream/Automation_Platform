"""Business helpers for validating and saving test objects."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Project, TestObject
from app.modules.test_objects.schemas import TestObjectCreate


def ensure_project_exists(db: Session, project_id: int | None) -> None:
    """Validate the optional project relation without forcing every object into a project."""
    if project_id is not None and db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


def ensure_unique_code(db: Session, code: str, exclude_id: int | None = None) -> None:
    """Prevent duplicate test object codes while allowing the current row during updates."""
    query = db.query(TestObject).filter(TestObject.code == code)
    if exclude_id is not None:
        query = query.filter(TestObject.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=400, detail="Test object code already exists")


def payload_data(payload: TestObjectCreate) -> dict:
    """Convert a validated request schema into ORM-ready data."""
    data = payload.model_dump()
    data["code"] = data["code"].strip()
    data["name"] = data["name"].strip()
    data["business_module"] = data["business_module"] or None
    data["description"] = data["description"] or None
    return data
