"""Additive marker: install built-in cases once, preserve later user edits/deletes."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.db import Base

class UiAutomationCatalogInstall(Base):
    __tablename__ = 'ui_automation_catalog_installs'
    version = Column(String(80), primary_key=True)
    installed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
