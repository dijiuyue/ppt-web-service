"""
PPT Master Web Service — Configuration Tests.

Tests for AppSettings and sub-settings loading, defaults, and env overrides.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.core.config import (
    AppSettings,
    DatabaseSettings,
    LLMSettings,
    MinIOSettings,
    RedisSettings,
    SecuritySettings,
    StorageSettings,
    get_settings,
)


# ---------------------------------------------------------------------------
# DatabaseSettings
# ---------------------------------------------------------------------------


class TestDatabaseSettings:
    """Tests for DatabaseSettings."""

    def test_database_settings_defaults(self) -> None:
        """Test DatabaseSettings uses correct defaults."""
        # Clear env vars that may be set by test suite
        with patch.dict(os.environ, {"DB_URL": ""}, clear=False):
            os.environ.pop("DB_URL", None)
            db = DatabaseSettings()
        assert "pptmaster" in db.url
        assert db.pool_size == 10
        assert db.max_overflow == 20
        assert db.pool_timeout == 30
        assert db.pool_recycle == 1800
        assert db.echo is False

    def test_database_settings_env_override(self) -> None:
        """Test DatabaseSettings reads environment variables."""
        with patch.dict(
            os.environ,
            {
                "DB_URL": "postgresql+asyncpg://custom:pass@dbhost:9999/mydb",
                "DB_POOL_SIZE": "25",
                "DB_ECHO": "true",
            },
            clear=False,
        ):
            db = DatabaseSettings()
            assert db.url == "postgresql+asyncpg://custom:pass@dbhost:9999/mydb"
            assert db.pool_size == 25
            assert db.echo is True


# ---------------------------------------------------------------------------
# RedisSettings
# ---------------------------------------------------------------------------


class TestRedisSettings:
    """Tests for RedisSettings."""

    def test_redis_settings_defaults(self) -> None:
        """Test RedisSettings uses correct defaults."""
        redis = RedisSettings()
        assert redis.url == "redis://localhost:6379/0"

    def test_redis_settings_env_override(self) -> None:
        """Test RedisSettings reads environment variables."""
        with patch.dict(
            os.environ,
            {"REDIS_URL": "redis://redis.example.com:6380/1"},
            clear=False,
        ):
            redis = RedisSettings()
            assert redis.url == "redis://redis.example.com:6380/1"


# ---------------------------------------------------------------------------
# MinIOSettings
# ---------------------------------------------------------------------------


class TestMinIOSettings:
    """Tests for MinIOSettings."""

    def test_minio_settings_defaults(self) -> None:
        """Test MinIOSettings uses correct defaults."""
        minio = MinIOSettings()
        assert minio.endpoint == "localhost:9000"
        assert minio.access_key == "minioadmin"
        assert minio.secret_key == "minioadmin"
        assert minio.bucket == "pptmaster"
        assert minio.secure is False

    def test_minio_settings_env_override(self) -> None:
        """Test MinIOSettings reads environment variables."""
        with patch.dict(
            os.environ,
            {
                "MINIO_ENDPOINT": "s3.example.com",
                "MINIO_ACCESS_KEY": "testkey",
                "MINIO_SECURE": "true",
                "MINIO_REGION": "us-east-1",
            },
            clear=False,
        ):
            minio = MinIOSettings()
            assert minio.endpoint == "s3.example.com"
            assert minio.access_key == "testkey"
            assert minio.secure is True
            assert minio.region == "us-east-1"


# ---------------------------------------------------------------------------
# LLMSettings
# ---------------------------------------------------------------------------


class TestLLMSettings:
    """Tests for LLMSettings."""

    def test_llm_settings_defaults(self) -> None:
        """Test LLMSettings uses correct defaults."""
        llm = LLMSettings()
        assert llm.provider == "openai"
        assert llm.model == "gpt-4o"
        assert llm.temperature == 0.7
        assert llm.timeout == 120
        assert llm.max_tokens is None

    def test_llm_settings_env_override(self) -> None:
        """Test LLMSettings reads environment variables."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "LLM_MODEL": "claude-3-5-sonnet-latest",
                "LLM_TEMPERATURE": "0.5",
                "LLM_TIMEOUT": "60",
                "OPENAI_API_KEY": "sk-test-key",
            },
            clear=False,
        ):
            llm = LLMSettings()
            assert llm.provider == "anthropic"
            assert llm.model == "claude-3-5-sonnet-latest"
            assert llm.temperature == 0.5
            assert llm.timeout == 60
            assert llm.openai_api_key == "sk-test-key"


