"""
PPT Master Web Service — Project Service Tests.

Tests for ProjectService CRUD operations, status management,
and pipeline control methods using mocked database sessions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from uuid import UUID, uuid4

import pytest

from app.core.schemas import (
    CanvasFormat,
    LLMProvider,
    PipelineStep,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
    StepStatus,
)
from app.models.project import Project
from app.services.project_service import ProjectService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_service(mock_db_session: MagicMock, storage: Any) -> ProjectService:
    """Create a ProjectService with mocked dependencies."""
    return ProjectService(db=mock_db_session, storage=storage)


# Need to import Any for type hints
from typing import Any


@pytest.fixture
def mock_scalar_result() -> MagicMock:
    """Create a mock scalar result that returns None by default."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Create Project Tests
# ---------------------------------------------------------------------------


class TestProjectServiceCreate:
    """Tests for ProjectService.create method."""

    @pytest.mark.asyncio
    async def test_create_project_minimal(
        self, project_service: ProjectService, mock_db_session: MagicMock
    ) -> None:
        """Test creating a project with minimal data."""
        data = ProjectCreate(name="Test Project")
        result = await project_service.create(data)

        assert isinstance(result, Project)
        assert result.name == "Test Project"
        assert result.description is None
        assert result.canvas_format == CanvasFormat.PPT169.value
        assert result.status == ProjectStatus.DRAFT.value
        assert result.current_step == PipelineStep.INIT.value
        assert result.step_status == StepStatus.PENDING.value
        assert result.llm_provider == LLMProvider.OPENAI.value
        assert result.llm_model == "gpt-4o"
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_project_full(
        self, project_service: ProjectService, mock_db_session: MagicMock
    ) -> None:
        """Test creating a project with all fields."""
        data = ProjectCreate(
            name="Full Project",
            description="Detailed description",
            canvas_format=CanvasFormat.PPT43,
            llm_provider=LLMProvider.ANTHROPIC,
            llm_model="claude-3-5-sonnet-latest",
        )
        result = await project_service.create(data)

        assert result.name == "Full Project"
        assert result.description == "Detailed description"
        assert result.canvas_format == CanvasFormat.PPT43.value
        assert result.llm_provider == LLMProvider.ANTHROPIC.value
        assert result.llm_model == "claude-3-5-sonnet-latest"

    @pytest.mark.asyncio
    async def test_create_project_anthropic(
        self, project_service: ProjectService
    ) -> None:
        """Test creating a project with Anthropic LLM."""
        data = ProjectCreate(
            name="Anthropic Project",
            llm_provider=LLMProvider.ANTHROPIC,
            llm_model="claude-3-haiku-latest",
        )
        result = await project_service.create(data)
        assert result.llm_provider == "anthropic"
        assert result.llm_model == "claude-3-haiku-latest"

    @pytest.mark.asyncio
    async def test_create_project_xhs_canvas(
        self, project_service: ProjectService
    ) -> None:
        """Test creating a project with XHS canvas format."""
        data = ProjectCreate(name="XHS Project", canvas_format=CanvasFormat.XHS)
        result = await project_service.create(data)
        assert result.canvas_format == CanvasFormat.XHS.value


# ---------------------------------------------------------------------------
# Get Project Tests
# ---------------------------------------------------------------------------


