"""
PPT Master Web Service — Test Suite.

⚠️  Environment variables MUST be set before any app module import.
    This file is imported by pytest *before* conftest.py and test files.
"""

import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
os.environ["STORAGE_BACKEND"] = os.environ.get("STORAGE_BACKEND", "local")
os.environ["LOCAL_STORAGE_ROOT"] = os.environ.get("LOCAL_STORAGE_ROOT", "./test_storage")
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-test-key")
os.environ["SECRET_KEY"] = os.environ.get("SECRET_KEY", "test-secret-key")
