"""Small startup schema migrations for additive, backward-compatible columns."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _has_column(engine: Engine, table_name: str, column_name: str) -> bool:
    """Return whether a table already has the requested column."""
    inspector = inspect(engine)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def ensure_runtime_schema(engine: Engine) -> None:
    """Apply safe additive migrations that SQLAlchemy create_all cannot perform."""
    if not _has_column(engine, "api_cases", "environment_id"):
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE api_cases ADD COLUMN environment_id INTEGER NULL"))
    if not _has_column(engine, "test_runs", "batch_id"):
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE test_runs ADD COLUMN batch_id INTEGER NULL"))
    if not _has_column(engine, "test_runs", "task_id"):
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE test_runs ADD COLUMN task_id INTEGER NULL"))
