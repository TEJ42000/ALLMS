"""Page Rendering Routes for the LLS Study Portal."""

import logging

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.course_service import get_course_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pages"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Serve the course selection landing page."""
    return templates.TemplateResponse(
        "course_selection.html",
        {
            "request": request,
            "title": "Select Your Course - LLS Study Portal",
            "version": "2.0.0"
        }
    )


@router.get("/courses/{course_id}/study-portal", response_class=HTMLResponse)
async def course_study_portal(request: Request, course_id: str):
    """
    Serve the study portal for a specific course.

    Args:
        course_id: The unique identifier for the course
    """
    try:
        # Verify course exists
        service = get_course_service()
        course = service.get_course(course_id, include_weeks=False)

        if not course:
            raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found")

        if not course.active:
            logger.warning("Attempted to access inactive course: %s", course_id)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": f"{course.name} - Study Portal",
                "version": "2.0.0",
                "course_id": course_id,
                "course_name": course.name,
                "course": course
            }
        )
    except ValueError as e:
        logger.error("Invalid course ID: %s", course_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error loading course %s: %s", course_id, e)
        raise HTTPException(status_code=500, detail="Failed to load course")


@router.get("/legacy", response_class=HTMLResponse)
async def legacy_portal(request: Request):
    """
    Serve the legacy single-course study portal (for backward compatibility).
    This route maintains the old behavior before multi-course support.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "LLS Study Portal",
            "version": "2.0.0",
            "course_id": None,  # Legacy mode - no specific course
            "course_name": "LLS",
            "course": None
        }
    )


@router.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "service": "lls-study-portal",
        "version": "2.0.0"
    }
