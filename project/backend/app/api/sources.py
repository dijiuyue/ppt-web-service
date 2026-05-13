"""
PPT Master Web Service - Source File API Routes.

Handles source file uploads (multi-file), URL sources, listing, and deletion.
"""

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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
    SourceFileListResponse,
    SourceFileResponse,
    SourceFileUpload,
    SourceUrlAdd,
)
from app.models.project import Project
from app.services.source_service import SourceService
from app.services.storage_service import StorageBackend

router = APIRouter()


def _source_service(db: AsyncSession, storage: StorageBackend) -> SourceService:
    return SourceService(db=db, storage=storage)


# ──── Routes ────


@router.post(
    "/upload",
    response_model=List[SourceFileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload source files",
    description="Upload one or more source files (PDF, DOCX, XLSX, PPTX, MD, TXT, etc.)",
    responses={
        201: {"description": "Files uploaded successfully"},
        400: {"description": "Invalid file type", "model": ErrorResponse},
        413: {"description": "File too large", "model": ErrorResponse},
    },
)
async def upload_sources(
    files: List[UploadFile] = File(
        ..., description="Source files to upload", max_length=100
    ),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> List[Any]:
    """Upload multiple source files.

    Args:
        files: List of uploaded files.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        List of created source file records.
    """
    service = _source_service(db, storage)

    file_data: list[tuple[str, bytes, Optional[str]]] = []
    for upload in files:
        content = await upload.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{upload.filename}' is empty",
            )
        # 50MB limit per file
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{upload.filename}' exceeds 50MB limit",
            )
        content_type = upload.content_type
        file_data.append((upload.filename or "unnamed", content, content_type))

    return await service.upload_multiple(project, file_data)


@router.post(
    "/url",
    response_model=SourceFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add URL source",
    description="Add a URL as a source (will be fetched and converted).",
)
async def add_url_source(
    data: SourceUrlAdd,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> Any:
    """Add a URL source.

    Args:
        data: URL source data.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Created source file record.
    """
    service = _source_service(db, storage)
    return await service.add_url_source(project, data)


@router.get(
    "",
    response_model=SourceFileListResponse,
    summary="List source files",
    description="Get all source files for a project.",
)
async def list_sources(
    pagination: PaginationParams = Depends(),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """List source files for a project.

    Args:
        pagination: Pagination parameters.
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Paginated source file list.
    """
    service = _source_service(db, storage)
    files, total = await service.get_list(
        project_id=project.id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return {
        "items": files,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": max(pages, 1),
    }


@router.delete(
    "/{sid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete source file",
    description="Delete a source file and its stored data.",
    responses={
        404: {"description": "Source file not found", "model": ErrorResponse},
    },
)
async def delete_source(
    sid: UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> None:
    """Delete a source file.

    Args:
        sid: Source file ID.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Raises:
        HTTPException: If source file not found.
    """
    service = _source_service(db, storage)
    source_file = await service.get_by_id(sid)
    if source_file is None or source_file.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source file '{sid}' not found",
        )
    await service.delete(source_file)