class TestProjectServiceGetById:
    """Tests for ProjectService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test get_by_id returns project when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db_session.execute.return_value = mock_result

        result = await project_service.get_by_id(sample_project.id)

        assert result is sample_project
        assert result.name == "Test Project"
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, project_service: ProjectService, mock_db_session: MagicMock
    ) -> None:
        """Test get_by_id returns None when project not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await project_service.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_relationships_loaded(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test get_by_id loads relationships."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db_session.execute.return_value = mock_result

        result = await project_service.get_by_id(sample_project.id)

        assert result is not None
        # Verify the query includes selectinload options
        call_args = mock_db_session.execute.call_args
        assert call_args is not None


# ---------------------------------------------------------------------------
# List Projects Tests
# ---------------------------------------------------------------------------


class TestProjectServiceGetList:
    """Tests for ProjectService.get_list method."""

    @pytest.mark.asyncio
    async def test_list_projects_default(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_projects_list: list[Project],
    ) -> None:
        """Test list projects with default pagination."""
        # First execute call returns projects, second returns count
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_projects_list
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = len(sample_projects_list)

        mock_db_session.execute.side_effect = [mock_result, mock_count_result]

        projects, total = await project_service.get_list()

        assert len(projects) == 3
        assert total == 3
        assert projects[0].name == "Test Project 1"

    @pytest.mark.asyncio
    async def test_list_projects_with_pagination(
        self, project_service: ProjectService, mock_db_session: MagicMock
    ) -> None:
        """Test list projects with custom offset and limit."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        mock_db_session.execute.side_effect = [mock_result, mock_count_result]

        projects, total = await project_service.get_list(offset=20, limit=10)

        assert len(projects) == 0
        assert total == 100

    @pytest.mark.asyncio
    async def test_list_projects_with_status_filter(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_projects_list: list[Project],
    ) -> None:
        """Test list projects filtered by status."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            p for p in sample_projects_list if p.status == ProjectStatus.DRAFT.value
        ]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3

        mock_db_session.execute.side_effect = [mock_result, mock_count_result]

        projects, total = await project_service.get_list(
            status_filter=ProjectStatus.DRAFT
        )

        assert len(projects) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_list_projects_empty_result(
        self, project_service: ProjectService, mock_db_session: MagicMock
    ) -> None:
        """Test list projects returns empty list when no projects exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_db_session.execute.side_effect = [mock_result, mock_count_result]

        projects, total = await project_service.get_list()

        assert len(projects) == 0
        assert total == 0


# ---------------------------------------------------------------------------
# Update Project Tests
# ---------------------------------------------------------------------------


class TestProjectServiceUpdate:
    """Tests for ProjectService.update method."""

    @pytest.mark.asyncio
    async def test_update_name(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test updating project name."""
        data = ProjectUpdate(name="Updated Name")
        result = await project_service.update(sample_project, data)

        assert result.name == "Updated Name"
        # Other fields unchanged
        assert result.description == "A test project for unit tests"
        mock_db_session.flush.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_canvas_format(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test updating canvas format."""
        data = ProjectUpdate(canvas_format=CanvasFormat.PPT43)
        result = await project_service.update(sample_project, data)

        assert result.canvas_format == CanvasFormat.PPT43.value

    @pytest.mark.asyncio
    async def test_update_llm_settings(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test updating LLM settings."""
        data = ProjectUpdate(
            llm_provider=LLMProvider.ANTHROPIC,
            llm_model="claude-3-5-sonnet-latest",
        )
        result = await project_service.update(sample_project, data)

        assert result.llm_provider == LLMProvider.ANTHROPIC.value
        assert result.llm_model == "claude-3-5-sonnet-latest"

    @pytest.mark.asyncio
    async def test_update_partial_no_change_to_unset_fields(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test that unset fields are not modified."""
        original_name = sample_project.name
        original_format = sample_project.canvas_format

        data = ProjectUpdate(description="Only desc updated")
        result = await project_service.update(sample_project, data)

        assert result.name == original_name
        assert result.canvas_format == original_format
        assert result.description == "Only desc updated"

    @pytest.mark.asyncio
    async def test_update_template_path(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test updating template path."""
        data = ProjectUpdate(template_path="/templates/custom")
        result = await project_service.update(sample_project, data)

        assert result.template_path == "/templates/custom"


# ---------------------------------------------------------------------------
# Delete Project Tests
# ---------------------------------------------------------------------------


class TestProjectServiceDelete:
    """Tests for ProjectService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_project(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test deleting a project."""
        await project_service.delete(sample_project)

        mock_db_session.delete.assert_called_once_with(sample_project)
        mock_db_session.flush.assert_awaited()


# ---------------------------------------------------------------------------
# Status Management Tests
# ---------------------------------------------------------------------------


class TestProjectServiceSetStatus:
    """Tests for ProjectService.set_status method."""

    @pytest.mark.asyncio
    async def test_set_status_processing(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test setting project status to PROCESSING."""
        result = await project_service.set_status(
            sample_project, ProjectStatus.PROCESSING
        )
        assert result.status == ProjectStatus.PROCESSING.value
        mock_db_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_status_completed(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test setting project status to COMPLETED."""
        result = await project_service.set_status(
            sample_project, ProjectStatus.COMPLETED
        )
        assert result.status == ProjectStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_set_status_failed(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test setting project status to FAILED."""
        result = await project_service.set_status(sample_project, ProjectStatus.FAILED)
        assert result.status == ProjectStatus.FAILED.value


class TestProjectServiceSetStep:
    """Tests for ProjectService.set_step method."""

    @pytest.mark.asyncio
    async def test_set_step(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test setting pipeline step."""
        result = await project_service.set_step(
            sample_project, PipelineStep.STRATEGIST, StepStatus.RUNNING
        )
        assert result.current_step == PipelineStep.STRATEGIST.value
        assert result.step_status == StepStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_set_step_without_status(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test setting step without changing status."""
        original_status = sample_project.step_status
        result = await project_service.set_step(
            sample_project, PipelineStep.EXECUTOR
        )
        assert result.current_step == PipelineStep.EXECUTOR.value
        assert result.step_status == original_status


class TestProjectServiceSetStepStatus:
    """Tests for ProjectService.set_step_status method."""

    @pytest.mark.asyncio
    async def test_set_step_status_running(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test setting step status to RUNNING."""
        result = await project_service.set_step_status(
            sample_project, StepStatus.RUNNING
        )
        assert result.step_status == StepStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_set_step_status_failed(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test setting step status to FAILED."""
        result = await project_service.set_step_status(
            sample_project, StepStatus.FAILED
        )
        assert result.step_status == StepStatus.FAILED.value


class TestProjectServiceCompleteProject:
    """Tests for ProjectService.complete_project method."""

    @pytest.mark.asyncio
    async def test_complete_project(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test marking project as completed."""
        result = await project_service.complete_project(sample_project)
        assert result.status == ProjectStatus.COMPLETED.value
        assert result.current_step == PipelineStep.COMPLETED.value
        assert result.step_status == StepStatus.COMPLETED.value
        assert result.completed_at is not None


class TestProjectServiceFailProject:
    """Tests for ProjectService.fail_project method."""

    @pytest.mark.asyncio
    async def test_fail_project(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test marking project as failed."""
        result = await project_service.fail_project(
            sample_project, "Something went wrong"
        )
        assert result.status == ProjectStatus.FAILED.value
        assert result.step_status == StepStatus.FAILED.value


# ---------------------------------------------------------------------------
# Pipeline Control Tests
# ---------------------------------------------------------------------------


class TestProjectServiceCanStartPipeline:
    """Tests for ProjectService.can_start_pipeline method."""

    @pytest.mark.asyncio
    async def test_can_start_from_draft(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline can start from DRAFT status."""
        sample_project.status = ProjectStatus.DRAFT.value
        assert await project_service.can_start_pipeline(sample_project) is True

    @pytest.mark.asyncio
    async def test_can_start_from_confirming(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline can start from CONFIRMING status."""
        sample_project.status = ProjectStatus.CONFIRMING.value
        assert await project_service.can_start_pipeline(sample_project) is True

    @pytest.mark.asyncio
    async def test_can_start_from_failed(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline can start from FAILED status."""
        sample_project.status = ProjectStatus.FAILED.value
        assert await project_service.can_start_pipeline(sample_project) is True

    @pytest.mark.asyncio
    async def test_cannot_start_from_processing(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline cannot start from PROCESSING status."""
        sample_project.status = ProjectStatus.PROCESSING.value
        assert await project_service.can_start_pipeline(sample_project) is False

    @pytest.mark.asyncio
    async def test_cannot_start_from_completed(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline cannot start from COMPLETED status."""
        sample_project.status = ProjectStatus.COMPLETED.value
        assert await project_service.can_start_pipeline(sample_project) is False


class TestProjectServiceCanCancelPipeline:
    """Tests for ProjectService.can_cancel_pipeline method."""

    @pytest.mark.asyncio
    async def test_can_cancel_running(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline can cancel when running."""
        sample_project.status = ProjectStatus.PROCESSING.value
        sample_project.step_status = StepStatus.RUNNING.value
        assert await project_service.can_cancel_pipeline(sample_project) is True

    @pytest.mark.asyncio
    async def test_cannot_cancel_not_processing(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline cannot cancel when not processing."""
        sample_project.status = ProjectStatus.DRAFT.value
        sample_project.step_status = StepStatus.RUNNING.value
        assert await project_service.can_cancel_pipeline(sample_project) is False

    @pytest.mark.asyncio
    async def test_cannot_cancel_not_running(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline cannot cancel when not running."""
        sample_project.status = ProjectStatus.PROCESSING.value
        sample_project.step_status = StepStatus.PENDING.value
        assert await project_service.can_cancel_pipeline(sample_project) is False


class TestProjectServiceCanResumePipeline:
    """Tests for ProjectService.can_resume_pipeline method."""

    @pytest.mark.asyncio
    async def test_can_resume_from_failed(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline can resume from FAILED status."""
        sample_project.status = ProjectStatus.FAILED.value
        assert await project_service.can_resume_pipeline(sample_project) is True

    @pytest.mark.asyncio
    async def test_can_resume_from_confirming(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline can resume from CONFIRMING status."""
        sample_project.status = ProjectStatus.CONFIRMING.value
        assert await project_service.can_resume_pipeline(sample_project) is True

    @pytest.mark.asyncio
    async def test_cannot_resume_from_draft(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline cannot resume from DRAFT status."""
        sample_project.status = ProjectStatus.DRAFT.value
        assert await project_service.can_resume_pipeline(sample_project) is False

    @pytest.mark.asyncio
    async def test_cannot_resume_from_processing(
        self, project_service: ProjectService, sample_project: Project
    ) -> None:
        """Test pipeline cannot resume from PROCESSING status."""
        sample_project.status = ProjectStatus.PROCESSING.value
        assert await project_service.can_resume_pipeline(sample_project) is False


# ---------------------------------------------------------------------------
# Statistics Tests
# ---------------------------------------------------------------------------


class TestProjectServiceGetStats:
    """Tests for ProjectService.get_project_stats method."""

    @pytest.mark.asyncio
    async def test_get_stats_empty_project(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test stats for project with no sources, pages, or exports."""
        mock_db_session.scalar = AsyncMock(return_value=0)

        stats = await project_service.get_project_stats(sample_project.id)

        assert stats["source_count"] == 0
        assert stats["svg_page_count"] == 0
        assert stats["export_count"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(
        self,
        project_service: ProjectService,
        mock_db_session: MagicMock,
        sample_project: Project,
    ) -> None:
        """Test stats for project with data."""
        mock_db_session.scalar = AsyncMock(side_effect=[5, 10, 2])

        stats = await project_service.get_project_stats(sample_project.id)

        assert stats["source_count"] == 5
        assert stats["svg_page_count"] == 10
        assert stats["export_count"] == 2
