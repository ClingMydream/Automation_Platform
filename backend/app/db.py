from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=280)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base SQLAlchemy class for all ORM models."""
    pass


def get_db():
    """Yield one SQLAlchemy session per FastAPI request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
