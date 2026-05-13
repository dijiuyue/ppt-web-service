"""
PPT Master Web Service - Pipeline API Routes.

Pipeline status, job history, and resume operations.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    PaginationParams,
    get_current_project,
    get_db,
    get_db_ro,
    get_storage,
)
from app.core.schemas import (
    ErrorResponse,
    JobListResponse,
    PipelineResumeRequest,
    PipelineStatusResponse,
)
from app.models.project import Project
from app.services.pipeline_service import PipelineService
from app.services.project_service import ProjectService
from app.services.storage_service import StorageBackend

router = APIRouter()


def _pipeline_service(db: AsyncSession) -> PipelineService:
    return PipelineService(db=db)


# ──── Routes ────


@router.get(
    "/status",
    response_model=dict,  # Using dict for dynamic status fields
    summary="Get pipeline status",
    description="Get the current pipeline status for a project.",
    responses={
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def get_pipeline_status(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Get current pipeline status.

    Args:
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Pipeline status information.
    """
    service = _pipeline_service(db)
    return await service.get_pipeline_status(project)


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="Get job history",
    description="Get the execution history of pipeline jobs for a project.",
)
async def get_job_history(
    pagination: PaginationParams = Depends(),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Get pipeline job history.

    Args:
        pagination: Pagination parameters.
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Paginated job history.
    """
    service = _pipeline_service(db)
    jobs, total = await service.get_job_history(
        project_id=project.id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return {
        "items": jobs,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": max(pages, 1),
    }


@router.post(
    "/resume",
    summary="Resume pipeline",
    description="Resume the pipeline from the current step. Useful after failures or confirmations.",
    responses={
        200: {"description": "Pipeline resumed"},
        400: {"description": "Cannot resume pipeline", "model": ErrorResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def resume_pipeline(
    request: PipelineResumeRequest = PipelineResumeRequest(),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Resume the pipeline.

    Args:
        request: Resume options.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Resume result with job info.
    """
    project_service = ProjectService(db=db, storage=storage)
    if not await project_service.can_resume_pipeline(project):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resume pipeline: project status is '{project.status}'",
        )

    service = _pipeline_service(db)
    job = await service.resume_pipeline(project, request)

    return {
        "message": "Pipeline resumed",
        "job_id": str(job.id),
        "step": job.step,
        "status": job.status,
    }
