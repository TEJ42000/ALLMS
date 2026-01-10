"""Public API Routes for Course Access.

Provides read-only course endpoints for authenticated users (any domain).
Unlike admin_courses.py, these endpoints don't require @mgms.eu domain.

This enables non-admin users (e.g., @gmail.com) to view the course catalog
and course details after OAuth login.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies.auth import require_authenticated
from app.models.auth_models import User
from app.models.course_models import Course, CourseSummary
from app.services.course_service import (
    get_course_service,
    ServiceValidationError,
    FirestoreOperationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/courses",
    tags=["Courses"],
    responses={
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"},
    }
)

# Pagination defaults
DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 100


class PaginatedCoursesResponse(BaseModel):
    """Paginated response for course listings."""
    items: List[CourseSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


@router.get("", response_model=PaginatedCoursesResponse)
async def list_courses(
    user: User = Depends(require_authenticated),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT, description="Maximum courses to return"),
    offset: int = Query(0, ge=0, description="Number of courses to skip")
):
    """
    List available courses for authenticated users.

    Returns active courses only. Any authenticated user can access this endpoint.

    **Parameters:**
    - `limit`: Maximum number of courses to return (1-100, default: 50)
    - `offset`: Number of courses to skip for pagination (default: 0)
    """
    try:
        service = get_course_service()
        # Only return active courses for regular users
        courses, total = service.get_all_courses(
            include_inactive=False,
            limit=limit,
            offset=offset
        )
        logger.info("User %s listed %d courses (total: %d)", user.email, len(courses), total)
        return PaginatedCoursesResponse(
            items=courses,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(courses)) < total
        )
    except ServiceValidationError as e:
        logger.warning("Invalid pagination parameters: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FirestoreOperationError as e:
        logger.error("Firestore error listing courses: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again."
        )


@router.get("/{course_id}", response_model=Course)
async def get_course(
    course_id: str,
    user: User = Depends(require_authenticated),
    include_weeks: bool = Query(True, description="Include weeks and legal skills")
):
    """
    Get a course by ID for authenticated users.

    Returns course details including weeks and legal skills.
    Only active courses are accessible to non-admin users.

    **Parameters:**
    - `course_id`: The unique course identifier (e.g., "LLS-2025-2026")
    - `include_weeks`: Whether to include weeks and legal skills (default: true)
    """
    try:
        service = get_course_service()
        course = service.get_course(course_id, include_weeks=include_weeks)

        if course is None:
            logger.warning("Course not found: %s (user: %s)", course_id, user.email)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        # Non-admin users can only access active courses
        if not course.active:
            logger.warning("User %s attempted to access inactive course: %s", user.email, course_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        logger.info("User %s retrieved course: %s", user.email, course_id)
        return course
    except (ServiceValidationError, ValueError) as e:
        logger.warning("Invalid course ID: %s - %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FirestoreOperationError as e:
        logger.error("Firestore error getting course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again."
        )
    except HTTPException:
        # Re-raise HTTPExceptions (raised above for 404 cases) without catching them
        raise
    except Exception as e:
        logger.error("Error getting course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get course details."
        )
