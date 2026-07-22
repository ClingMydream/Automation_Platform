from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    years_experience: int = 6
    current_role: str
    target_role: str
    target_city: str
    current_salary: str
    target_salary: str
    target_date: date
    daily_target_minutes: int = Field(ge=0, le=1440)
    current_focus: str
    strengths: list[str] = []
    gaps: list[str] = []


class TaskInput(BaseModel):
    plan_id: int | None = None
    day_number: int = Field(ge=1)
    phase: str
    category: str
    title: str
    details: str = ""
    acceptance_criteria: str = ""
    expected_minutes: int = Field(default=60, ge=0, le=1440)
    original_planned_date: date | None = None
    planned_date: date
    sort_order: int = 0
    status: str = "pending"


class CheckinInput(BaseModel):
    actual_minutes: int = Field(default=0, ge=0, le=1440)
    gains: str = ""
    blockers: str = ""
    tomorrow_focus: str = ""


class FolderInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    parent_id: int | None = None
    sort_order: int = 0


class NoteInput(BaseModel):
    folder_id: int | None = None
    linked_task_id: int | None = None
    title: str = Field(default="未命名笔记", min_length=1, max_length=240)
    content_markdown: str = ""
    tags: list[str] = []
    is_pinned: bool = False
    restore: bool = False
