"""Public API Routes for Course Access.

Provides read-only course endpoints for authenticated users (any domain).
Unlike admin_courses.py, these endpoints don't require @mgms.eu domain.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies.auth import require_authenticated
from app.models.auth_models import User
from app.models.course_models import CourseSummary
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

