"""Public API Routes for Course Access.

Provides read-only course endpoints for authenticated users (any domain).
Unlike admin_courses.py, these endpoints don't require @mgms.eu domain.

This enables non-admin users (e.g., @gmail.com) to view the course catalog
and course details after OAuth login.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from app.dependencies.auth import require_authenticated
from app.models.auth_models import User
from app.models.course_models import Course, CourseSummary
from app.services.course_service import (
    get_course_service,
    ServiceValidationError,
    FirestoreOperationError,
)
from app.services.course_materials_service import get_course_materials_service

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
    course_id: str = Path(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Course identifier (alphanumeric with hyphens/underscores)"
    ),
    user: User = Depends(require_authenticated),
    include_weeks: bool = Query(True, description="Include weeks and legal skills")
):
    """
    Get a course by ID for authenticated users.

    Returns course details including weeks and legal skills.

    **Security**: Only active courses are accessible to non-admin users.
    Inactive courses return 404 (not 403) to avoid leaking course existence.

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
                detail="Course not found"
            )

        # Non-admin users can only access active courses
        if not course.active:
            logger.warning("User %s attempted to access inactive course: %s", user.email, course_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
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


class WeekMaterialCount(BaseModel):
    """Material count for a single week."""
    week: int
    count: int


class MaterialCountsByWeekResponse(BaseModel):
    """Response for material counts by week."""
    course_id: str
    weeks: List[WeekMaterialCount]
    no_week_count: int
    total: int


@router.get(
    "/{course_id}/materials/week-counts",
    response_model=MaterialCountsByWeekResponse,
    summary="Get material counts by week",
    description="Returns the number of materials available for each week. "
                "Useful for showing users which weeks have content available."
)
async def get_material_counts_by_week(
    course_id: str = Path(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Course identifier"
    ),
    user: User = Depends(require_authenticated),
    max_week: int = Query(12, ge=1, le=52, description="Maximum week number to include")
) -> MaterialCountsByWeekResponse:
    """
    Get material counts grouped by week number.

    Returns the count of materials for each week (1 to max_week),
    including weeks with zero materials. This helps users understand
    which weeks have content available for study guide generation.

    **Parameters:**
    - `course_id`: The course identifier
    - `max_week`: Maximum week number to include (default: 12)
    """
    try:
        # Verify course exists and is active
        course_service = get_course_service()
        course = course_service.get_course(course_id, include_weeks=False)

        if course is None or not course.active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )

        # Get material counts
        materials_service = get_course_materials_service()
        counts = materials_service.get_material_counts_by_week(course_id, max_week)

        logger.info(
            "User %s retrieved material counts for course %s: %d total materials",
            user.email, course_id, counts["total"]
        )

        return MaterialCountsByWeekResponse(**counts)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting material counts for %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get material counts."
        )
