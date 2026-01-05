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


def get_user_from_request(request: Request):
    """Extract user from request state (set by auth middleware)."""
    return getattr(request.state, 'user', None)


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Serve the course selection landing page."""
    user = get_user_from_request(request)
    return templates.TemplateResponse(
        "course_selection.html",
        {
            "request": request,
            "title": "Select Your Course - LLS Study Portal",
            "version": "2.0.0",
            "user": user
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

        user = get_user_from_request(request)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": f"{course.name} - Study Portal",
                "version": "2.0.0",
                "course_id": course_id,
                "course_name": course.name,
                "course": course,
                "user": user
            }
        )
    except ValueError as e:
        logger.error("Invalid course ID: %s", course_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error loading course %s: %s", course_id, e)
        raise HTTPException(status_code=500, detail="Failed to load course")


@router.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "service": "lls-study-portal",
        "version": "2.0.0"
    }
