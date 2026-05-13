"""
PPT Master Web Service — Project API Integration Tests.

Tests for project CRUD endpoints and pipeline actions.
Uses httpx.AsyncClient with mocked dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

from app.core.schemas import (
    CanvasFormat,
    LLMProvider,
    PipelineStep,
    ProjectStatus,
    StepStatus,
)
from app.models.project import Project


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _make_project(
    project_id: UUID | None = None,
    name: str = "Test Project",
    status: str = ProjectStatus.DRAFT.value,
    step: str = PipelineStep.INIT.value,
    step_status: str = StepStatus.PENDING.value,
) -> Project:
    """Create a project instance for testing."""
    return Project(
        id=project_id or uuid4(),
        name=name,
        description="Test description",
        canvas_format=CanvasFormat.PPT169.value,
        status=status,
        current_step=step,
        step_status=step_status,
        llm_provider=LLMProvider.OPENAI.value,
        llm_model="gpt-4o",
        template_path=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        completed_at=None,
    )


# ---------------------------------------------------------------------------
# Mock Dependency Fixtures (autouse)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def setup_deps() -> AsyncGenerator[None, None]:
    """Override FastAPI dependencies for all API tests."""
    from app.main import app
    from app.api import deps

    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.execute = AsyncMock()

    mock_storage = MagicMock()
    mock_storage.put = AsyncMock(return_value="test-key")
    mock_storage.get = AsyncMock(return_value=b"test-data")
    mock_storage.delete = AsyncMock()
    mock_storage.exists = AsyncMock(return_value=True)
    mock_storage.get_url = MagicMock(return_value="http://test/url")
    mock_storage.get_public_url = MagicMock(return_value="http://test/public")

    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    async def _mock_get_db_ro() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    async def _mock_get_storage() -> MagicMock:
        return mock_storage

    async def _mock_get_current_project(
        id: UUID, db: Any = MagicMock()
    ) -> Project:
        return _make_project(project_id=id)

    app.dependency_overrides[deps.get_db] = _mock_get_db
    app.dependency_overrides[deps.get_db_ro] = _mock_get_db_ro
    app.dependency_overrides[deps.get_storage] = _mock_get_storage
    app.dependency_overrides[deps.get_current_project] = _mock_get_current_project

    yield

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/projects — Create Project
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreateProjectAPI:
    """Tests for POST /api/projects endpoint."""

    async def test_create_project_success(self, client: AsyncClient) -> None:
        """Test creating a project with valid data returns 201."""
        mock_project = _make_project(name="API Test Project")

        with patch("app.api.projects.ProjectService.create", new_callable=AsyncMock, return_value=mock_project):
            response = await client.post(
                "/api/projects",
                json={
                    "name": "API Test Project",
                    "description": "Created via API",
                    "canvas_format": "ppt169",
                    "llm_provider": "openai",
                    "llm_model": "gpt-4o",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "API Test Project"

    async def test_create_project_validation_error(self, client: AsyncClient) -> None:
        """Test creating a project with empty name returns 422."""
        response = await client.post("/api/projects", json={"name": ""})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_project_missing_name(self, client: AsyncClient) -> None:
        """Test creating a project without name returns 422."""
        response = await client.post("/api/projects", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_project_name_too_long(self, client: AsyncClient) -> None:
        """Test creating a project with overly long name returns 422."""
        response = await client.post("/api/projects", json={"name": "A" * 256})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_project_invalid_canvas_format(self, client: AsyncClient) -> None:
        """Test creating a project with invalid canvas_format returns 422."""
        response = await client.post(
            "/api/projects",
            json={"name": "Test", "canvas_format": "invalid"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_project_invalid_llm_provider(self, client: AsyncClient) -> None:
        """Test creating a project with invalid llm_provider returns 422."""
        response = await client.post(
            "/api/projects",
            json={"name": "Test", "llm_provider": "google"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# GET /api/projects — List Projects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestListProjectsAPI:
    """Tests for GET /api/projects endpoint."""

    async def test_list_projects_success(self, client: AsyncClient) -> None:
        """Test listing projects returns 200 with items."""
        mock_projects = [_make_project(name=f"Project {i}") for i in range(3)]

        with patch("app.api.projects.ProjectService.get_list", new_callable=AsyncMock, return_value=(mock_projects, 3)):
            response = await client.get("/api/projects")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_projects_empty(self, client: AsyncClient) -> None:
        """Test listing projects returns 200 with empty list."""
        with patch("app.api.projects.ProjectService.get_list", new_callable=AsyncMock, return_value=([], 0)):
            response = await client.get("/api/projects")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    async def test_list_projects_with_pagination(self, client: AsyncClient) -> None:
        """Test listing projects with pagination params."""
        with patch("app.api.projects.ProjectService.get_list", new_callable=AsyncMock, return_value=([], 0)):
            response = await client.get("/api/projects?page=2&page_size=5")
        assert response.status_code == status.HTTP_200_OK

    async def test_list_projects_invalid_page(self, client: AsyncClient) -> None:
        """Test listing projects with invalid page returns 422."""
        response = await client.get("/api/projects?page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_list_projects_invalid_page_size(self, client: AsyncClient) -> None:
        """Test listing projects with invalid page_size returns 422."""
        response = await client.get("/api/projects?page_size=101")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_list_projects_with_status_filter(self, client: AsyncClient) -> None:
        """Test listing projects with valid status filter."""
        mock_projects = [_make_project(name="Draft Project")]
        with patch("app.api.projects.ProjectService.get_list", new_callable=AsyncMock, return_value=(mock_projects, 1)):
            response = await client.get("/api/projects?status_filter=draft")
        assert response.status_code == status.HTTP_200_OK

    async def test_list_projects_invalid_status_filter(self, client: AsyncClient) -> None:
        """Test listing projects with invalid status filter returns 422."""
        response = await client.get("/api/projects?status_filter=invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# GET /api/projects/{id} — Get Project Detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetProjectAPI:
    """Tests for GET /api/projects/{id} endpoint."""

    async def test_get_project_success(self, client: AsyncClient) -> None:
        """Test getting an existing project returns 200."""
        project_id = "12345678-1234-5678-1234-567812345678"
        response = await client.get(f"/api/projects/{project_id}")
        assert response.status_code == status.HTTP_200_OK

    async def test_get_project_invalid_uuid(self, client: AsyncClient) -> None:
        """Test getting a project with invalid UUID returns 422."""
        response = await client.get("/api/projects/not-a-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# PUT /api/projects/{id} — Update Project
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestUpdateProjectAPI:
    """Tests for PUT /api/projects/{id} endpoint."""

    async def test_update_project_success(self, client: AsyncClient) -> None:
        """Test updating a project with valid data returns 200."""
        mock_project = _make_project(name="Updated Name")

        with patch("app.api.projects.ProjectService.update", new_callable=AsyncMock, return_value=mock_project):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.put(
                f"/api/projects/{project_id}",
                json={"name": "Updated Name"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"

    async def test_update_project_validation_error(self, client: AsyncClient) -> None:
        """Test updating with invalid data returns 422."""
        project_id = "12345678-1234-5678-1234-567812345678"
        response = await client.put(
            f"/api/projects/{project_id}",
            json={"name": ""},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# DELETE /api/projects/{id} — Delete Project
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeleteProjectAPI:
    """Tests for DELETE /api/projects/{id} endpoint."""

    async def test_delete_project_success(self, client: AsyncClient) -> None:
        """Test deleting a project returns 204."""
        with patch("app.api.projects.ProjectService.delete", new_callable=AsyncMock):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.delete(f"/api/projects/{project_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_project_invalid_uuid(self, client: AsyncClient) -> None:
        """Test deleting with invalid UUID returns 422."""
        response = await client.delete("/api/projects/not-a-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# POST /api/projects/{id}/start — Start Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStartPipelineAPI:
    """Tests for POST /api/projects/{id}/start endpoint."""

    async def test_start_pipeline_success(self, client: AsyncClient) -> None:
        """Test starting pipeline returns 200."""
        mock_job = MagicMock()
        mock_job.id = str(uuid4())
        mock_job.step = "source_processing"
        mock_job.status = "running"

        with patch("app.api.projects.ProjectService.can_start_pipeline", new_callable=AsyncMock, return_value=True):
            with patch("app.services.pipeline_service.PipelineService.start_pipeline", new_callable=AsyncMock, return_value=mock_job):
                project_id = "12345678-1234-5678-1234-567812345678"
                response = await client.post(
                    f"/api/projects/{project_id}/start",
                    json={},
                )

        assert response.status_code == status.HTTP_200_OK

    async def test_start_pipeline_invalid_body(self, client: AsyncClient) -> None:
        """Test starting pipeline with invalid body returns 422."""
        project_id = "12345678-1234-5678-1234-567812345678"
        response = await client.post(
            f"/api/projects/{project_id}/start",
            json={"start_from_step": "invalid_step"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_start_pipeline_valid_step(self, client: AsyncClient) -> None:
        """Test starting pipeline with valid step returns 200."""
        mock_job = MagicMock()
        mock_job.id = str(uuid4())
        mock_job.step = "strategist"
        mock_job.status = "running"

        with patch("app.api.projects.ProjectService.can_start_pipeline", new_callable=AsyncMock, return_value=True):
            with patch("app.services.pipeline_service.PipelineService.start_pipeline", new_callable=AsyncMock, return_value=mock_job):
                project_id = "12345678-1234-5678-1234-567812345678"
                response = await client.post(
                    f"/api/projects/{project_id}/start",
                    json={"start_from_step": "strategist"},
                )

        assert response.status_code == status.HTTP_200_OK

    async def test_start_pipeline_cannot_start(self, client: AsyncClient) -> None:
        """Test starting pipeline when not allowed returns 400."""
        with patch("app.api.projects.ProjectService.can_start_pipeline", new_callable=AsyncMock, return_value=False):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.post(
                f"/api/projects/{project_id}/start",
                json={},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# POST /api/projects/{id}/cancel — Cancel Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCancelPipelineAPI:
    """Tests for POST /api/projects/{id}/cancel endpoint."""

    async def test_cancel_pipeline_success(self, client: AsyncClient) -> None:
        """Test cancelling pipeline returns 200."""
        mock_job = MagicMock()
        mock_job.id = str(uuid4())
        mock_job.status = "cancelled"

        with patch("app.api.projects.ProjectService.can_cancel_pipeline", new_callable=AsyncMock, return_value=True):
            with patch("app.services.pipeline_service.PipelineService.cancel_pipeline", new_callable=AsyncMock, return_value=mock_job):
                project_id = "12345678-1234-5678-1234-567812345678"
                response = await client.post(f"/api/projects/{project_id}/cancel")

        assert response.status_code == status.HTTP_200_OK

    async def test_cancel_pipeline_cannot_cancel(self, client: AsyncClient) -> None:
        """Test cancelling pipeline when not allowed returns 400."""
        with patch("app.api.projects.ProjectService.can_cancel_pipeline", new_callable=AsyncMock, return_value=False):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.post(f"/api/projects/{project_id}/cancel")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHealthCheckAPI:
    """Tests for /health endpoint."""

    async def test_health_check_returns_ok(self, client: AsyncClient) -> None:
        """Test health check returns ok status."""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "0.1.0"

    async def test_health_check_has_services(self, client: AsyncClient) -> None:
        """Test health check includes services info."""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "services" in data
        assert "api" in data["services"]


# ---------------------------------------------------------------------------
# WebSocket Status Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestWebSocketStatusAPI:
    """Tests for /ws-status endpoint."""

    async def test_ws_status_returns_data(self, client: AsyncClient) -> None:
        """Test WebSocket status endpoint returns data."""
        response = await client.get("/ws-status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# API Docs Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAPIDocs:
    """Tests for API documentation endpoints."""

    async def test_openapi_json_accessible(self, client: AsyncClient) -> None:
        """Test OpenAPI JSON is accessible."""
        response = await client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK

    async def test_docs_page_accessible(self, client: AsyncClient) -> None:
        """Test Swagger UI docs page is accessible."""
        response = await client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
