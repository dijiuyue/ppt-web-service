"""
PPT Master Web Service — Pydantic Schema Tests.

Tests for request/response schema validation, serialization,
and edge cases including boundary conditions and invalid enum values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.core.schemas import (
    CanvasFormat,
    ColorScheme,
    ConfirmationUpdate,
    FileType,
    LLMProvider,
    PipelineStep,
    ProjectCreate,
    ProjectResponse,
    ProjectStartRequest,
    ProjectStatus,
    ProjectUpdate,
    SourceUrlAdd,
    StepStatus,
    TypographySpec,
)


# ---------------------------------------------------------------------------
# ProjectCreate Schema Tests
# ---------------------------------------------------------------------------


class TestProjectCreateSchema:
    """Tests for ProjectCreate schema validation."""

    def test_create_valid_minimal(self) -> None:
        """Test ProjectCreate with minimal valid data."""
        data = ProjectCreate(name="Test Project")
        assert data.name == "Test Project"
        assert data.description is None
        assert data.canvas_format == CanvasFormat.PPT169
        assert data.llm_provider == LLMProvider.OPENAI
        assert data.llm_model == "gpt-4o"

    def test_create_valid_full(self) -> None:
        """Test ProjectCreate with all fields."""
        data = ProjectCreate(
            name="Full Project",
            description="A detailed description",
            canvas_format=CanvasFormat.PPT43,
            llm_provider=LLMProvider.ANTHROPIC,
            llm_model="claude-3-5-sonnet-latest",
        )
        assert data.name == "Full Project"
        assert data.description == "A detailed description"
        assert data.canvas_format == CanvasFormat.PPT43
        assert data.llm_provider == LLMProvider.ANTHROPIC
        assert data.llm_model == "claude-3-5-sonnet-latest"

    def test_create_name_required(self) -> None:
        """Test ProjectCreate requires name field."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_create_name_empty_string_raises(self) -> None:
        """Test ProjectCreate with empty name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(name="")
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("name",) and "too_short" in str(e.get("type", ""))
            for e in errors
        )

    def test_create_name_whitespace_only_allowed(self) -> None:
        """Test ProjectCreate with whitespace-only name is allowed (min_length passes)."""
        # Pydantic v2 min_length=1 only checks length, not content
        # Whitespace-only string has length > 0, so it passes
        data = ProjectCreate(name="   ")
        assert data.name == "   "

    def test_create_name_max_length(self) -> None:
        """Test ProjectCreate with max-length name succeeds."""
        long_name = "A" * 255
        data = ProjectCreate(name=long_name)
        assert data.name == long_name

    def test_create_name_too_long_raises(self) -> None:
        """Test ProjectCreate with overly long name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(name="A" * 256)
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("name",) and "too_long" in str(e.get("type", ""))
            for e in errors
        )

    def test_create_description_max_length(self) -> None:
        """Test ProjectCreate description at max length."""
        desc = "B" * 2000
        data = ProjectCreate(name="Test", description=desc)
        assert data.description == desc

    def test_create_description_too_long_raises(self) -> None:
        """Test ProjectCreate with overly long description raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(name="Test", description="B" * 2001)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("description",) for e in errors)

    def test_create_invalid_canvas_format(self) -> None:
        """Test ProjectCreate with invalid canvas format raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(name="Test", canvas_format="invalid_format")  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("canvas_format",) for e in errors)

    def test_create_invalid_llm_provider(self) -> None:
        """Test ProjectCreate with invalid LLM provider raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(name="Test", llm_provider="google")  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("llm_provider",) for e in errors)


# ---------------------------------------------------------------------------
# ProjectUpdate Schema Tests
# ---------------------------------------------------------------------------


class TestProjectUpdateSchema:
    """Tests for ProjectUpdate schema validation."""

    def test_update_empty(self) -> None:
        """Test ProjectUpdate with no fields (partial update)."""
        data = ProjectUpdate()
        assert data.name is None
        assert data.description is None
        assert data.canvas_format is None
        assert data.llm_provider is None
        assert data.llm_model is None
        assert data.template_path is None

    def test_update_single_field(self) -> None:
        """Test ProjectUpdate with one field."""
        data = ProjectUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.description is None

    def test_update_all_fields(self) -> None:
        """Test ProjectUpdate with all fields."""
        data = ProjectUpdate(
            name="Updated",
            description="New desc",
            canvas_format=CanvasFormat.XHS,
            llm_provider=LLMProvider.ANTHROPIC,
            llm_model="claude-3-haiku-latest",
            template_path="/templates/new",
        )
        assert data.name == "Updated"
        assert data.canvas_format == CanvasFormat.XHS
        assert data.template_path == "/templates/new"

    def test_update_empty_name_raises(self) -> None:
        """Test ProjectUpdate with empty name raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectUpdate(name="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


# ---------------------------------------------------------------------------
# ProjectResponse Schema Tests
# ---------------------------------------------------------------------------


class TestProjectResponseSchema:
    """Tests for ProjectResponse schema."""

    def test_response_valid(self) -> None:
        """Test ProjectResponse with valid data."""
        now = datetime.now(timezone.utc)
        data = ProjectResponse(
            id=uuid4(),
            name="Test Project",
            description="A test project",
            canvas_format="ppt169",
            status=ProjectStatus.DRAFT,
            current_step=PipelineStep.INIT,
            step_status=StepStatus.PENDING,
            llm_provider="openai",
            llm_model="gpt-4o",
            template_path=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        assert data.name == "Test Project"
        assert data.status == ProjectStatus.DRAFT

    def test_response_required_fields(self) -> None:
        """Test ProjectResponse requires mandatory fields."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            ProjectResponse(
                id=uuid4(),
                name="Test",
                # missing required fields
                created_at=now,
                updated_at=now,
            )


# ---------------------------------------------------------------------------
# ProjectStartRequest Schema Tests
# ---------------------------------------------------------------------------


class TestProjectStartRequestSchema:
    """Tests for ProjectStartRequest schema."""

    def test_default_no_step(self) -> None:
        """Test ProjectStartRequest defaults to None."""
        req = ProjectStartRequest()
        assert req.start_from_step is None

    def test_with_valid_step(self) -> None:
        """Test ProjectStartRequest with a valid step."""
        req = ProjectStartRequest(start_from_step=PipelineStep.STRATEGIST)
        assert req.start_from_step == PipelineStep.STRATEGIST


# ---------------------------------------------------------------------------
# SourceUrlAdd Schema Tests
# ---------------------------------------------------------------------------


class TestSourceUrlAddSchema:
    """Tests for SourceUrlAdd schema."""

    def test_valid_url(self) -> None:
        """Test SourceUrlAdd with valid URL."""
        data = SourceUrlAdd(url="https://example.com")
        assert data.url == "https://example.com"
        assert data.title is None
        assert data.sort_order == 0

    def test_url_with_title(self) -> None:
        """Test SourceUrlAdd with URL and title."""
        data = SourceUrlAdd(url="https://example.com", title="Example", sort_order=2)
        assert data.title == "Example"
        assert data.sort_order == 2

    def test_empty_url_raises(self) -> None:
        """Test SourceUrlAdd with empty URL raises error."""
        with pytest.raises(ValidationError) as exc_info:
            SourceUrlAdd(url="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) for e in errors)

    def test_negative_sort_order_raises(self) -> None:
        """Test SourceUrlAdd with negative sort_order raises error."""
        with pytest.raises(ValidationError) as exc_info:
            SourceUrlAdd(url="https://example.com", sort_order=-1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sort_order",) for e in errors)


# ---------------------------------------------------------------------------
# ConfirmationUpdate Schema Tests
# ---------------------------------------------------------------------------


class TestConfirmationUpdateSchema:
    """Tests for ConfirmationUpdate schema."""

    def test_empty_update(self) -> None:
        """Test ConfirmationUpdate with no fields."""
        data = ConfirmationUpdate()
        assert data.confirmation_canvas is None
        assert data.confirmation_page_count is None

    def test_full_update(self) -> None:
        """Test ConfirmationUpdate with all fields."""
        data = ConfirmationUpdate(
            confirmation_canvas="ppt169",
            confirmation_page_count=10,
            confirmation_audience="Developers",
            confirmation_style_mode="A",
            confirmation_style_descriptor="Clean modern",
            confirmation_color_scheme=ColorScheme(
                primary="#000000", secondary="#ffffff"
            ),
            confirmation_icon_approach="B",
            confirmation_typography=TypographySpec(
                title_font="Arial", body_font="Helvetica"
            ),
            confirmation_image_approach="C",
        )
        assert data.confirmation_page_count == 10
        assert data.confirmation_style_mode == "A"
        assert data.confirmation_color_scheme.primary == "#000000"

    def test_page_count_bounds(self) -> None:
        """Test ConfirmationUpdate page_count boundary values."""
        data_min = ConfirmationUpdate(confirmation_page_count=1)
        assert data_min.confirmation_page_count == 1

        data_max = ConfirmationUpdate(confirmation_page_count=100)
        assert data_max.confirmation_page_count == 100

    def test_page_count_too_low_raises(self) -> None:
        """Test page_count below 1 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfirmationUpdate(confirmation_page_count=0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confirmation_page_count",) for e in errors)

    def test_page_count_too_high_raises(self) -> None:
        """Test page_count above 100 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfirmationUpdate(confirmation_page_count=101)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confirmation_page_count",) for e in errors)


# ---------------------------------------------------------------------------
# Enum Validation Tests
# ---------------------------------------------------------------------------


class TestEnumValidation:
    """Tests for enum value validation in schemas."""

    def test_project_status_values(self) -> None:
        """Test all ProjectStatus enum values."""
        assert ProjectStatus.DRAFT == "draft"
        assert ProjectStatus.CONFIRMING == "confirming"
        assert ProjectStatus.PROCESSING == "processing"
        assert ProjectStatus.COMPLETED == "completed"
        assert ProjectStatus.FAILED == "failed"

    def test_pipeline_step_values(self) -> None:
        """Test all PipelineStep enum values."""
        assert PipelineStep.INIT == "init"
        assert PipelineStep.SOURCE_PROCESSING == "source_processing"
        assert PipelineStep.COMPLETED == "completed"

    def test_step_status_values(self) -> None:
        """Test all StepStatus enum values."""
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.WAITING_CONFIRMATION == "waiting_confirmation"

    def test_canvas_format_values(self) -> None:
        """Test all CanvasFormat enum values."""
        assert CanvasFormat.PPT169 == "ppt169"
        assert CanvasFormat.PPT43 == "ppt43"
        assert CanvasFormat.XHS == "xhs"
        assert CanvasFormat.STORY == "story"

    def test_file_type_values(self) -> None:
        """Test all FileType enum values."""
        assert FileType.PDF == "pdf"
        assert FileType.DOCX == "docx"
        assert FileType.URL == "url"
        assert FileType.MD == "md"

    def test_llm_provider_values(self) -> None:
        """Test LLMProvider enum values."""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"


# ---------------------------------------------------------------------------
# ColorScheme & TypographySpec Tests
# ---------------------------------------------------------------------------


class TestColorSchemeSchema:
    """Tests for ColorScheme schema."""

    def test_empty_color_scheme(self) -> None:
        """Test ColorScheme with no fields."""
        cs = ColorScheme()
        assert cs.primary is None
        assert cs.secondary is None

    def test_full_color_scheme(self) -> None:
        """Test ColorScheme with all fields."""
        cs = ColorScheme(
            primary="#000000",
            secondary="#ffffff",
            accent="#ff0000",
            background="#f0f0f0",
            text="#333333",
        )
        assert cs.primary == "#000000"
        assert cs.accent == "#ff0000"


class TestTypographySpecSchema:
    """Tests for TypographySpec schema."""

    def test_typography_spec(self) -> None:
        """Test TypographySpec creation."""
        ts = TypographySpec(title_font="Arial", body_font="Helvetica", title_size="24pt")
        assert ts.title_font == "Arial"
        assert ts.body_size is None
