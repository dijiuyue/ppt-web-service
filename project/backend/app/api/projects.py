"""
PPT Master Web Service - Project API Routes.

CRUD operations for projects, plus pipeline start/cancel actions.
"""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    PaginationParams,
    get_current_project,
    get_db,
    get_db_ro,
    get_storage,
    optional_api_key,
)
from app.core.schemas import (
    ErrorResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectStartRequest,
    ProjectStatus,
    ProjectUpdate,
)
from app.models.project import Project
from app.services.project_service import ProjectService
from app.services.storage_service import StorageBackend

router = APIRouter()


# ──── Helper: Build service ────


def _project_service(db: AsyncSession, storage: StorageBackend) -> ProjectService:
    return ProjectService(db=db, storage=storage)


# ──── Routes ────


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new PPT generation project with the given configuration.",
    responses={
        201: {"description": "Project created successfully"},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> Project:
    """Create a new project.

    Args:
        data: Project creation parameters.
        db: Database session.
        storage: Storage backend.

    Returns:
        The created project.
    """
    service = _project_service(db, storage)
    return await service.create(data)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List projects",
    description="Get a paginated list of all projects, optionally filtered by status.",
)
async def list_projects(
    status_filter: Optional[ProjectStatus] = Query(
        default=None, description="Filter by project status"
    ),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """List projects with pagination.

    Args:
        status_filter: Optional status filter.
        pagination: Pagination parameters.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Paginated project list.
    """
    service = _project_service(db, storage)
    projects, total = await service.get_list(
        offset=pagination.offset,
        limit=pagination.page_size,
        status_filter=status_filter,
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return {
        "items": projects,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": max(pages, 1),
    }


@router.get(
    "/{id}",
    response_model=ProjectResponse,
    summary="Get project details",
    description="Get detailed information about a specific project.",
    responses={
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def get_project(
    project: Project = Depends(get_current_project),
) -> Project:
    """Get project by ID.

    Args:
        project: Resolved project dependency.

    Returns:
        Project details.
    """
    return project


@router.put(
    "/{id}",
    response_model=ProjectResponse,
    summary="Update project",
    description="Update project metadata. Only provided fields are changed.",
    responses={
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def update_project(
    data: ProjectUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> Project:
    """Update a project.

    Args:
        data: Update data (only provided fields are changed).
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Updated project.
    """
    service = _project_service(db, storage)
    return await service.update(project, data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete a project and all associated data (cascading).",
    responses={
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def delete_project(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> None:
    """Delete a project.

    Args:
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.
    """
    service = _project_service(db, storage)
    await service.delete(project)


# ──── Pipeline Actions ────


@router.post(
    "/{id}/start",
    summary="Start pipeline",
    description="Start the PPT generation pipeline for this project.",
    responses={
        200: {"description": "Pipeline started"},
        400: {"description": "Pipeline cannot be started", "model": ErrorResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def start_pipeline(
    request: ProjectStartRequest,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Start the pipeline.

    Args:
        request: Start options.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Job info dict.
    """
    from app.services.pipeline_service import PipelineService

    service = _project_service(db, storage)
    if not await service.can_start_pipeline(project):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start pipeline: project status is '{project.status}'",
        )

    pipeline = PipelineService(db)
    job = await pipeline.start_pipeline(
        project, start_from_step=request.start_from_step
    )
    return {
        "message": "Pipeline started",
        "job_id": str(job.id),
        "step": job.step,
        "status": job.status,
    }


@router.post(
    "/{id}/cancel",
    summary="Cancel pipeline",
    description="Cancel the currently running pipeline.",
    responses={
        200: {"description": "Pipeline cancelled"},
        400: {"description": "Pipeline not running", "model": ErrorResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def cancel_pipeline(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, str]:
    """Cancel the pipeline.

    Args:
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Status message.
    """
    from app.services.pipeline_service import PipelineService

    service = _project_service(db, storage)
    if not await service.can_cancel_pipeline(project):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline is not currently running",
        )

    pipeline = PipelineService(db)
    await pipeline.cancel_pipeline(project)
    return {"message": "Pipeline cancelled"}
