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


@router.post("/courses/{course_id}/estimate-tokens")
async def estimate_tokens(
    course_id: str,
    weeks: Optional[List[int]] = Query(None, description="Week numbers to include")
):
    """Estimate token count for a study guide request.

    Returns estimated input tokens based on the materials that would be included.
    Helps users stay under rate limits (e.g., 10,000 tokens/minute).
    """
    try:
        files_service = get_files_api_service()

        # Get materials that would be included (same logic as generate)
        materials_with_text = []

        if weeks and len(weeks) > 0:
            for week_num in weeks:
                week_materials = await files_service.get_course_materials_with_text(
                    course_id=course_id,
                    week_number=week_num,
                    limit=3  # Same limit as generate
                )
                materials_with_text.extend(week_materials)
        else:
            materials_with_text = await files_service.get_course_materials_with_text(
                course_id=course_id,
                week_number=None,
                limit=5  # Same limit as generate
            )

        # Calculate character counts and estimate tokens
        # Rough estimation: ~4 characters per token for English text
        total_chars = 0
        material_details = []

        for material, text in materials_with_text:
            char_count = len(text)
            token_estimate = char_count // 4
            total_chars += char_count
            material_details.append({
                "title": material.title or material.filename,
                "week": material.week_number,
                "characters": char_count,
                "estimated_tokens": token_estimate
            })

        # Add system prompt (~500 tokens) and user prompt (~800 tokens)
        system_prompt_tokens = 500
        user_prompt_tokens = 800
        total_estimated_tokens = (total_chars // 4) + system_prompt_tokens + user_prompt_tokens

        # Rate limit info
        rate_limit = 10000  # tokens per minute
        will_exceed = total_estimated_tokens > rate_limit

        return {
            "course_id": course_id,
            "weeks": weeks,
            "material_count": len(materials_with_text),
            "materials": material_details,
            "total_characters": total_chars,
            "estimated_input_tokens": total_estimated_tokens,
            "rate_limit": rate_limit,
            "will_exceed_rate_limit": will_exceed,
            "recommendation": (
                "⚠️ Request will likely exceed rate limit. Try fewer weeks or wait 60 seconds."
                if will_exceed else
                "✅ Request should be within rate limits."
            )
        }

    except Exception as e:
        logger.error("Error estimating tokens: %s", e)
        raise HTTPException(500, detail=str(e)) from e
