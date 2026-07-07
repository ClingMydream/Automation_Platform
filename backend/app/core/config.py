"""Environment-driven backend settings and cached configuration access."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Define environment-based backend configuration."""
    # Basic application identity and environment label.
    app_name: str = "Automation Platform"
    app_env: str = "development"
    # Secrets and default administrator credentials must be overridden by server .env in production.
    app_secret_key: str = "dev-secret-change-me"
    admin_username: str = "admin"
    admin_password: str = "admin123456"
    access_token_expire_minutes: int = 720
    # Service connection strings used by FastAPI routes and queue publishing.
    database_url: str = "mysql+pymysql://automation:automation@mysql:3306/automation_platform?charset=utf8mb4"
    redis_url: str = "redis://redis:6379/0"
    public_base_url: str = "http://localhost"
    external_trigger_token: str | None = None
    # Security and file-transfer settings used by testing and temporary sharing features.
    allow_private_targets: bool = False
    file_transfer_dir: str = "/tmp/automation-platform-transfers"
    file_transfer_max_mb: int = 1024
    file_transfer_default_hours: int = 24
    result_attachment_dir: str = "/tmp/automation-platform-attachments"
    result_attachment_max_mb: int = 200

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return cached backend settings."""
    # Cache settings so every request does not re-read environment files.
    return Settings()
