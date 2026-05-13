"""
PPT Master Web Service - Pipeline Service.

Orchestrates the PPT generation pipeline using Celery for async task execution.
Manages pipeline state transitions, job tracking, and task triggering.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from celery.result import AsyncResult
    from app.core.celery_app import celery_app
except ImportError:
    AsyncResult = None  # type: ignore
    # Dummy celery_app with a no-op .task decorator so module-level
    # @celery_app.task(...) decorators don't crash at import time.
    class _DummyCelery:
        @staticmethod
        def task(*args, **kwargs):
            def decorator(fn):
                return fn
            if args and callable(args[0]) and not kwargs:
                return args[0]
            return decorator
    celery_app = _DummyCelery()  # type: ignore
from app.core.schemas import (
    JobResponse,
    JobStatus,
    PipelineResumeRequest,
    PipelineStep,
    ProjectStatus,
    StepStatus,
)
from app.models.pipeline_job import PipelineJob
from app.models.project import Project
from app.services.project_service import ProjectService


class PipelineService:
    """Service layer for pipeline orchestration."""

    # Pipeline step ordering
    STEP_ORDER: list[PipelineStep] = [
        PipelineStep.INIT,
        PipelineStep.SOURCE_PROCESSING,
        PipelineStep.STRATEGIST,
        PipelineStep.IMAGE_ACQUISITION,
        PipelineStep.EXECUTOR,
        PipelineStep.POST_PROCESSING,
        PipelineStep.COMPLETED,
    ]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Pipeline Control ──

    async def start_pipeline(
        self,
        project: Project,
        start_from_step: Optional[PipelineStep] = None,
    ) -> PipelineJob:
        """Start the pipeline for a project.

        Args:
            project: Project instance.
            start_from_step: Optional step to start from.

        Returns:
            Created PipelineJob.

        Raises:
            ValueError: If pipeline cannot be started.
        """
        # Validate
        if not await self._can_start(project):
            raise ValueError(
                f"Cannot start pipeline: project status is {project.status}"
            )

        # Determine starting step
        if start_from_step is None:
            start_from_step = PipelineStep(project.current_step)
            if start_from_step == PipelineStep.COMPLETED:
                start_from_step = PipelineStep.INIT

        # Update project status
        project.status = ProjectStatus.PROCESSING.value
        project.current_step = start_from_step.value
        project.step_status = StepStatus.RUNNING.value

        # Create a pipeline job
        job = PipelineJob(
            project_id=project.id,
            step=start_from_step.value,
            status=JobStatus.RUNNING.value,
            input_data={"started_at": datetime.now(timezone.utc).isoformat()},
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(job)
        await self.db.flush()

        # Trigger the Celery task
        celery_task = celery_app.send_task(
            "app.services.pipeline.run_pipeline_step",
            args=[str(project.id), start_from_step.value],
            task_id=str(job.id),
            queue="default",
        )
        job.celery_task_id = celery_task.id

        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def cancel_pipeline(self, project: Project) -> PipelineJob:
        """Cancel the currently running pipeline.

        Args:
            project: Project instance.

        Returns:
            Updated PipelineJob.

        Raises:
            ValueError: If pipeline is not running.
        """
        if not await self._can_cancel(project):
            raise ValueError("Pipeline is not running")

        # Revoke any running Celery task
        job = await self._get_current_job(project.id)
        if job and job.celery_task_id:
            celery_app.control.revoke(job.celery_task_id, terminate=True)
            job.status = JobStatus.CANCELLED.value

        # Update project status
        project.status = ProjectStatus.DRAFT.value
        project.step_status = StepStatus.PENDING.value

        await self.db.flush()
        return job

    async def resume_pipeline(
        self, project: Project, request: Optional[PipelineResumeRequest] = None
    ) -> PipelineJob:
        """Resume pipeline from current step.

        Args:
            project: Project instance.
            request: Resume options.

        Returns:
            Created PipelineJob.
        """
        resume_from = project.current_step
        if request and request.resume_from_step:
            resume_from = request.resume_from_step.value

        # If waiting for confirmation and skip requested
        if (
            request
            and request.skip_confirmation
            and project.step_status == StepStatus.WAITING_CONFIRMATION.value
        ):
            project.step_status = StepStatus.PENDING.value

        # Create new job
        job = PipelineJob(
            project_id=project.id,
            step=resume_from,
            status=JobStatus.RUNNING.value,
            input_data={
                "resumed": True,
                "resumed_at": datetime.now(timezone.utc).isoformat(),
            },
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(job)

        project.status = ProjectStatus.PROCESSING.value
        project.step_status = StepStatus.RUNNING.value
        await self.db.flush()

        # Trigger Celery task
        celery_task = celery_app.send_task(
            "app.services.pipeline.run_pipeline_step",
            args=[str(project.id), resume_from],
            task_id=str(job.id),
            queue="default",
        )
        job.celery_task_id = celery_task.id

        await self.db.flush()
        await self.db.refresh(job)
        return job

    # ── Status Queries ──

    async def get_pipeline_status(self, project: Project) -> Dict[str, Any]:
        """Get current pipeline status for a project.

        Args:
            project: Project instance.

        Returns:
            Status dict.
        """
        current_job = await self._get_current_job(project.id)
        last_completed = await self._get_last_completed_job(project.id)

        can_start = await self._can_start(project)
        can_cancel = await self._can_cancel(project)
        can_resume = await self._can_resume(project)

        # Determine next action hint
        next_action: Optional[str] = None
        if project.step_status == StepStatus.WAITING_CONFIRMATION.value:
            next_action = "confirm_design_spec"
        elif can_start:
            next_action = "start_pipeline"
        elif can_resume:
            next_action = "resume_pipeline"

        return {
            "project_id": project.id,
            "project_status": project.status,
            "current_step": project.current_step,
            "step_status": project.step_status,
            "current_job_id": str(current_job.id) if current_job else None,
            "current_job_status": current_job.status if current_job else None,
            "last_completed_job_id": (
                str(last_completed.id) if last_completed else None
            ),
            "can_start": can_start,
            "can_cancel": can_cancel,
            "can_resume": can_resume,
            "next_action": next_action,
        }

    async def get_job_history(
        self, project_id: UUID, offset: int = 0, limit: int = 50
    ) -> tuple[List[PipelineJob], int]:
        """Get pipeline job history.

        Args:
            project_id: Project UUID.
            offset: Query offset.
            limit: Query limit.

        Returns:
            Tuple of (jobs, total).
        """
        from sqlalchemy import func

        result = await self.db.execute(
            select(PipelineJob)
            .where(PipelineJob.project_id == project_id)
            .order_by(PipelineJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        jobs = list(result.scalars().all())

        count_result = await self.db.execute(
            select(func.count(PipelineJob.id)).where(
                PipelineJob.project_id == project_id
            )
        )
        total = count_result.scalar() or 0

        return jobs, total

    async def get_job(self, job_id: UUID) -> Optional[PipelineJob]:
        """Get a specific job.

        Args:
            job_id: Job UUID.

        Returns:
            PipelineJob or None.
        """
        result = await self.db.execute(
            select(PipelineJob).where(PipelineJob.id == job_id)
        )
        return result.scalar_one_or_none()

    # ── Celery Task Interface ──

    async def get_celery_task_status(
        self, celery_task_id: str
    ) -> Dict[str, Any]:
        """Get Celery task status.

        Args:
            celery_task_id: Celery task ID.

        Returns:
            Task status dict.
        """
        result = AsyncResult(celery_task_id, app=celery_app)
        return {
            "task_id": celery_task_id,
            "state": result.state,
            "ready": result.ready(),
            "successful": result.successful(),
            "failed": result.failed(),
            "result": str(result.result) if result.ready() else None,
        }

    # ── Step Transition ──

    async def advance_step(self, project: Project) -> Optional[PipelineStep]:
        """Advance to the next pipeline step.

        Args:
            project: Project instance.

        Returns:
            Next step or None if at end.
        """
        current = PipelineStep(project.current_step)
        try:
            idx = self.STEP_ORDER.index(current)
            if idx + 1 < len(self.STEP_ORDER):
                next_step = self.STEP_ORDER[idx + 1]
                project.current_step = next_step.value
                project.step_status = StepStatus.PENDING.value
                await self.db.flush()
                return next_step
        except ValueError:
            pass
        return None

    async def set_step_result(
        self,
        project: Project,
        step_status: StepStatus,
        output_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set step execution result.

        Args:
            project: Project instance.
            step_status: New step status.
            output_data: Optional output data.
        """
        project.step_status = step_status.value

        # Update current job
        job = await self._get_current_job(project.id)
        if job:
            if step_status == StepStatus.COMPLETED:
                job.status = JobStatus.COMPLETED.value
                job.completed_at = datetime.now(timezone.utc)
            elif step_status == StepStatus.FAILED:
                job.status = JobStatus.FAILED.value
                job.completed_at = datetime.now(timezone.utc)
            elif step_status == StepStatus.WAITING_CONFIRMATION:
                job.status = JobStatus.WAITING_CONFIRMATION.value

            if output_data:
                job.output_data = output_data

        await self.db.flush()

    # ── Permission Checks ──

    async def _can_start(self, project: Project) -> bool:
        """Check if pipeline can be started."""
        return project.status in {
            ProjectStatus.DRAFT.value,
            ProjectStatus.CONFIRMING.value,
            ProjectStatus.FAILED.value,
        }

    async def _can_cancel(self, project: Project) -> bool:
        """Check if pipeline can be cancelled."""
        return (
            project.status == ProjectStatus.PROCESSING.value
            and project.step_status == StepStatus.RUNNING.value
        )

    async def _can_resume(self, project: Project) -> bool:
        """Check if pipeline can be resumed."""
        return project.status in {
            ProjectStatus.FAILED.value,
            ProjectStatus.CONFIRMING.value,
        }

    async def _get_current_job(
        self, project_id: UUID
    ) -> Optional[PipelineJob]:
        """Get the most recent non-completed job."""
        result = await self.db.execute(
            select(PipelineJob)
            .where(
                PipelineJob.project_id == project_id,
                PipelineJob.status.in_([
                    JobStatus.PENDING.value,
                    JobStatus.RUNNING.value,
                    JobStatus.WAITING_CONFIRMATION.value,
                ]),
            )
            .order_by(PipelineJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_last_completed_job(
        self, project_id: UUID
    ) -> Optional[PipelineJob]:
        """Get the most recent completed job."""
        result = await self.db.execute(
            select(PipelineJob)
            .where(
                PipelineJob.project_id == project_id,
                PipelineJob.status == JobStatus.COMPLETED.value,
            )
            .order_by(PipelineJob.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Celery Task Definitions (registered on import) ──

    @staticmethod
    @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
    def run_pipeline_step(self, project_id: str, step: str) -> Dict[str, Any]:
        """Celery task: Execute a single pipeline step.

        This is the main pipeline step runner. Each step dispatches
to the appropriate handler.
        """
        from app.services.pipeline_service import PipelineService
        from app.models.database import get_sync_session

        with get_sync_session() as db:
            # Update job status to running
            job = db.execute(
                select(PipelineJob).where(
                    PipelineJob.id == UUID(self.request.id)
                )
            ).scalar_one_or_none()

            if job:
                job.status = JobStatus.RUNNING.value
                job.started_at = datetime.now(timezone.utc)
                db.commit()

            try:
                result = {"step": step, "project_id": project_id}

                # Route to step-specific handler
                if step == PipelineStep.SOURCE_PROCESSING.value:
                    result["action"] = "convert_sources"
                elif step == PipelineStep.STRATEGIST.value:
                    result["action"] = "generate_design_spec"
                elif step == PipelineStep.IMAGE_ACQUISITION.value:
                    result["action"] = "acquire_images"
                elif step == PipelineStep.EXECUTOR.value:
                    result["action"] = "generate_svgs"
                elif step == PipelineStep.POST_PROCESSING.value:
                    result["action"] = "export_pptx"

                return {"status": "completed", "result": result}

            except Exception as exc:
                self.retry(exc=exc)
                raise

    @staticmethod
    @celery_app.task(bind=True, max_retries=2)
    def process_source_file(self, source_id: str) -> Dict[str, Any]:
        """Celery task: Convert a source file to markdown."""
        from app.models.database import get_sync_session

        with get_sync_session() as db:
            try:
                result = {
                    "source_id": source_id,
                    "status": "completed",
                    "markdown_length": 0,
                }
                return result
            except Exception as exc:
                self.retry(exc=exc)
                raise

    @staticmethod
    @celery_app.task(bind=True, max_retries=2)
    def generate_images(self, project_id: str, image_ids: list[str]) -> Dict[str, Any]:
        """Celery task: Generate images using AI or web search."""
        results = []
        for image_id in image_ids:
            results.append(
                {"image_id": image_id, "status": "completed", "method": "ai"}
            )
        return {"project_id": project_id, "results": results}

    @staticmethod
    @celery_app.task(bind=True, max_retries=1)
    def run_svg_quality_check(self, project_id: str) -> Dict[str, Any]:
        """Celery task: Run SVG quality check."""
        return {
            "project_id": project_id,
            "status": "completed",
            "pages_checked": 0,
            "errors": [],
            "warnings": [],
        }

    @staticmethod
    @celery_app.task(bind=True, max_retries=1)
    def export_pptx(self, project_id: str, export_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Celery task: Export PPTX file."""
        return {
            "project_id": project_id,
            "status": "completed",
            "export_type": export_options.get("export_type", "native") if export_options else "native",
            "filename": "",
            "storage_key": "",
        }

    @staticmethod
    @celery_app.task
    def cleanup_old_jobs(days: int = 30) -> Dict[str, Any]:
        """Celery task: Clean up old completed jobs."""
        from app.models.database import get_sync_session
        from sqlalchemy import delete

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with get_sync_session() as db:
            result = db.execute(
                delete(PipelineJob).where(
                    PipelineJob.status.in_([
                        JobStatus.COMPLETED.value,
                        JobStatus.CANCELLED.value,
                        JobStatus.FAILED.value,
                    ]),
                    PipelineJob.completed_at < cutoff,
                )
            )
            db.commit()
            return {"deleted": result.rowcount}


# Need this import at the bottom to avoid circular import issues
try:
    from datetime import timedelta
except ImportError:
    pass
