"""
PPT Master Web Service — ORM Model Tests.

Tests for Project, SourceFile, and DesignSpec model creation,
enum definitions, and relationship configurations.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import String

from app.db.base import Base
from app.models.design_spec import ConfirmationStatus, DesignSpec
from app.models.project import (
    CanvasFormat,
    PipelineStep,
    Project,
    ProjectStatus,
    StepStatus,
)
from app.models.source_file import ConversionStatus, SourceFile, SourceFileType


# ---------------------------------------------------------------------------
# Project Model Tests
# ---------------------------------------------------------------------------


class TestProjectModel:
    """Tests for the Project ORM model."""

    def test_project_table_name(self) -> None:
        """Test Project has correct table name."""
        assert Project.__tablename__ == "projects"

    def test_project_create_minimal(self) -> None:
        """Test creating a Project with minimal fields."""
        from sqlalchemy import inspect
        project = Project(name="Minimal Project")
        assert project.name == "Minimal Project"
        assert project.description is None
        assert project.template_path is None
        assert project.completed_at is None
        # SQLAlchemy defaults are applied at flush time, not on __init__
        # Verify the column defaults are configured correctly on the mapper
        mapper = inspect(Project)
        status_col = mapper.columns.get("status")
        assert status_col.default.arg == ProjectStatus.DRAFT.value
        format_col = mapper.columns.get("canvas_format")
        assert format_col.default.arg == CanvasFormat.PPT169.value
        step_col = mapper.columns.get("current_step")
        assert step_col.default.arg == PipelineStep.INIT.value
        step_status_col = mapper.columns.get("step_status")
        assert step_status_col.default.arg == StepStatus.PENDING.value
        llm_col = mapper.columns.get("llm_provider")
        assert llm_col.default.arg == "openai"
        model_col = mapper.columns.get("llm_model")
        assert model_col.default.arg == "gpt-4o"

    def test_project_create_full(self) -> None:
        """Test creating a Project with all fields."""
        project_id = uuid4()
        now = datetime.now(timezone.utc)
        project = Project(
            id=project_id,
            name="Full Project",
            description="A complete project",
            canvas_format=CanvasFormat.PPT43.value,
            status=ProjectStatus.PROCESSING.value,
            current_step=PipelineStep.STRATEGIST.value,
            step_status=StepStatus.RUNNING.value,
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-latest",
            template_path="/templates/custom",
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        assert project.id == project_id
        assert project.name == "Full Project"
        assert project.description == "A complete project"
        assert project.canvas_format == "ppt43"
        assert project.status == "processing"
        assert project.current_step == "strategist"
        assert project.step_status == "running"
        assert project.llm_provider == "anthropic"
        assert project.llm_model == "claude-3-5-sonnet-latest"
        assert project.template_path == "/templates/custom"

    def test_project_repr(self) -> None:
        """Test Project repr is informative."""
        project = Project(name="Test")
        repr_str = repr(project)
        assert "Project" in repr_str
        assert project.name in repr_str
        assert str(project.id) in repr_str

    def test_project_default_status(self) -> None:
        """Test Project default status is configured as DRAFT."""
        from sqlalchemy import inspect
        mapper = inspect(Project)
        status_col = mapper.columns.get("status")
        assert status_col.default.arg == ProjectStatus.DRAFT.value

    def test_project_default_step(self) -> None:
        """Test Project default step is configured as INIT."""
        from sqlalchemy import inspect
        mapper = inspect(Project)
        step_col = mapper.columns.get("current_step")
        assert step_col.default.arg == PipelineStep.INIT.value
        step_status_col = mapper.columns.get("step_status")
        assert step_status_col.default.arg == StepStatus.PENDING.value

    def test_project_relationships_defined(self) -> None:
        """Test Project has expected relationship attributes."""
        # Check that relationship attributes exist
        assert hasattr(Project, "source_files")
        assert hasattr(Project, "design_spec")
        assert hasattr(Project, "spec_lock")
        assert hasattr(Project, "image_resources")
        assert hasattr(Project, "svg_pages")
        assert hasattr(Project, "speaker_notes")
        assert hasattr(Project, "pptx_exports")
        assert hasattr(Project, "pipeline_jobs")


# ---------------------------------------------------------------------------
# SourceFile Model Tests
# ---------------------------------------------------------------------------


class TestSourceFileModel:
    """Tests for the SourceFile ORM model."""

    def test_source_file_table_name(self) -> None:
        """Test SourceFile has correct table name."""
        assert SourceFile.__tablename__ == "source_files"

    def test_source_file_create(self) -> None:
        """Test creating a SourceFile."""
        project_id = uuid4()
        source_id = uuid4()
        sf = SourceFile(
            id=source_id,
            project_id=project_id,
            original_filename="document.pdf",
            file_type=SourceFileType.PDF.value,
            storage_key=f"projects/{project_id}/sources/{source_id}/document.pdf",
            storage_backend="local",
            file_size=2048,
            conversion_status=ConversionStatus.PENDING.value,
            sort_order=0,
        )
        assert sf.id == source_id
        assert sf.project_id == project_id
        assert sf.original_filename == "document.pdf"
        assert sf.file_type == "pdf"
        assert sf.file_size == 2048
        assert sf.conversion_status == "pending"
        assert sf.sort_order == 0
        assert sf.markdown_content is None

    def test_source_file_repr(self) -> None:
        """Test SourceFile repr is informative."""
        project_id = uuid4()
        sf = SourceFile(
            project_id=project_id,
            original_filename="test.md",
            file_type=SourceFileType.MD.value,
            storage_key="test-key",
            file_size=100,
        )
        repr_str = repr(sf)
        assert "SourceFile" in repr_str
        assert "test.md" in repr_str

    def test_source_file_default_conversion_status(self) -> None:
        """Test SourceFile default conversion status is configured as PENDING."""
        from sqlalchemy import inspect
        mapper = inspect(SourceFile)
        status_col = mapper.columns.get("conversion_status")
        assert status_col.default.arg == ConversionStatus.PENDING.value

    def test_source_file_sort_order(self) -> None:
        """Test SourceFile sort_order field."""
        project_id = uuid4()
        sf = SourceFile(
            project_id=project_id,
            original_filename="ordered.txt",
            file_type=SourceFileType.TXT.value,
            storage_key="key",
            file_size=10,
            sort_order=5,
        )
        assert sf.sort_order == 5

    def test_source_file_relationship(self) -> None:
        """Test SourceFile has project relationship."""
        assert hasattr(SourceFile, "project")


# ---------------------------------------------------------------------------
# DesignSpec Model Tests
# ---------------------------------------------------------------------------


class TestDesignSpecModel:
    """Tests for the DesignSpec ORM model."""

    def test_design_spec_table_name(self) -> None:
        """Test DesignSpec has correct table name."""
        assert DesignSpec.__tablename__ == "design_specs"

    def test_design_spec_create(self) -> None:
        """Test creating a DesignSpec."""
        project_id = uuid4()
        spec = DesignSpec(
            project_id=project_id,
            confirmation_canvas="ppt169",
            confirmation_page_count=10,
            confirmation_audience="Engineers",
            confirmation_status=ConfirmationStatus.PENDING.value,
            spec_content="# Design Spec\n\n## Colors\n...",
        )
        assert spec.project_id == project_id
        assert spec.confirmation_canvas == "ppt169"
        assert spec.confirmation_page_count == 10
        assert spec.confirmation_audience == "Engineers"
        assert spec.confirmation_status == "pending"
        assert spec.spec_content == "# Design Spec\n\n## Colors\n..."
        assert spec.confirmed_at is None

    def test_design_spec_repr(self) -> None:
        """Test DesignSpec repr is informative."""
        project_id = uuid4()
        spec = DesignSpec(project_id=project_id)
        repr_str = repr(spec)
        assert "DesignSpec" in repr_str
        assert str(project_id) in repr_str

    def test_design_spec_default_confirmation_status(self) -> None:
        """Test DesignSpec default confirmation status is configured as PENDING."""
        from sqlalchemy import inspect
        mapper = inspect(DesignSpec)
        status_col = mapper.columns.get("confirmation_status")
        assert status_col.default.arg == ConfirmationStatus.PENDING.value

    def test_design_spec_all_confirmations(self) -> None:
        """Test DesignSpec with all Eight Confirmations set."""
        spec = DesignSpec(
            project_id=uuid4(),
            confirmation_canvas="ppt169",
            confirmation_page_count=15,
            confirmation_audience="Executives",
            confirmation_style_mode="A",
            confirmation_style_descriptor="Modern minimalist",
            confirmation_color_scheme={"primary": "#000", "background": "#fff"},
            confirmation_icon_approach="B",
            confirmation_typography={"title_font": "Arial", "body_font": "Helvetica"},
            confirmation_image_approach="C",
        )
        assert spec.confirmation_style_mode == "A"
        assert spec.confirmation_icon_approach == "B"
        assert spec.confirmation_image_approach == "C"
        assert spec.confirmation_color_scheme["primary"] == "#000"


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestProjectStatusEnum:
    """Tests for ProjectStatus enum."""

    def test_enum_values(self) -> None:
        """Test ProjectStatus has all expected values."""
        assert ProjectStatus.DRAFT.value == "draft"
        assert ProjectStatus.CONFIRMING.value == "confirming"
        assert ProjectStatus.PROCESSING.value == "processing"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.FAILED.value == "failed"

    def test_enum_is_str_enum(self) -> None:
        """Test ProjectStatus is a string enum."""
        assert issubclass(ProjectStatus, str)
        assert issubclass(ProjectStatus, enum.Enum)

    def test_enum_membership(self) -> None:
        """Test ProjectStatus membership check."""
        assert ProjectStatus("draft") == ProjectStatus.DRAFT
        assert ProjectStatus("processing") == ProjectStatus.PROCESSING

    def test_enum_invalid_value_raises(self) -> None:
        """Test invalid ProjectStatus value raises ValueError."""
        with pytest.raises(ValueError):
            ProjectStatus("invalid_status")


class TestPipelineStepEnum:
    """Tests for PipelineStep enum."""

    def test_enum_values(self) -> None:
        """Test PipelineStep has all expected values."""
        assert PipelineStep.INIT.value == "init"
        assert PipelineStep.SOURCE_PROCESSING.value == "source_processing"
        assert PipelineStep.STRATEGIST.value == "strategist"
        assert PipelineStep.IMAGE_ACQUISITION.value == "image_acquisition"
        assert PipelineStep.EXECUTOR.value == "executor"
        assert PipelineStep.POST_PROCESSING.value == "post_processing"
        assert PipelineStep.COMPLETED.value == "completed"

    def test_pipeline_step_count(self) -> None:
        """Test PipelineStep has exactly 7 members."""
        assert len(list(PipelineStep)) == 7


class TestStepStatusEnum:
    """Tests for StepStatus enum."""

    def test_enum_values(self) -> None:
        """Test StepStatus has all expected values."""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.WAITING_CONFIRMATION.value == "waiting_confirmation"


class TestCanvasFormatEnum:
    """Tests for CanvasFormat enum."""

    def test_enum_values(self) -> None:
        """Test CanvasFormat has all expected values."""
        assert CanvasFormat.PPT169.value == "ppt169"
        assert CanvasFormat.PPT43.value == "ppt43"
        assert CanvasFormat.XHS.value == "xhs"
        assert CanvasFormat.STORY.value == "story"


class TestSourceFileTypeEnum:
    """Tests for SourceFileType enum."""

    def test_enum_values(self) -> None:
        """Test SourceFileType has all expected values."""
        assert SourceFileType.PDF.value == "pdf"
        assert SourceFileType.DOCX.value == "docx"
        assert SourceFileType.XLSX.value == "xlsx"
        assert SourceFileType.PPTX.value == "pptx"
        assert SourceFileType.URL.value == "url"
        assert SourceFileType.MD.value == "md"
        assert SourceFileType.TXT.value == "txt"
        assert SourceFileType.HTML.value == "html"
        assert SourceFileType.EPUB.value == "epub"


class TestConversionStatusEnum:
    """Tests for ConversionStatus enum."""

    def test_enum_values(self) -> None:
        """Test ConversionStatus has all expected values."""
        assert ConversionStatus.PENDING.value == "pending"
        assert ConversionStatus.PROCESSING.value == "processing"
        assert ConversionStatus.COMPLETED.value == "completed"
        assert ConversionStatus.FAILED.value == "failed"


class TestConfirmationStatusEnum:
    """Tests for ConfirmationStatus enum."""

    def test_enum_values(self) -> None:
        """Test ConfirmationStatus has all expected values."""
        assert ConfirmationStatus.PENDING.value == "pending"
        assert ConfirmationStatus.CONFIRMED.value == "confirmed"


# ---------------------------------------------------------------------------
# Base Model Tests
# ---------------------------------------------------------------------------


class TestBaseModel:
    """Tests for SQLAlchemy Base."""

    def test_base_is_declarative(self) -> None:
        """Test Base is a SQLAlchemy DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)
