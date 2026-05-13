"""
PPT Master Web Service — Shared Pytest Fixtures.

Provides common fixtures for async testing, FastAPI app, HTTP client,
database session, and sample data objects.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# We need to set up the path for imports
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.schemas import (
    CanvasFormat,
    ConversionStatus,
    FileType,
    LLMProvider,
    PipelineStep,
    ProjectCreate,
    ProjectStatus,
    SourceUrlAdd,
    StepStatus,
)
from app.models.project import Project
from app.models.source_file import SourceFile
from app.services.storage_service import LocalStorage, StorageManager


# ---------------------------------------------------------------------------
# Event Loop
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a session-scoped event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_storage_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for local storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def storage(temp_storage_dir: str) -> LocalStorage:
    """Provide a LocalStorage instance using a temp directory."""
    # Reset singleton to ensure fresh instance
    StorageManager.reset()
    return LocalStorage(base_dir=temp_storage_dir)


# ---------------------------------------------------------------------------
# Mock Database Session
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Provide a mocked async SQLAlchemy session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock(return_value=0)
    return session


# ---------------------------------------------------------------------------
# Sample Data Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_project_id() -> UUID:
    """Return a fixed UUID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_project(sample_project_id: UUID) -> Project:
    """Return a sample Project ORM instance (not persisted)."""
    return Project(
        id=sample_project_id,
        name="Test Project",
        description="A test project for unit tests",
        canvas_format=CanvasFormat.PPT169.value,
        status=ProjectStatus.DRAFT.value,
        current_step=PipelineStep.INIT.value,
        step_status=StepStatus.PENDING.value,
        llm_provider=LLMProvider.OPENAI.value,
        llm_model="gpt-4o",
        template_path=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        completed_at=None,
    )


@pytest.fixture
def sample_project_create() -> ProjectCreate:
    """Return a sample ProjectCreate schema."""
    return ProjectCreate(
        name="Test Project",
        description="A test project",
        canvas_format=CanvasFormat.PPT169,
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-4o",
    )


@pytest.fixture
def sample_source_file_id() -> UUID:
    """Return a fixed UUID for source file testing."""
    return UUID("87654321-4321-8765-4321-876543218765")


@pytest.fixture
def sample_source_file(
    sample_source_file_id: UUID, sample_project_id: UUID
) -> SourceFile:
    """Return a sample SourceFile ORM instance (not persisted)."""
    return SourceFile(
        id=sample_source_file_id,
        project_id=sample_project_id,
        original_filename="test_document.pdf",
        file_type=FileType.PDF.value,
        storage_key=f"projects/{sample_project_id}/sources/{sample_source_file_id}/test_document.pdf",
        storage_backend="local",
        file_size=1024,
        markdown_content=None,
        markdown_storage_key=None,
        conversion_status=ConversionStatus.PENDING.value,
        conversion_error=None,
        sort_order=0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_url_source_add() -> SourceUrlAdd:
    """Return a sample SourceUrlAdd schema."""
    return SourceUrlAdd(
        url="https://example.com/article",
        title="Example Article",
        sort_order=1,
    )


@pytest.fixture
def sample_file_data() -> bytes:
    """Return sample binary file data."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n"


@pytest.fixture
def sample_projects_list(sample_project_id: UUID) -> list[Project]:
    """Return a list of sample projects."""
    projects = []
    for i in range(3):
        project = Project(
            id=uuid4(),
            name=f"Test Project {i + 1}",
            description=f"Description for project {i + 1}",
            canvas_format=CanvasFormat.PPT169.value,
            status=ProjectStatus.DRAFT.value,
            current_step=PipelineStep.INIT.value,
            step_status=StepStatus.PENDING.value,
            llm_provider=LLMProvider.OPENAI.value,
            llm_model="gpt-4o",
            template_path=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=None,
        )
        projects.append(project)
    # First project uses the fixed ID
    projects[0].id = sample_project_id
    return projects


# ---------------------------------------------------------------------------
# Mock AsyncResult for Celery
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_celery_app() -> MagicMock:
    """Provide a mocked Celery app."""
    celery = MagicMock()
    celery.send_task = MagicMock()
    celery.control = MagicMock()
    return celery


# ---------------------------------------------------------------------------
# FastAPI App & Client
# ---------------------------------------------------------------------------


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI test application with mocked dependencies."""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for API testing."""
    from app.core.database import init_db, get_session_maker
    from app.api.deps import set_db_session_factory
    await init_db()  # Create tables + initialize session factory
    set_db_session_factory(get_session_maker())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
