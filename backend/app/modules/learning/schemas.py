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
    learning_day: int | None = Field(default=None, ge=1)
    actual_minutes: int = Field(default=0, ge=0, le=1440)
    gains: str = ""
    blockers: str = ""
    tomorrow_focus: str = ""


class RestartLearningInput(BaseModel):
    start_date: date | None = None
    title: str = "第二期 · 零基础文档训练营"
    confirm: bool = False


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


class MasteryProgressInput(BaseModel):
    current_step: int = Field(default=0, ge=0, le=8)
    prediction: str = Field(default="", max_length=10000)
    run_confirmed: bool = False
    run_output: str = Field(default="", max_length=20000)
    modified_code: str = Field(default="", max_length=30000)
    exercise_answer: str = Field(default="", max_length=20000)
    quiz_answers: list[int] = []
    explanation: str = Field(default="", max_length=10000)
    complete: bool = False


class MasteryBlockerInput(BaseModel):
    content: str = Field(min_length=2, max_length=1000)


class MasteryTimerInput(BaseModel):
    action: str


class MasteryResetInput(BaseModel):
    confirm_text: str
