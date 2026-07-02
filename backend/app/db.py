"""Database engine, ORM base class, and request-scoped session dependency."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


settings = get_settings()
# pool_pre_ping avoids stale MySQL connections after containers sit idle.
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=280)
# FastAPI dependencies create one SessionLocal instance for each request that needs database access.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base SQLAlchemy class for all ORM models."""
    pass


def get_db():
    """Yield one SQLAlchemy session per FastAPI request."""
    # The generator form lets FastAPI close the session after the route finishes or raises.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