# ---------------------------------------------------------------------------
# StorageSettings
# ---------------------------------------------------------------------------


class TestStorageSettings:
    """Tests for StorageSettings."""

    def test_storage_settings_defaults(self) -> None:
        """Test StorageSettings uses correct defaults."""
        with patch.dict(os.environ, {"STORAGE_BACKEND": ""}, clear=False):
            os.environ.pop("STORAGE_BACKEND", None)
            storage = StorageSettings()
        assert storage.backend == "minio"
        assert storage.local_base_path == "./data/storage"
        assert storage.public_url_base is None

    def test_storage_settings_env_override(self) -> None:
        """Test StorageSettings reads environment variables."""
        with patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "local",
                "STORAGE_LOCAL_BASE_PATH": "/tmp/test-storage",
                "STORAGE_PUBLIC_URL_BASE": "http://localhost:8000/static",
            },
            clear=False,
        ):
            storage = StorageSettings()
            assert storage.backend == "local"
            assert storage.local_base_path == "/tmp/test-storage"
            assert storage.public_url_base == "http://localhost:8000/static"


# ---------------------------------------------------------------------------
# SecuritySettings
# ---------------------------------------------------------------------------


class TestSecuritySettings:
    """Tests for SecuritySettings."""

    def test_security_settings_defaults(self) -> None:
        """Test SecuritySettings uses correct defaults."""
        security = SecuritySettings()
        assert security.api_key is None
        assert "change-me" in security.secret_key

    def test_security_settings_env_override(self) -> None:
        """Test SecuritySettings reads environment variables."""
        with patch.dict(
            os.environ,
            {
                "SECURITY_API_KEY": "test-api-key-123",
                "SECURITY_SECRET_KEY": "super-secret-key",
            },
            clear=False,
        ):
            security = SecuritySettings()
            assert security.api_key == "test-api-key-123"
            assert security.secret_key == "super-secret-key"


# ---------------------------------------------------------------------------
# AppSettings (Integration)
# ---------------------------------------------------------------------------


class TestAppSettings:
    """Tests for AppSettings (global configuration)."""

    def test_app_settings_defaults(self) -> None:
        """Test AppSettings uses correct defaults."""
        # Override .env values via os.environ (takes precedence over env_file)
        with patch.dict(os.environ, {"DEBUG": "false", "DB_URL": ""}, clear=False):
            os.environ.pop("DB_URL", None)
            settings = AppSettings()
        assert settings.app_name == "PPT Master Web Service"
        assert settings.debug is False
        assert settings.log_level == "info"
        assert settings.version == "0.1.0"
        assert isinstance(settings.cors_origins, list)
        assert "http://localhost:5173" in settings.cors_origins

    def test_app_settings_sub_settings(self) -> None:
        """Test AppSettings contains all sub-settings."""
        settings = AppSettings()
        assert isinstance(settings.db, DatabaseSettings)
        assert isinstance(settings.redis, RedisSettings)
        assert isinstance(settings.minio, MinIOSettings)
        assert isinstance(settings.llm, LLMSettings)
        assert isinstance(settings.storage, StorageSettings)
        assert isinstance(settings.security, SecuritySettings)

    def test_app_settings_env_override(self) -> None:
        """Test AppSettings reads top-level env vars."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Custom App",
                "DEBUG": "true",
                "LOG_LEVEL": "debug",
            },
            clear=False,
        ):
            settings = AppSettings()
            assert settings.app_name == "Custom App"
            assert settings.debug is True
            assert settings.log_level == "debug"

    def test_get_settings_cached(self) -> None:
        """Test get_settings returns a cached singleton."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
