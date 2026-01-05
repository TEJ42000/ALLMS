"""Admin Page Routes for Course Management.

Serves HTML pages for the admin interface.
Requires @mgms.eu domain authentication.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies.auth import require_mgms_domain
from app.models.auth_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Pages"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: User = Depends(require_mgms_domain)
):
    """
    Admin dashboard - redirects to courses page.

    Requires @mgms.eu domain authentication.
    """
    return templates.TemplateResponse(
        "admin/courses.html",
        {
            "request": request,
            "title": "Course Management",
            "version": "2.0.0",
            "user": user
        }
    )


@router.get("/courses", response_class=HTMLResponse)
async def admin_courses(
    request: Request,
    user: User = Depends(require_mgms_domain)
):
    """
    Course management page.

    Requires @mgms.eu domain authentication.

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
            "version": "2.0.0",
            "user": user
        }
    )


@router.get("/courses/{course_id}", response_class=HTMLResponse)
async def admin_course_detail(
    request: Request,
    course_id: str,
    user: User = Depends(require_mgms_domain)
):
    """
    Course detail/edit page.

    Requires @mgms.eu domain authentication.

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
            "version": "2.0.0",
            "user": user
        }
    )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    user: User = Depends(require_mgms_domain)
):
    """
    User allow list management page.

    Requires @mgms.eu domain authentication.

    Allows admins to:
    - View all allowed external users
    - Add new users to the allow list
    - Edit or remove existing users
    """
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "title": "User Management",
            "version": "2.0.0",
            "user": user
        }
    )
