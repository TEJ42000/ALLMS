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
from app.services.auth_service import get_auth_config

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
    auth_config = get_auth_config()
    return templates.TemplateResponse(
        "admin/courses.html",
        {
            "request": request,
            "title": "Course Management",
            "version": "2.0.0",
            "user": user,
            "auth_enabled": auth_config.auth_enabled
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
    auth_config = get_auth_config()
    return templates.TemplateResponse(
        "admin/courses.html",
        {
            "request": request,
            "title": "Course Management",
            "version": "2.0.0",
            "user": user,
            "auth_enabled": auth_config.auth_enabled
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
    auth_config = get_auth_config()
    return templates.TemplateResponse(
        "admin/courses.html",
        {
            "request": request,
            "title": f"Edit Course: {course_id}",
            "course_id": course_id,
            "version": "2.0.0",
            "user": user,
            "auth_enabled": auth_config.auth_enabled
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
    auth_config = get_auth_config()
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "title": "User Management",
            "version": "2.0.0",
            "user": user,
            "auth_enabled": auth_config.auth_enabled
        }
    )


@router.get("/usage", response_class=HTMLResponse)
async def admin_usage_dashboard(
    request: Request,
    user: User = Depends(require_mgms_domain)
):
    """
    LLM Usage Analytics Dashboard.

    Requires @mgms.eu domain authentication.

    Provides:
    - KPI summary cards (total requests, cost, users)
    - Cost over time chart with granularity options
    - Usage breakdown by operation type
    - Top users by cost
    - Filterable data grid with export
    """
    auth_config = get_auth_config()
    return templates.TemplateResponse(
        "admin/usage_dashboard.html",
        {
            "request": request,
            "title": "Usage Analytics",
            "version": "2.0.0",
            "user": user,
            "auth_enabled": auth_config.auth_enabled
        }
    )
