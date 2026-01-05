"""API Routes for Study Guide Management and Persistence.

Provides endpoints for:
- Listing saved study guides for a course
- Getting a specific study guide
- Creating/generating a new study guide with persistence
- Deleting study guides
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    CreateStudyGuideRequest,
    StoredStudyGuide,
    StoredStudyGuideSummary,
)
from app.services.study_guide_persistence_service import get_study_guide_persistence_service
from app.services.files_api_service import get_files_api_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/study-guides",
    tags=["Study Guide Management"]
)


@router.get("/courses/{course_id}")
async def list_course_study_guides(
    course_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max results")
):
    """List available study guides for a course.

    Returns guide summaries without full content.
    Use GET /api/study-guides/courses/{course_id}/{guide_id} to get full guide.
    """
    try:
        service = get_study_guide_persistence_service()
        guides = await service.list_study_guides(
            course_id=course_id,
            limit=limit
        )

        return {
            "guides": guides,
            "count": len(guides),
            "course_id": course_id
        }

    except Exception as e:
        logger.error("Error listing study guides: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/courses/{course_id}/{guide_id}")
async def get_study_guide(course_id: str, guide_id: str):
    """Get a specific study guide by ID."""
    try:
        service = get_study_guide_persistence_service()
        guide = await service.get_study_guide(course_id, guide_id)

        if not guide:
            raise HTTPException(404, detail=f"Study guide {guide_id} not found")

        return guide

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting study guide: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.post("/courses/{course_id}")
async def create_study_guide(
    course_id: str,
    request: CreateStudyGuideRequest
):
    """Generate and save a new study guide.

    Generates a comprehensive study guide using course materials
    and saves it to Firestore for future retrieval.
    """
    try:
        persistence_service = get_study_guide_persistence_service()
        files_service = get_files_api_service()

        # Generate topic description based on weeks
        if request.weeks and len(request.weeks) > 0:
            if len(request.weeks) == 1:
                topic = f"Course '{course_id}' - Week {request.weeks[0]}"
            else:
                topic = f"Course '{course_id}' - Weeks {', '.join(map(str, request.weeks))}"
        else:
            topic = f"Course '{course_id}' - All Materials"

        # Generate the study guide content
        logger.info("Generating study guide for %s, weeks=%s", course_id, request.weeks)
        content = await files_service.generate_study_guide_from_course(
            course_id=course_id,
            topic=topic,
            week_numbers=request.weeks
        )

        # Check for duplicates unless explicitly allowed
        if not request.allow_duplicate:
            existing = await persistence_service.find_duplicate_guide(
                course_id=course_id,
                content=content
            )
            if existing:
                logger.info("Found duplicate study guide: %s", existing.get("id"))
                return {
                    "guide": existing,
                    "is_duplicate": True,
                    "message": "Returning existing study guide with same content"
                }

        # Save the new study guide
        guide_data = await persistence_service.save_study_guide(
            course_id=course_id,
            content=content,
            week_numbers=request.weeks,
            title=request.title
        )

        return {
            "guide": guide_data,
            "is_duplicate": False,
            "message": "Study guide generated and saved successfully"
        }

    except Exception as e:
        logger.error("Error creating study guide: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.delete("/courses/{course_id}/{guide_id}")
async def delete_study_guide(course_id: str, guide_id: str):
    """Delete a study guide."""
    try:
        service = get_study_guide_persistence_service()
        deleted = await service.delete_study_guide(course_id, guide_id)

        if not deleted:
            raise HTTPException(404, detail=f"Study guide {guide_id} not found")

        return {"message": "Study guide deleted successfully", "id": guide_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting study guide: %s", e)
        raise HTTPException(500, detail=str(e)) from e

