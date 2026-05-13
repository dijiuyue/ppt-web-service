"""
PPT Master Web Service - Project Service.

Business logic for project CRUD, status management,
and project lifecycle operations.
"""

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.schemas import (
    CanvasFormat,
    JobStatus,
    LLMProvider,
    PipelineStep,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
    StepStatus,
)
from app.models.design_spec import DesignSpec
from app.models.project import Project
from app.models.speaker_note import SpeakerNote
from app.models.svg_page import SVGPage
from app.services.storage_service import StorageBackend


class ProjectService:
    """Service layer for project management."""

    def __init__(self, db: AsyncSession, storage: StorageBackend) -> None:
        self.db = db
        self.storage = storage

    # ── CRUD Operations ──

    async def create(self, data: ProjectCreate) -> Project:
        """Create a new project.

        Args:
            data: Project creation schema.

        Returns:
            The newly created Project instance.
        """
        project = Project(
            name=data.name,
            description=data.description,
            canvas_format=data.canvas_format.value,
            status=ProjectStatus.DRAFT.value,
            current_step=PipelineStep.INIT.value,
            step_status=StepStatus.PENDING.value,
            llm_provider=data.llm_provider.value,
            llm_model=data.llm_model,
        )
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID with all relationships loaded.

        Args:
            project_id: Project UUID.

        Returns:
            Project instance or None.
        """
        result = await self.db.execute(
            select(Project)
            .options(
                selectinload(Project.source_files),
                selectinload(Project.design_spec),
                selectinload(Project.image_resources),
                selectinload(Project.svg_pages),
                selectinload(Project.pptx_exports),
            )
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self, offset: int = 0, limit: int = 20, status_filter: Optional[ProjectStatus] = None
    ) -> tuple[List[Project], int]:
        """Get paginated project list.

        Args:
            offset: Query offset.
            limit: Query limit.
            status_filter: Optional status filter.

        Returns:
            Tuple of (projects list, total count).
        """
        query = select(Project).order_by(Project.created_at.desc())
        count_query = select(func.count(Project.id))

        if status_filter:
            query = query.where(Project.status == status_filter.value)
            count_query = count_query.where(Project.status == status_filter.value)

        result = await self.db.execute(query.offset(offset).limit(limit))
        projects = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(projects), total

    async def update(self, project: Project, data: ProjectUpdate) -> Project:
        """Update a project.

        Args:
            project: Project instance to update.
            data: Update data.

        Returns:
            Updated project instance.
        """
        update_fields = {
            "name": data.name,
            "description": data.description,
            "canvas_format": data.canvas_format.value if data.canvas_format else None,
            "llm_provider": data.llm_provider.value if data.llm_provider else None,
            "llm_model": data.llm_model,
            "template_path": data.template_path,
        }

        for field, value in update_fields.items():
            if value is not None:
                setattr(project, field, value)

        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        """Delete a project and all associated data.

        This performs a cascading delete: source files, design specs,
        SVG pages, exports, and pipeline jobs. Storage objects are
        also cleaned up.

        Args:
            project: Project instance to delete.
        """
        # Clean up storage
        await self._cleanup_storage(project.id)

        # SQLAlchemy cascade delete handles related records
        await self.db.delete(project)
        await self.db.flush()

    async def _cleanup_storage(self, project_id: UUID) -> None:
        """Remove all storage objects for a project.

        Args:
            project_id: Project UUID.
        """
        # Delete project directory from storage
        prefix = f"projects/{project_id}/"
        try:
            # Try to delete recursively (MinIO)
            if hasattr(self.storage, "_client"):
                objects = self.storage._client.list_objects(
                    self.storage.bucket, prefix=prefix, recursive=True
                )
                for obj in objects:
                    self.storage._client.remove_object(
                        self.storage.bucket, obj.object_name
                    )
        except Exception:
            # Best-effort cleanup
            pass

    # ── Status Management ──

    async def set_status(
        self, project: Project, status: ProjectStatus
    ) -> Project:
        """Set project status.

        Args:
            project: Project instance.
            status: New status.

        Returns:
            Updated project.
        """
        project.status = status.value
        await self.db.flush()
        return project

    async def set_step(
        self,
        project: Project,
        step: PipelineStep,
        step_status: Optional[StepStatus] = None,
    ) -> Project:
        """Set current pipeline step and optionally step status.

        Args:
            project: Project instance.
            step: New current step.
            step_status: Optional step status.

        Returns:
            Updated project.
        """
        project.current_step = step.value
        if step_status:
            project.step_status = step_status.value
        await self.db.flush()
        return project

    async def set_step_status(self, project: Project, step_status: StepStatus) -> Project:
        """Set only the step status.

        Args:
            project: Project instance.
            step_status: New step status.

        Returns:
            Updated project.
        """
        project.step_status = step_status.value
        await self.db.flush()
        return project

    async def complete_project(self, project: Project) -> Project:
        """Mark project as completed.

        Args:
            project: Project instance.

        Returns:
            Updated project.
        """
        from datetime import datetime, timezone

        project.status = ProjectStatus.COMPLETED.value
        project.current_step = PipelineStep.COMPLETED.value
        project.step_status = StepStatus.COMPLETED.value
        project.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return project

    async def fail_project(self, project: Project, error_message: str) -> Project:
        """Mark project as failed.

        Args:
            project: Project instance.
            error_message: Error description.

        Returns:
            Updated project.
        """
        project.status = ProjectStatus.FAILED.value
        project.step_status = StepStatus.FAILED.value
        await self.db.flush()
        return project

    # ── Pipeline Control ──

    async def can_start_pipeline(self, project: Project) -> bool:
        """Check if pipeline can be started for this project.

        Returns:
            True if pipeline can start.
        """
        return project.status in {
            ProjectStatus.DRAFT.value,
            ProjectStatus.CONFIRMING.value,
            ProjectStatus.FAILED.value,
        }

    async def can_cancel_pipeline(self, project: Project) -> bool:
        """Check if pipeline can be cancelled.

        Returns:
            True if pipeline is running and can be cancelled.
        """
        return (
            project.status == ProjectStatus.PROCESSING.value
            and project.step_status == StepStatus.RUNNING.value
        )

    async def can_resume_pipeline(self, project: Project) -> bool:
        """Check if pipeline can be resumed.

        Returns:
            True if pipeline is in a resumable state.
        """
        return project.status in {
            ProjectStatus.FAILED.value,
            ProjectStatus.CONFIRMING.value,
        }

    # ── Statistics ──

    async def get_project_stats(self, project_id: UUID) -> dict[str, Any]:
        """Get project statistics.

        Args:
            project_id: Project UUID.

        Returns:
            Dict with source count, SVG page count, export count.
        """
        from app.models.source_file import SourceFile
        from app.models.svg_page import SVGPage
        from app.models.pptx_export import PPTXExport

        source_count = await self.db.scalar(
            select(func.count(SourceFile.id)).where(
                SourceFile.project_id == project_id
            )
        )
        svg_count = await self.db.scalar(
            select(func.count(SVGPage.id)).where(
                SVGPage.project_id == project_id
            )
        )
        export_count = await self.db.scalar(
            select(func.count(PPTXExport.id)).where(
                PPTXExport.project_id == project_id
            )
        )

        return {
            "source_count": source_count or 0,
            "svg_page_count": svg_count or 0,
            "export_count": export_count or 0,
        }
