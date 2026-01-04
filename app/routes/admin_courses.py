"""Admin API Routes for Course Management.

Provides CRUD endpoints for managing courses, weeks, and legal skills.
These endpoints are intended for administrative use only.

Note: Authentication middleware will be added in Phase 5.
See Issue #29 for the implementation plan.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel

from app.models.course_models import (
    Course,
    CourseCreate,
    CourseUpdate,
    CourseSummary,
    Week,
    WeekCreate,
    LegalSkill,
    MaterialsRegistry,
    CoreTextbook,
    Lecture,
    CaseStudy,
    MockExam,
)
from app.services.course_service import get_course_service
from app.services.materials_scanner import (
    scan_materials_folder,
    enhance_titles_with_ai,
    convert_to_materials_registry,
    ScanResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/courses",
    tags=["Admin - Courses"],
    responses={
        400: {"description": "Bad request - Invalid input"},
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    }
)


# Week number constraints
MIN_WEEK = 1
MAX_WEEK = 52


# ============================================================================
# Course Endpoints
# ============================================================================


@router.get("", response_model=List[CourseSummary])
async def list_courses(
    include_inactive: bool = Query(False, description="Include inactive courses")
):
    """
    List all courses.

    Returns a summary of each course including name, program, and week count.
    """
    try:
        service = get_course_service()
        courses = service.get_all_courses(include_inactive=include_inactive)
        logger.info("Listed %d courses", len(courses))
        return courses
    except Exception as e:
        logger.error("Error listing courses: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list courses: {str(e)}"
        )


@router.get("/{course_id}", response_model=Course)
async def get_course(
    course_id: str,
    include_weeks: bool = Query(True, description="Include weeks and legal skills")
):
    """
    Get a course by ID.

    Returns full course details including weeks, legal skills, and materials.

    **Parameters:**
    - `course_id`: The unique course identifier (e.g., "LLS-2025-2026")
    - `include_weeks`: Whether to include weeks and legal skills (default: true)

    **Example Response:**
    ```json
    {
        "id": "LLS-2025-2026",
        "name": "Law and Legal Skills",
        "academicYear": "2025-2026",
        "weeks": [...],
        "legalSkills": {...}
    }
    ```
    """
    try:
        service = get_course_service()
        course = service.get_course(course_id, include_weeks=include_weeks)

        if course is None:
            logger.warning("Course not found: %s", course_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        logger.info("Retrieved course: %s", course_id)
        return course
    except ValueError as e:
        logger.warning("Invalid course ID: %s - %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get course: {str(e)}"
        )


@router.post("", response_model=Course, status_code=status.HTTP_201_CREATED)
async def create_course(course_data: CourseCreate):
    """
    Create a new course.

    The course ID must be unique and follow the pattern: alphanumeric with hyphens
    and underscores (e.g., "LLS-2025-2026", "Criminal_Law_101").

    **Example Request:**
    ```json
    {
        "id": "Criminal_Law-2025-2026",
        "name": "Criminal Law",
        "academicYear": "2025-2026",
        "program": "European Law School",
        "institution": "University of Groningen",
        "materialSubjects": ["Criminal_Law"]
    }
    ```

    **Returns:** The created course object with timestamps.
    """
    try:
        service = get_course_service()
        course = service.create_course(course_data)
        logger.info("Created course: %s", course_data.id)
        return course
    except ValueError as e:
        logger.warning("Invalid course data: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error creating course: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course: {str(e)}"
        )


@router.patch("/{course_id}", response_model=Course)
async def update_course(course_id: str, updates: CourseUpdate):
    """
    Update a course.

    Only the fields provided in the request body will be updated.
    """
    try:
        service = get_course_service()
        course = service.update_course(course_id, updates)

        if course is None:
            logger.warning("Course not found for update: %s", course_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        logger.info("Updated course: %s", course_id)
        return course
    except ValueError as e:
        logger.warning("Invalid update for course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update course: {str(e)}"
        )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_course(course_id: str):
    """
    Deactivate a course (soft delete).

    The course will be hidden from normal listings but can be restored.
    Use `include_inactive=true` on list endpoint to see deactivated courses.
    """
    try:
        service = get_course_service()
        success = service.deactivate_course(course_id)

        if not success:
            logger.warning("Course not found for deactivation: %s", course_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        logger.info("Deactivated course: %s", course_id)
        return None
    except ValueError as e:
        logger.warning("Invalid course ID for deactivation: %s", course_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deactivating course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate course: {str(e)}"
        )


# ============================================================================
# Week Endpoints
# ============================================================================


@router.get("/{course_id}/weeks", response_model=List[Week])
async def list_weeks(course_id: str):
    """
    List all weeks for a course.

    Returns weeks sorted by week number.
    """
    try:
        service = get_course_service()
        weeks = service.get_course_weeks(course_id)
        logger.info("Listed %d weeks for course %s", len(weeks), course_id)
        return weeks
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error listing weeks for course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list weeks: {str(e)}"
        )


@router.get("/{course_id}/weeks/{week_number}", response_model=Week)
async def get_week(
    course_id: str,
    week_number: int = Path(..., ge=MIN_WEEK, le=MAX_WEEK, description="Week number (1-52)")
):
    """
    Get a specific week by number.

    Returns week details including topics, materials, and key concepts.
    """
    try:
        service = get_course_service()
        week = service.get_week(course_id, week_number)

        if week is None:
            logger.warning("Week %d not found in course %s", week_number, course_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Week {week_number} not found in course {course_id}"
            )

        logger.info("Retrieved week %d for course %s", week_number, course_id)
        return week
    except ValueError as e:
        logger.warning("Invalid request for week: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting week %d for course %s: %s", week_number, course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get week: {str(e)}"
        )


@router.put("/{course_id}/weeks/{week_number}", response_model=Week)
async def upsert_week(
    course_id: str,
    week_number: int = Path(..., ge=MIN_WEEK, le=MAX_WEEK, description="Week number (1-52)"),
    week_data: WeekCreate = ...
):
    """
    Create or update a week.

    If the week exists, it will be replaced. If not, it will be created.
    The week_number in the URL must match the weekNumber in the request body.

    **Example Request:**
    ```json
    {
        "weekNumber": 1,
        "title": "Introduction to Legal Systems",
        "topics": ["Legal Sources", "Court Hierarchy"],
        "materials": [],
        "keyConcepts": []
    }
    ```
    """
    # Validate URL week_number first (already validated by Path constraints)
    # Then check it matches the body
    if week_data.weekNumber != week_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Week number mismatch: URL has {week_number}, body has {week_data.weekNumber}"
        )

    try:
        service = get_course_service()
        week = service.upsert_week(course_id, week_data)
        logger.info("Upserted week %d for course %s", week_number, course_id)
        return week
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error upserting week %d for course %s: %s", week_number, course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert week: {str(e)}"
        )


@router.delete("/{course_id}/weeks/{week_number}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_week(
    course_id: str,
    week_number: int = Path(..., ge=MIN_WEEK, le=MAX_WEEK, description="Week number (1-52)")
):
    """
    Delete a week from a course.
    """
    try:
        service = get_course_service()
        success = service.delete_week(course_id, week_number)

        if not success:
            logger.warning("Week %d not found for deletion in course %s", week_number, course_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Week {week_number} not found in course {course_id}"
            )

        logger.info("Deleted week %d from course %s", week_number, course_id)
        return None
    except ValueError as e:
        logger.warning("Invalid delete week request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting week %d from course %s: %s", week_number, course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete week: {str(e)}"
        )


# ============================================================================
# Legal Skills Endpoints
# ============================================================================


@router.get("/{course_id}/skills", response_model=dict)
async def list_legal_skills(course_id: str):
    """
    List all legal skills for a course.

    Returns a dictionary of skill_id -> LegalSkill.
    """
    try:
        service = get_course_service()
        skills = service.get_legal_skills(course_id)
        logger.info("Listed %d legal skills for course %s", len(skills), course_id)
        return skills
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error listing legal skills for course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list legal skills: {str(e)}"
        )


@router.put("/{course_id}/skills/{skill_id}", response_model=LegalSkill)
async def upsert_legal_skill(course_id: str, skill_id: str, skill: LegalSkill):
    """
    Create or update a legal skill.

    If the skill exists, it will be replaced. If not, it will be created.
    """
    try:
        service = get_course_service()
        result = service.upsert_legal_skill(course_id, skill_id, skill)
        logger.info("Upserted legal skill '%s' for course %s", skill_id, course_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error upserting legal skill '%s' for course %s: %s", skill_id, course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert legal skill: {str(e)}"
        )


# ============================================================================
# Materials Scanning Endpoints
# ============================================================================


class MaterialsScanRequest(BaseModel):
    """Request options for materials scan."""
    use_ai_titles: bool = False  # Whether to use AI to generate better titles


class MaterialsScanResponse(BaseModel):
    """Response from materials scan."""
    course_id: str
    subjects_scanned: List[str]
    total_files: int
    categories: Dict[str, int]
    materials_updated: bool
    message: str


@router.post(
    "/{course_id}/scan-materials",
    response_model=MaterialsScanResponse,
    summary="Scan and update course materials",
    description="""
    Scan the course's material folders and update the materials registry.

    This endpoint:
    1. Gets the course's materialSubjects (folder names)
    2. Scans each folder for PDF, DOCX, and other documents
    3. Categorizes files by folder (Lectures, Readings, Core_Materials, etc.)
    4. Extracts week numbers from filenames
    5. Optionally uses AI to generate better titles
    6. Updates the course's materials in Firestore

    **Note:** Folders named "LLS Essential" (metadata) are skipped.
    """
)
async def scan_course_materials(
    course_id: str = Path(..., description="Course ID"),
    request: Optional[MaterialsScanRequest] = None
):
    """Scan material folders and update course materials registry."""
    service = get_course_service()

    # Get course
    course = service.get_course(course_id, include_weeks=False)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course not found: {course_id}"
        )

    subjects = course.materialSubjects or []
    if not subjects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course has no materialSubjects configured"
        )

    # Scan all subject folders
    all_materials = []
    all_categories: Dict[str, int] = {}

    for subject in subjects:
        logger.info("Scanning materials for subject: %s", subject)
        scan_result = scan_materials_folder(subject)
        all_materials.extend(scan_result.materials)
        for cat, count in scan_result.categories.items():
            all_categories[cat] = all_categories.get(cat, 0) + count

    if not all_materials:
        return MaterialsScanResponse(
            course_id=course_id,
            subjects_scanned=subjects,
            total_files=0,
            categories={},
            materials_updated=False,
            message="No materials found in configured folders"
        )

    # Optionally enhance titles with AI
    use_ai = request.use_ai_titles if request else False
    if use_ai:
        logger.info("Enhancing titles with AI for %d materials", len(all_materials))
        all_materials = await enhance_titles_with_ai(all_materials)

    # Convert to registry format
    combined_result = ScanResult(
        subject=",".join(subjects),
        total_files=len(all_materials),
        materials=all_materials,
        categories=all_categories
    )
    registry = convert_to_materials_registry(combined_result)

    # Update course in Firestore directly (materials is a complex nested dict)
    try:
        from datetime import datetime, timezone
        doc_ref = service.db.collection("courses").document(course_id)
        doc_ref.update({
            "materials": registry,
            "updatedAt": datetime.now(timezone.utc)
        })
        logger.info("Updated materials for course %s: %d files", course_id, len(all_materials))
    except Exception as e:
        logger.error("Failed to update materials for %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update materials: {str(e)}"
        )

    return MaterialsScanResponse(
        course_id=course_id,
        subjects_scanned=subjects,
        total_files=len(all_materials),
        categories=all_categories,
        materials_updated=True,
        message=f"Successfully scanned and updated {len(all_materials)} materials"
    )


@router.get(
    "/{course_id}/materials",
    summary="Get course materials registry",
    description="Returns the current materials registry for a course."
)
async def get_course_materials(
    course_id: str = Path(..., description="Course ID")
):
    """Get the materials registry for a course."""
    service = get_course_service()

    course = service.get_course(course_id, include_weeks=False)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course not found: {course_id}"
        )

    return {
        "course_id": course_id,
        "materials": course.materials.model_dump() if course.materials else None
    }
