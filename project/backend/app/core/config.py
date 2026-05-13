"""Application configuration using pydantic-settings.

All settings are loaded from environment variables with sensible defaults.
The Settings class is exposed as a singleton via `get_settings()`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database connection settings."""

    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    url: str = Field(
        default="postgresql+asyncpg://pptmaster:pptmaster@localhost:5432/pptmaster",
        description="Full async database URL including driver",
    )
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=1800, description="Recycle connections after N seconds")
    echo: bool = Field(default=False, description="Echo SQL statements (debug)")


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )


class MinIOSettings(BaseSettings):
    """MinIO / S3-compatible object storage settings."""

    model_config = SettingsConfigDict(env_prefix="MINIO_", extra="ignore")

    endpoint: str = Field(default="localhost:9000", description="MinIO server endpoint")
    access_key: str = Field(default="minioadmin", description="Access key")
    secret_key: str = Field(default="minioadmin", description="Secret key")
    bucket: str = Field(default="pptmaster", description="Default bucket name")
    secure: bool = Field(default=False, description="Use HTTPS")
    region: Optional[str] = Field(default=None, description="S3 region (optional)")


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    provider: str = Field(default="openai", description="Default LLM provider")
    model: str = Field(default="gpt-4o", description="Default LLM model")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_base_url: Optional[str] = Field(default=None, alias="ANTHROPIC_BASE_URL")
    temperature: float = Field(default=0.7, description="Default sampling temperature")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens per request")
    timeout: int = Field(default=120, description="Request timeout in seconds")


class StorageSettings(BaseSettings):
    """Storage backend selection and configuration."""

    model_config = SettingsConfigDict(env_prefix="STORAGE_", extra="ignore")

    backend: str = Field(
        default="minio",
        description="Storage backend: 'minio' or 'local'",
    )
    local_base_path: str = Field(
        default="./data/storage",
        description="Base path for local file storage (dev mode)",
    )
    public_url_base: Optional[str] = Field(
        default=None,
        description="Public URL base for serving local files (e.g. http://localhost:8000/static)",
    )


class SecuritySettings(BaseSettings):
    """API security settings."""

    model_config = SettingsConfigDict(env_prefix="SECURITY_", extra="ignore")

    api_key: Optional[str] = Field(
        default=None,
        description="Static API key for service-to-service authentication",
    )
    secret_key: str = Field(
        default="change-me-in-production-secret-key-2024",
        description="Secret key for signing tokens / encryption",
    )


class AppSettings(BaseSettings):
    """Global application settings composed of sub-settings groups."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="PPT Master Web Service")
    debug: bool = Field(default=False)
    log_level: str = Field(default="info")
    version: str = Field(default="0.1.0")

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # PPT Master skill directory
    ppt_master_skill_dir: str = Field(
        default="/app/ppt-master/skills/ppt-master",
        alias="PPT_MASTER_SKILL_DIR",
    )

    # Sub-settings
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)


@lru_cache
def get_settings() -> AppSettings:
    """Return a cached singleton of AppSettings."""
    return AppSettings()


settings = get_settings()
