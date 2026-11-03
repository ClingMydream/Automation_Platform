"""Reusable UI test environments; execution history keeps independent snapshots."""
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.models.entities import TimestampMixin


class UiAutomationEnvironment(Base, TimestampMixin):
    __tablename__ = 'ui_automation_environments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False, default='')
    viewport: Mapped[str] = mapped_column(String(20), nullable=False, default='mobile')
    notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
