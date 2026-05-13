"""
PPT Master Web Service - SVG Pages API Routes.

Handles SVG page listing, content retrieval (JSON and raw SVG),
and SVG content updates.
"""

from typing import Any, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
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
    SVGPageListResponse,
    SVGPageResponse,
    SVGPageUpdate,
)
from app.models.project import Project
from app.models.svg_page import SVGPage
from app.services.storage_service import StorageBackend

router = APIRouter()


# ──── Routes ────


@router.get(
    "",
    response_model=SVGPageListResponse,
    summary="List SVG pages",
    description="Get all SVG pages for a project, ordered by page number.",
)
async def list_svg_pages(
    pagination: PaginationParams = Depends(),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """List SVG pages for a project.

    Args:
        pagination: Pagination parameters.
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Paginated SVG page list.
    """
    result = await db.execute(
        select(SVGPage)
        .where(SVGPage.project_id == project.id)
        .order_by(SVGPage.page_number)
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    pages = list(result.scalars().all())

    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count(SVGPage.id)).where(SVGPage.project_id == project.id)
    )
    total = count_result.scalar() or 0
    num_pages = (total + pagination.page_size - 1) // pagination.page_size

    return {
        "items": pages,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": max(num_pages, 1),
    }


@router.get(
    "/{pid}",
    response_model=SVGPageResponse,
    summary="Get SVG page",
    description="Get a single SVG page with its metadata and content.",
    responses={
        404: {"description": "SVG page not found", "model": ErrorResponse},
    },
)
async def get_svg_page(
    pid: UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> Any:
    """Get SVG page by ID.

    Args:
        pid: SVG page ID.
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        SVG page data.

    Raises:
        HTTPException: If SVG page not found.
    """
    result = await db.execute(
        select(SVGPage).where(
            SVGPage.id == pid, SVGPage.project_id == project.id
        )
    )
    page = result.scalar_one_or_none()
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SVG page '{pid}' not found",
        )

    # Load SVG content from storage if needed
    if not page.svg_content and page.svg_storage_key:
        try:
            data = await storage.get(page.svg_storage_key)
            page.svg_content = data.decode("utf-8")
        except Exception:
            pass

    return page


@router.get(
    "/{pid}/svg",
    response_class=PlainTextResponse,
    summary="Get raw SVG content",
    description="Get the raw SVG XML content for a page. Returns SVG as text/plain.",
    responses={
        200: {
            "content": {"text/plain": {}},
            "description": "Raw SVG XML content",
        },
        404: {"description": "SVG page not found", "model": ErrorResponse},
    },
)
async def get_svg_raw(
    pid: UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> str:
    """Get raw SVG content.

    Args:
        pid: SVG page ID.
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Raw SVG XML string.

    Raises:
        HTTPException: If SVG page not found or content unavailable.
    """
    result = await db.execute(
        select(SVGPage).where(
            SVGPage.id == pid, SVGPage.project_id == project.id
        )
    )
    page = result.scalar_one_or_none()
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SVG page '{pid}' not found",
        )

    # Return SVG content
    if page.svg_content:
        return page.svg_content

    if page.svg_storage_key:
        try:
            data = await storage.get(page.svg_storage_key)
            return data.decode("utf-8")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load SVG content: {exc}",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="SVG content not available for this page",
    )


@router.put(
    "/{pid}",
    response_model=SVGPageResponse,
    summary="Update SVG page",
    description="Update SVG page content and/or metadata. Full content replacement.",
    responses={
        404: {"description": "SVG page not found", "model": ErrorResponse},
    },
)
async def update_svg_page(
    pid: UUID,
    data: SVGPageUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> Any:
    """Update SVG page.

    Args:
        pid: SVG page ID.
        data: Update data.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Updated SVG page.

    Raises:
        HTTPException: If SVG page not found.
    """
    result = await db.execute(
        select(SVGPage).where(
            SVGPage.id == pid, SVGPage.project_id == project.id
        )
    )
    page = result.scalar_one_or_none()
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SVG page '{pid}' not found",
        )

    # Update SVG content
    if data.svg_content:
        page.svg_content = data.svg_content
        # Store to storage
        storage_key = storage.svg_page_path(
            project.id, page.page_number, page.page_name or "page"
        )
        await storage.put(storage_key, data.svg_content, "image/svg+xml")
        page.svg_storage_key = storage_key

    # Update metadata
    if data.page_name is not None:
        page.page_name = data.page_name
    if data.page_rhythm is not None:
        page.page_rhythm = data.page_rhythm
    if data.page_layout is not None:
        page.page_layout = data.page_layout
    if data.page_chart is not None:
        page.page_chart = data.page_chart

    await db.flush()
    await db.refresh(page)
    return page
