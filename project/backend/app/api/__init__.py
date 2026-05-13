"""
PPT Master Web Service - API Router Registration.

Registers all API routers under /api prefix.
"""

from fastapi import APIRouter

from app.api import projects, sources, design_spec, pipeline, svg_pages, exports, images, websocket

api_router = APIRouter(prefix="/api")

api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(sources.router, prefix="/projects/{id}/sources", tags=["sources"])
api_router.include_router(design_spec.router, prefix="/projects/{id}/design-spec", tags=["design-spec"])
api_router.include_router(pipeline.router, prefix="/projects/{id}/pipeline", tags=["pipeline"])
api_router.include_router(svg_pages.router, prefix="/projects/{id}/pages", tags=["svg-pages"])
api_router.include_router(exports.router, prefix="/projects/{id}/exports", tags=["exports"])
api_router.include_router(images.router, prefix="/projects/{id}/images", tags=["images"])

__all__ = ["api_router"]
