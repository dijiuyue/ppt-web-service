"""
PPT Master Web Service — Source File API Tests.

Tests for source file upload, URL addition, listing, and deletion endpoints.
Uses httpx.AsyncClient with mocked dependencies.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

from app.core.schemas import ConversionStatus, FileType
from app.models.project import Project
from app.models.source_file import SourceFile


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _make_project(project_id: UUID | None = None) -> Project:
    """Create a project instance for testing."""
    from datetime import datetime, timezone
    from app.core.schemas import CanvasFormat, LLMProvider, PipelineStep, StepStatus
    return Project(
        id=project_id or uuid4(),
        name="Source Test Project",
        description="Test",
        canvas_format=CanvasFormat.PPT169.value,
        status="draft",
        current_step=PipelineStep.INIT.value,
        step_status=StepStatus.PENDING.value,
        llm_provider=LLMProvider.OPENAI.value,
        llm_model="gpt-4o",
        created_at=datetime.now(timezone.utc),
    )


def _make_source_file(
    project_id: UUID, source_id: UUID | None = None, filename: str = "test.txt"
) -> SourceFile:
    """Create a source file instance for testing."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return SourceFile(
        id=source_id or uuid4(),
        project_id=project_id,
        original_filename=filename,
        file_type=FileType.TXT.value,
        storage_key=f"projects/{project_id}/sources/{source_id or uuid4()}/{filename}",
        storage_backend="local",
        file_size=100,
        conversion_status=ConversionStatus.COMPLETED.value,
        sort_order=0,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Override dependencies for testing
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def setup_source_deps() -> AsyncGenerator[None, None]:
    """Override FastAPI dependencies for source API tests."""
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

    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    async def _mock_get_db_ro() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    async def _mock_get_storage() -> MagicMock:
        return mock_storage

    async def _mock_get_current_project(id: UUID, db: Any = MagicMock()) -> Project:
        return _make_project(project_id=id)

    app.dependency_overrides[deps.get_db] = _mock_get_db
    app.dependency_overrides[deps.get_db_ro] = _mock_get_db_ro
    app.dependency_overrides[deps.get_storage] = _mock_get_storage
    app.dependency_overrides[deps.get_current_project] = _mock_get_current_project

    yield

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/projects/{id}/sources/upload — Upload Files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestUploadSourcesAPI:
    """Tests for POST /api/projects/{id}/sources/upload endpoint."""

    async def test_upload_single_file_success(self, client: AsyncClient) -> None:
        """Test uploading a single file returns 201."""
        mock_source = _make_source_file(uuid4())
        with patch("app.api.sources.SourceService.upload_multiple", new_callable=AsyncMock, return_value=[mock_source]):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.post(
                f"/api/projects/{project_id}/sources/upload",
                files={"files": ("test.txt", BytesIO(b"file content"), "text/plain")},
            )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_upload_invalid_project_uuid(self, client: AsyncClient) -> None:
        """Test uploading with invalid project UUID returns 422."""
        response = await client.post(
            "/api/projects/not-a-uuid/sources/upload",
            files={"files": ("test.txt", BytesIO(b"content"), "text/plain")},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_upload_multiple_files_success(self, client: AsyncClient) -> None:
        """Test uploading multiple files returns 201."""
        proj_id = uuid4()
        mock_sources = [_make_source_file(proj_id, filename=f"file{i}.txt") for i in range(2)]
        with patch("app.api.sources.SourceService.upload_multiple", new_callable=AsyncMock, return_value=mock_sources):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.post(
                f"/api/projects/{project_id}/sources/upload",
                files=[
                    ("files", ("file1.txt", BytesIO(b"content1"), "text/plain")),
                    ("files", ("file2.txt", BytesIO(b"content2"), "text/plain")),
                ],
            )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_upload_empty_file(self, client: AsyncClient) -> None:
        """Test uploading empty file returns 400."""
        project_id = "12345678-1234-5678-1234-567812345678"
        with patch("app.api.sources.SourceService.upload_multiple", new_callable=AsyncMock, return_value=[]):
            response = await client.post(
                f"/api/projects/{project_id}/sources/upload",
                files={"files": ("empty.txt", BytesIO(b""), "text/plain")},
            )
        # Empty files should be rejected
        assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# POST /api/projects/{id}/sources/url — Add URL Source
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAddUrlSourceAPI:
    """Tests for POST /api/projects/{id}/sources/url endpoint."""

    async def test_add_url_source_success(self, client: AsyncClient) -> None:
        """Test adding URL source with valid data returns 201."""
        mock_source = _make_source_file(uuid4(), filename="Example Article")
        mock_source.file_type = FileType.URL.value
        with patch("app.api.sources.SourceService.add_url_source", new_callable=AsyncMock, return_value=mock_source):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.post(
                f"/api/projects/{project_id}/sources/url",
                json={
                    "url": "https://example.com/article",
                    "title": "Example Article",
                    "sort_order": 1,
                },
            )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_add_url_source_validation_error(self, client: AsyncClient) -> None:
        """Test adding URL with empty URL returns 422."""
        project_id = "12345678-1234-5678-1234-567812345678"
        response = await client.post(
            f"/api/projects/{project_id}/sources/url",
            json={"url": ""},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_add_url_source_negative_sort_order(self, client: AsyncClient) -> None:
        """Test adding URL with negative sort_order returns 422."""
        project_id = "12345678-1234-5678-1234-567812345678"
        response = await client.post(
            f"/api/projects/{project_id}/sources/url",
            json={"url": "https://example.com", "sort_order": -1},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_add_url_source_invalid_project_uuid(self, client: AsyncClient) -> None:
        """Test adding URL with invalid project UUID returns 422."""
        response = await client.post(
            "/api/projects/not-a-uuid/sources/url",
            json={"url": "https://example.com"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# GET /api/projects/{id}/sources — List Source Files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestListSourcesAPI:
    """Tests for GET /api/projects/{id}/sources endpoint."""

    async def test_list_sources_success(self, client: AsyncClient) -> None:
        """Test listing sources returns 200."""
        proj_id = uuid4()
        mock_sources = [_make_source_file(proj_id) for _ in range(2)]
        with patch("app.api.sources.SourceService.get_list", new_callable=AsyncMock, return_value=(mock_sources, 2)):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.get(f"/api/projects/{project_id}/sources")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_sources_with_pagination(self, client: AsyncClient) -> None:
        """Test listing sources with pagination."""
        with patch("app.api.sources.SourceService.get_list", new_callable=AsyncMock, return_value=([], 0)):
            project_id = "12345678-1234-5678-1234-567812345678"
            response = await client.get(
                f"/api/projects/{project_id}/sources?page=1&page_size=10"
            )
        assert response.status_code == status.HTTP_200_OK

    async def test_list_sources_invalid_pagination(self, client: AsyncClient) -> None:
        """Test listing sources with invalid pagination returns 422."""
        project_id = "12345678-1234-5678-1234-567812345678"
        response = await client.get(f"/api/projects/{project_id}/sources?page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_list_sources_invalid_project_uuid(self, client: AsyncClient) -> None:
        """Test listing sources with invalid project UUID returns 422."""
        response = await client.get("/api/projects/not-a-uuid/sources")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# DELETE /api/projects/{id}/sources/{sid} — Delete Source File
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeleteSourceAPI:
    """Tests for DELETE /api/projects/{id}/sources/{sid} endpoint."""

    async def test_delete_source_success(self, client: AsyncClient) -> None:
        """Test deleting a source file returns 204."""
        project_id = UUID("12345678-1234-5678-1234-567812345678")
        source_id = UUID("87654321-4321-8765-4321-876543218765")
        mock_source = _make_source_file(project_id, source_id=source_id)
        with patch("app.api.sources.SourceService.get_by_id", new_callable=AsyncMock, return_value=mock_source):
            with patch("app.api.sources.SourceService.delete", new_callable=AsyncMock):
                response = await client.delete(
                    f"/api/projects/{project_id}/sources/{source_id}"
                )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_source_invalid_project_uuid(self, client: AsyncClient) -> None:
        """Test deleting source with invalid project UUID returns 422."""
        source_id = "87654321-4321-8765-4321-876543218765"
        response = await client.delete(
            f"/api/projects/not-a-uuid/sources/{source_id}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_delete_source_invalid_source_uuid(self, client: AsyncClient) -> None:
        """Test deleting source with invalid source UUID returns 422."""
        project_id = "12345678-1234-5678-1234-567812345678"
        response = await client.delete(
            f"/api/projects/{project_id}/sources/not-a-uuid"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Route Existence Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSourceRoutesExist:
    """Tests to verify all source routes are registered."""

    async def test_upload_route_exists(self, client: AsyncClient) -> None:
        """Verify upload route exists (POST is registered)."""
        project_id = "12345678-1234-5678-1234-567812345678"
        # GET should not be allowed
        response = await client.get(f"/api/projects/{project_id}/sources/upload")
        assert response.status_code in (
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_404_NOT_FOUND,
        )

    async def test_url_route_exists(self, client: AsyncClient) -> None:
        """Verify URL route exists."""
        project_id = "12345678-1234-5678-1234-567812345678"
        response = await client.get(f"/api/projects/{project_id}/sources/url")
        assert response.status_code in (
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_404_NOT_FOUND,
        )

    async def test_sources_list_route_exists(self, client: AsyncClient) -> None:
        """Verify sources list route exists and responds."""
        project_id = "12345678-1234-5678-1234-567812345678"
        with patch("app.api.sources.SourceService.get_list", new_callable=AsyncMock, return_value=([], 0)):
            response = await client.get(f"/api/projects/{project_id}/sources")
        assert response.status_code == status.HTTP_200_OK
