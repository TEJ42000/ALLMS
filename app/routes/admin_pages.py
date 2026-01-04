"""Admin Page Routes for Course Management.

Serves HTML pages for the admin interface.
Note: Authentication is planned for Phase 5.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Pages"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """
    Admin dashboard - redirects to courses page.
    """
    return templates.TemplateResponse(
        "admin/courses.html",
        {
            "request": request,
            "title": "Course Management",
            "version": "2.0.0"
        }
    )


@router.get("/courses", response_class=HTMLResponse)
async def admin_courses(request: Request):
    """
    Course management page.
    
    Shows list of courses with ability to:
    - View course details
    - Edit course metadata
    - Manage weeks and materials
    """
    return templates.TemplateResponse(
        "admin/courses.html",
        {
            "request": request,
            "title": "Course Management",
            "version": "2.0.0"
        }
    )


@router.get("/courses/{course_id}", response_class=HTMLResponse)
async def admin_course_detail(request: Request, course_id: str):
    """
    Course detail/edit page.
    
    Shows course details with ability to:
    - Edit course metadata
    - Manage weeks
    - Link materials
    """
    return templates.TemplateResponse(
        "admin/courses.html",
        {
            "request": request,
            "title": f"Edit Course: {course_id}",
            "course_id": course_id,
            "version": "2.0.0"
        }
    )

