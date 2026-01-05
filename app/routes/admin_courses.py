"""Admin API Routes for Course Management.

Provides CRUD endpoints for managing courses, weeks, and legal skills.
These endpoints are intended for administrative use only.

Note: Authentication middleware will be added in Phase 5.
See Issue #29 for the implementation plan.
"""

import logging
import pathlib
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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
    UploadedMaterial,
    CourseMaterial,
    CourseTopic,
    TopicCreate,
    TopicUpdate,
)
from app.services.course_service import (
    get_course_service,
    CourseNotFoundError,
    CourseAlreadyExistsError,
    FirestoreOperationError,
    ServiceValidationError,
)
from app.services.materials_scanner import (
    scan_materials_folder,
    enhance_titles_with_ai,
    convert_to_materials_registry,
    ScanResult,
)
from app.services.slide_archive import (
    get_file_type,
    extract_slide_archive,
    get_slide_image,
    get_all_text,
    SlideArchiveData,
)
from app.services.text_extractor import (
    extract_text,
    detect_file_type as detect_extraction_type,
    ExtractionResult,
)
from app.services.document_upload_service import (
    upload_document,
    FileValidationError,
    StorageError,
    SUPPORTED_EXTENSIONS,
    TIER_FOLDERS,
    CATEGORY_FOLDERS,
    MAX_FILE_SIZE,
)

logger = logging.getLogger(__name__)

# Base directory for materials - resolved once at module load
MATERIALS_BASE = pathlib.Path("Materials").resolve()


def resolve_incomplete_path(file_path: str) -> Optional[str]:
    """
    Attempt to resolve an incomplete storagePath by searching Course_Materials subdirectories.

    This handles cases where storagePath was stored incorrectly as e.g. "Readings/file.pdf"
    instead of "Course_Materials/LLS/Readings/file.pdf".

    Args:
        file_path: The incomplete path to resolve

    Returns:
        The corrected path if found, None otherwise
    """
    # If path already starts with a known tier folder, it's likely correct
    if file_path.startswith(("Course_Materials/", "Syllabus/", "Supplementary_Sources/")):
        return None

    # Search in Course_Materials subdirectories
    course_materials_dir = MATERIALS_BASE / "Course_Materials"
    if not course_materials_dir.exists():
        return None

    # file_path might be something like "Readings/file.pdf" or "Lectures/file.pdf"
    # Search all subject folders for a match
    for subject_dir in course_materials_dir.iterdir():
        if subject_dir.is_dir():
            candidate_path = subject_dir / file_path
            if candidate_path.exists():
                # Found it! Return the corrected relative path
                corrected = f"Course_Materials/{subject_dir.name}/{file_path}"
                logger.info("Resolved incomplete path '%s' to '%s'", file_path, corrected)
                return corrected

    return None


def validate_materials_path(file_path: str, try_resolve: bool = True) -> pathlib.Path:
    """
    Validate and resolve a file path within the Materials directory.

    This function prevents path traversal attacks by ensuring the resolved
    path is within the Materials directory.

    Args:
        file_path: Relative path within Materials directory
        try_resolve: If True, attempt to resolve incomplete paths by searching
                     Course_Materials subdirectories

    Returns:
        Resolved absolute path to the file

    Raises:
        HTTPException: If path is invalid or outside Materials directory
    """
    # Reject paths with null bytes (can bypass some checks)
    if "\x00" in file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path: null bytes not allowed"
        )

    # Build the path and resolve it
    try:
        # Use the already-resolved MATERIALS_BASE
        full_path = (MATERIALS_BASE / file_path).resolve()
    except (ValueError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file path: {e}"
        )

    # Security: Ensure the resolved path is under MATERIALS_BASE
    # Using is_relative_to() is the secure way to check this
    try:
        full_path.relative_to(MATERIALS_BASE)
    except ValueError:
        # Path is not under MATERIALS_BASE - potential path traversal
        logger.warning("Path traversal attempt blocked: %s -> %s", file_path, full_path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: path outside materials directory"
        )

    # If file doesn't exist and try_resolve is True, attempt to resolve incomplete path
    if not full_path.exists() and try_resolve:
        corrected_path = resolve_incomplete_path(file_path)
        if corrected_path:
            # Validate the corrected path exists before returning it
            corrected_full_path = (MATERIALS_BASE / corrected_path).resolve()
            # Security check: ensure corrected path is also under MATERIALS_BASE
            try:
                corrected_full_path.relative_to(MATERIALS_BASE)
            except ValueError:
                logger.warning("Corrected path outside materials directory: %s", corrected_full_path)
                return full_path
            
            # Only return corrected path if file actually exists
            if corrected_full_path.exists():
                return corrected_full_path
            else:
                logger.warning("Corrected path does not exist: %s", corrected_full_path)

    return full_path

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


# ============================================================================
# Course Endpoints
# ============================================================================


@router.get("", response_model=PaginatedCoursesResponse)
async def list_courses(
    include_inactive: bool = Query(False, description="Include inactive courses"),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT, description="Maximum number of courses to return"),
    offset: int = Query(0, ge=0, description="Number of courses to skip")
):
    """
    List all courses with pagination.

    Returns a paginated summary of each course including name, program, and week count.

    **Parameters:**
    - `include_inactive`: Include inactive courses (default: false)
    - `limit`: Maximum number of courses to return (1-100, default: 50)
    - `offset`: Number of courses to skip for pagination (default: 0)
    """
    try:
        service = get_course_service()
        courses, total = service.get_all_courses(
            include_inactive=include_inactive,
            limit=limit,
            offset=offset
        )
        logger.info("Listed %d courses (total: %d)", len(courses), total)
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
            detail="Database temporarily unavailable. Please try again later."
        )
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
    except CourseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
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
            detail="Database temporarily unavailable. Please try again later."
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
    except CourseAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except (ServiceValidationError, ValueError) as e:
        logger.warning("Invalid course data: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FirestoreOperationError as e:
        logger.error("Firestore error creating course: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again later."
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
    except (ServiceValidationError, ValueError) as e:
        logger.warning("Invalid update for course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except CourseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except FirestoreOperationError as e:
        logger.error("Firestore error updating course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again later."
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
    except (ServiceValidationError, ValueError) as e:
        logger.warning("Invalid course ID for deactivation: %s - %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except CourseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except FirestoreOperationError as e:
        logger.error("Firestore error deactivating course %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again later."
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
    warnings: Optional[List[str]] = None


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
    all_course_materials = []  # Unified CourseMaterial objects

    for subject in subjects:
        logger.info("Scanning materials for subject: %s", subject)
        scan_result = scan_materials_folder(subject)
        all_materials.extend(scan_result.materials)
        for cat, count in scan_result.categories.items():
            all_categories[cat] = all_categories.get(cat, 0) + count

        # Convert to unified CourseMaterial format
        from app.services.materials_scanner import convert_to_course_materials
        course_materials = convert_to_course_materials(scan_result, subject)
        if course_materials:
            all_course_materials.extend(course_materials)

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
        # Also update titles in unified materials
        title_map = {m.filename: m.title for m in all_materials if m.title}
        for cm in all_course_materials:
            if cm.filename in title_map:
                cm.title = title_map[cm.filename]

    # Convert to registry format (legacy - kept for backward compatibility)
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
        logger.info("Updated legacy materials registry for course %s: %d files", course_id, len(all_materials))
    except Exception as e:
        logger.error("Failed to update materials for %s: %s", course_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update materials: {str(e)}"
        )

    # Store in unified materials collection
    warnings = []
    try:
        from app.services.course_materials_service import get_course_materials_service
        materials_service = get_course_materials_service()
        count = materials_service.bulk_upsert_materials(course_id, all_course_materials)
        logger.info("Upserted %d materials to unified collection for course %s", count, course_id)
    except Exception as e:
        logger.error("Failed to upsert unified materials for %s: %s", course_id, e)
        warnings.append(f"Failed to update unified materials collection: {str(e)}")

    return MaterialsScanResponse(
        course_id=course_id,
        subjects_scanned=subjects,
        total_files=len(all_materials),
        categories=all_categories,
        materials_updated=True,
        message=f"Successfully scanned and updated {len(all_materials)} materials",
        warnings=warnings if warnings else None
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


class SyncWeekMaterialsResponse(BaseModel):
    """Response from syncing materials to weeks."""
    course_id: str
    weeks_updated: int
    materials_linked: int
    message: str


@router.post(
    "/{course_id}/sync-week-materials",
    response_model=SyncWeekMaterialsResponse,
    summary="Sync materials to course weeks",
    description="""
    Automatically link materials to course weeks based on week numbers.

    This endpoint:
    1. Gets the course's materials registry (lectures, readings with week numbers)
    2. For each week, creates WeekMaterial entries for matching materials
    3. Updates the week's materials list in Firestore

    Materials are matched by their `week` field. Materials without a week number
    are not automatically linked.
    """
)
async def sync_week_materials(
    course_id: str = Path(..., description="Course ID")
):
    """Auto-link materials to weeks based on week numbers."""
    service = get_course_service()

    # Get course with weeks
    course = service.get_course(course_id, include_weeks=True)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course not found: {course_id}"
        )

    materials = course.materials
    if not materials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course has no materials. Run 'Scan Folders' first."
        )

    weeks = course.weeks or []
    if not weeks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course has no weeks configured."
        )

    # Build week -> materials mapping
    week_materials_map: Dict[int, List[Dict]] = {}

    # Add lectures
    for lecture in materials.lectures or []:
        if lecture.week:
            if lecture.week not in week_materials_map:
                week_materials_map[lecture.week] = []
            week_materials_map[lecture.week].append({
                "type": "lecture",
                "file": lecture.file,
                "title": lecture.title
            })

    # Add readings if they exist
    readings = getattr(materials, 'readings', None) or []
    for reading in readings:
        week = getattr(reading, 'week', None)
        if week:
            if week not in week_materials_map:
                week_materials_map[week] = []
            week_materials_map[week].append({
                "type": "reading",
                "file": reading.file,
                "title": reading.title
            })

    # Update weeks with materials
    weeks_updated = 0
    materials_linked = 0

    from datetime import datetime, timezone

    for week in weeks:
        week_num = week.weekNumber
        if week_num in week_materials_map:
            new_materials = week_materials_map[week_num]

            # Convert to WeekMaterial format
            week_material_list = [
                {"type": m["type"], "file": m["file"]}
                for m in new_materials
            ]

            # Update week in Firestore (document ID is "week-{n}")
            try:
                week_ref = service.db.collection("courses").document(course_id)\
                    .collection("weeks").document(f"week-{week_num}")
                week_ref.update({
                    "materials": week_material_list,
                    "updatedAt": datetime.now(timezone.utc)
                })
                weeks_updated += 1
                materials_linked += len(new_materials)
            except Exception as e:
                logger.warning("Failed to update week %d: %s", week_num, e)

    return SyncWeekMaterialsResponse(
        course_id=course_id,
        weeks_updated=weeks_updated,
        materials_linked=materials_linked,
        message=f"Linked {materials_linked} materials to {weeks_updated} weeks"
    )


# ============================================================================
# Syllabus Import Endpoints
# ============================================================================


class SyllabusFileInfo(BaseModel):
    """Information about a single syllabus PDF file."""
    filename: str
    path: str
    pages: int


class SyllabusFolderInfo(BaseModel):
    """Information about a discovered syllabus folder."""
    subject: str
    path: str
    files: List[SyllabusFileInfo]
    total_pages: int


class ScanSyllabiResponse(BaseModel):
    """Response from scanning for syllabi folders."""
    folders: List[SyllabusFolderInfo]
    count: int


class ExtractedTopicData(BaseModel):
    """Extracted topic from syllabus."""
    id: str
    name: str
    description: str
    weekNumbers: List[int] = []
    extractionConfidence: Optional[str] = Field(
        None,
        description="Confidence level: 'high' (explicit), 'medium' (implied), 'low' (inferred)"
    )
    extractedFromSyllabus: bool = True


class ExtractedCourseData(BaseModel):
    """Extracted course data from syllabus."""
    # Basic course info
    courseName: Optional[str] = None
    courseCode: Optional[str] = None
    academicYear: Optional[str] = None
    program: Optional[str] = None
    institution: Optional[str] = None
    totalPoints: Optional[int] = None
    passingThreshold: Optional[int] = None
    components: Optional[List[Dict]] = None
    coordinators: Optional[List[Dict]] = None
    lecturers: Optional[List[Dict]] = None
    weeks: Optional[List[Dict]] = None
    examInfo: Optional[Dict] = None
    participationRequirements: Optional[str] = None
    materialSubjects: Optional[List[str]] = None  # Derived from syllabus folder

    # Extended syllabus data
    courseDescription: Optional[str] = None
    learningObjectives: Optional[List[str]] = None
    prerequisites: Optional[str] = None
    teachingMethods: Optional[str] = None
    assessmentInfo: Optional[str] = None
    assessments: Optional[List[Dict]] = None
    attendancePolicy: Optional[str] = None
    academicIntegrity: Optional[str] = None
    sections: Optional[List[Dict]] = None
    additionalNotes: Optional[str] = None

    # Extracted topics (Issue #68)
    extractedTopics: Optional[List[ExtractedTopicData]] = None
    topicExtractionNotes: Optional[str] = None

    # Raw text for storage
    rawText: Optional[str] = None
    sourceFolder: Optional[str] = None
    sourceFiles: Optional[List[str]] = None


class ImportSyllabusRequest(BaseModel):
    """Request to import course data from a syllabus folder."""
    syllabus_path: str  # Path to folder relative to Materials/


class ImportSyllabusResponse(BaseModel):
    """Response from syllabus import."""
    success: bool
    extracted_data: ExtractedCourseData
    message: str


@router.get("/syllabi/scan", response_model=ScanSyllabiResponse)
async def scan_syllabi(
    subject: Optional[str] = Query(None, description="Filter by subject folder")
):
    """
    Scan for syllabus folders in the Materials/Syllabus directory.

    Returns a list of discovered syllabus folders with their PDF files.
    """
    try:
        from app.services.syllabus_parser import scan_syllabi as do_scan

        folders = do_scan(subject=subject)

        return ScanSyllabiResponse(
            folders=[SyllabusFolderInfo(
                subject=f["subject"],
                path=f["path"],
                files=[SyllabusFileInfo(**file) for file in f["files"]],
                total_pages=f["total_pages"]
            ) for f in folders],
            count=len(folders)
        )
    except Exception as e:
        logger.error("Error scanning syllabi: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan syllabi: {str(e)}"
        )


@router.post("/syllabi/extract", response_model=ImportSyllabusResponse)
async def extract_syllabus_data(request: ImportSyllabusRequest):
    """
    Extract course data from all PDFs in a syllabus folder using AI.

    This endpoint reads all PDFs in the folder, extracts text, and uses AI to parse
    structured course information including weeks, readings, lecturers, and topics.

    The extracted data includes detailed topics with descriptions and week associations.
    These can be reviewed and edited before creating/updating a course.
    Also includes raw text and source information for storage with the course.
    """
    try:
        from app.services.syllabus_parser import extract_text_from_folder
        from app.services.syllabus_extractor import extract_course_data_with_topics

        # Extract subject from syllabus path (e.g., "Syllabus/LLS" -> "LLS")
        path_parts = request.syllabus_path.split("/")
        subject = path_parts[1] if len(path_parts) >= 2 else None

        # Extract text from all PDFs in folder (with details)
        logger.info("Extracting text from folder: %s", request.syllabus_path)
        extraction_result = extract_text_from_folder(
            request.syllabus_path,
            return_details=True
        )

        raw_text = extraction_result["text"]
        source_files = extraction_result["files"]
        source_folder = extraction_result["folder_path"]

        # Use AI to extract structured data WITH enhanced topic extraction
        logger.info("Extracting course data and topics with AI...")
        extracted = await extract_course_data_with_topics(raw_text)

        # Add materialSubjects derived from syllabus folder
        if subject:
            extracted["materialSubjects"] = [subject]

        # Add raw text and source info for storage
        extracted["rawText"] = raw_text
        extracted["sourceFolder"] = source_folder
        extracted["sourceFiles"] = source_files

        topic_count = len(extracted.get("extractedTopics", []))
        return ImportSyllabusResponse(
            success=True,
            extracted_data=ExtractedCourseData(**extracted),
            message=f"Successfully extracted course data and {topic_count} topics from {len(source_files)} file(s)"
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Syllabus not found: {str(e)}"
        )
    except Exception as e:
        logger.error("Error extracting syllabus data: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract syllabus data: {str(e)}"
        )


# ============================================================================
# Topic Endpoints (Issue #68)
# ============================================================================


class TopicListResponse(BaseModel):
    """Response for listing topics."""
    topics: List[CourseTopic]
    count: int


class TopicRegenerateRequest(BaseModel):
    """Request to regenerate topics from stored syllabus."""
    delete_existing: bool = True  # Whether to delete existing topics first


class TopicRegenerateResponse(BaseModel):
    """Response from topic regeneration."""
    success: bool
    topics_created: int
    extraction_notes: Optional[str] = None
    message: str


@router.get("/{course_id}/topics", response_model=TopicListResponse)
async def list_topics(
    course_id: str = Path(..., description="Course ID"),
    week: Optional[int] = Query(None, description="Filter by week number"),
):
    """
    Get all topics for a course.

    Topics are extracted from syllabi and can be:
    - Associated with specific weeks
    - Course-wide (no week association)

    **Example:**
    ```
    GET /api/admin/courses/LLS-2025-2026/topics
    GET /api/admin/courses/LLS-2025-2026/topics?week=3
    ```
    """
    try:
        service = get_course_service()
        topics = service.get_topics(course_id, week_number=week)
        return TopicListResponse(topics=topics, count=len(topics))
    except CourseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FirestoreOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable."
        )


@router.get("/{course_id}/topics/{topic_id}", response_model=CourseTopic)
async def get_topic(
    course_id: str = Path(..., description="Course ID"),
    topic_id: str = Path(..., description="Topic ID"),
):
    """
    Get a specific topic by ID.

    **Example:**
    ```
    GET /api/admin/courses/LLS-2025-2026/topics/criminal-law-mens-rea-abc12345
    ```
    """
    try:
        service = get_course_service()
        topic = service.get_topic(course_id, topic_id)
        if topic is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic not found: {topic_id}"
            )
        return topic
    except HTTPException:
        raise  # Re-raise HTTPException without wrapping
    except ServiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FirestoreOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable."
        )


@router.post("/{course_id}/topics", response_model=CourseTopic, status_code=status.HTTP_201_CREATED)
async def create_topic(
    course_id: str = Path(..., description="Course ID"),
    topic_data: TopicCreate = ...,
):
    """
    Create a new topic for a course.

    **Example Request:**
    ```json
    {
        "name": "Constitutional Review",
        "description": "Examination of constitutional review processes...",
        "weekNumbers": [2, 3]
    }
    ```
    """
    try:
        service = get_course_service()
        topic = service.create_topic(course_id, topic_data)
        logger.info("Created topic '%s' for course %s", topic.id, course_id)
        return topic
    except CourseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FirestoreOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable."
        )


@router.put("/{course_id}/topics/{topic_id}", response_model=CourseTopic)
async def update_topic(
    course_id: str = Path(..., description="Course ID"),
    topic_id: str = Path(..., description="Topic ID"),
    updates: TopicUpdate = ...,
):
    """
    Update an existing topic.

    All fields are optional. Only provided fields will be updated.

    **Example Request:**
    ```json
    {
        "name": "Updated Topic Name",
        "weekNumbers": [1, 2, 3]
    }
    ```
    """
    try:
        service = get_course_service()
        topic = service.update_topic(course_id, topic_id, updates)
        if topic is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic not found: {topic_id}"
            )
        logger.info("Updated topic '%s' for course %s", topic_id, course_id)
        return topic
    except ServiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FirestoreOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable."
        )


@router.delete("/{course_id}/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    course_id: str = Path(..., description="Course ID"),
    topic_id: str = Path(..., description="Topic ID"),
):
    """
    Delete a topic from a course.

    **Example:**
    ```
    DELETE /api/admin/courses/LLS-2025-2026/topics/criminal-law-mens-rea-abc12345
    ```
    """
    try:
        service = get_course_service()
        deleted = service.delete_topic(course_id, topic_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic not found: {topic_id}"
            )
        logger.info("Deleted topic '%s' from course %s", topic_id, course_id)
        return None
    except ServiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FirestoreOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable."
        )


@router.post("/{course_id}/topics/regenerate", response_model=TopicRegenerateResponse)
async def regenerate_topics(
    course_id: str = Path(..., description="Course ID"),
    request: TopicRegenerateRequest = TopicRegenerateRequest(),
):
    """
    Regenerate topics for a course from its stored syllabus text.

    This endpoint:
    1. Retrieves the stored raw syllabus text for the course
    2. Uses AI to extract topics with descriptions
    3. Optionally deletes existing topics first
    4. Creates new topics in the database

    **Example Request:**
    ```json
    {
        "delete_existing": true
    }
    ```
    """
    try:
        from app.services.syllabus_extractor import extract_topics_from_syllabus

        service = get_course_service()

        # Get the course to retrieve stored syllabus text
        course = service.get_course(course_id, include_weeks=False)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        # Check if we have stored syllabus text
        # Look for rawText in the course data (stored during import)
        course_doc = service.db.collection("courses").document(course_id).get()
        course_data = course_doc.to_dict() if course_doc.exists else {}
        syllabus_text = course_data.get("rawText")

        if not syllabus_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No stored syllabus text found for this course. Import a syllabus first."
            )

        # Delete existing topics if requested
        if request.delete_existing:
            deleted_count = service.delete_all_topics(course_id)
            logger.info("Deleted %d existing topics before regeneration", deleted_count)

        # Extract topics using AI
        logger.info("Regenerating topics for course %s", course_id)
        result = await extract_topics_from_syllabus(syllabus_text, course_name=course.name)

        # Create topics in database
        topics = service.bulk_create_topics(course_id, result["topics"])

        return TopicRegenerateResponse(
            success=True,
            topics_created=len(topics),
            extraction_notes=result.get("extractionNotes"),
            message=f"Successfully regenerated {len(topics)} topics for course {course_id}"
        )

    except CourseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FirestoreOperationError as e:
        logger.error("Firestore error regenerating topics: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable."
        )
    except Exception as e:
        logger.error("Error regenerating topics: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate topics: {str(e)}"
        )


# ============================================================================
# Material Preview Endpoint
# ============================================================================


@router.get("/materials/preview/{file_path:path}")
async def preview_material(file_path: str):
    """
    Get a material file for preview.

    Returns the file with appropriate content type for browser preview.
    Supports PDF, images, and text files.

    **Parameters:**
    - `file_path`: Path relative to Materials/ directory

    **Example:**
    ```
    GET /api/admin/courses/materials/preview/Course_Materials/LLS/Readings/dutch_example.pdf
    ```
    """
    import mimetypes
    from fastapi.responses import FileResponse

    # Validate and resolve path (prevents path traversal)
    full_path = validate_materials_path(file_path)

    # Check file exists
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )

    if not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a file"
        )

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(full_path))
    if content_type is None:
        content_type = "application/octet-stream"

    # Return file for inline preview (not download)
    # Check if this is a slide archive (ZIP with manifest.json)
    file_type = get_file_type(full_path)

    if file_type == 'slide_archive':
        # Return metadata about the slide archive so frontend can use the slide viewer
        archive_data = extract_slide_archive(full_path)
        if archive_data:
            return {
                "type": "slide_archive",
                "file_path": file_path,
                "num_pages": archive_data.num_pages,
                "slides": [
                    {
                        "page_number": slide.page_number,
                        "width": slide.width,
                        "height": slide.height,
                        "has_text": bool(slide.text_content)
                    }
                    for slide in archive_data.slides
                ]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to extract slide archive"
            )

    # For real PDFs, return the file for inline preview
    return FileResponse(
        path=full_path,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{full_path.name}"'
        }
    )



@router.get("/materials/slide/{file_path:path}/page/{page_number}")
async def get_slide_page(
    file_path: str = Path(..., description="File path relative to Materials/"),
    page_number: int = Path(..., ge=1, description="Page number (1-based)")
):
    """Get a slide image from a slide archive.

    Returns the JPEG image for the specified page number.
    """
    from fastapi.responses import Response

    # Validate and resolve path (prevents path traversal)
    full_path = validate_materials_path(file_path)

    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Get slide image
    result = get_slide_image(full_path, page_number)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slide {page_number} not found"
        )

    image_bytes, media_type = result
    return Response(
        content=image_bytes,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/materials/slide/{file_path:path}/text")
async def get_slide_archive_text(
    file_path: str = Path(..., description="File path relative to Materials/"),
    page: Optional[int] = Query(None, ge=1, description="Specific page number, or None for all")
):
    """Get text content from a slide archive.

    If page is specified, returns text for that page only.
    If page is None, returns all text concatenated (useful for indexing).
    """
    from app.services.slide_archive import get_slide_text

    # Validate and resolve path (prevents path traversal)
    full_path = validate_materials_path(file_path)

    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if page:
        text = get_slide_text(full_path, page)
        if text is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Page {page} not found")
        return {"page": page, "text": text}
    else:
        text = get_all_text(full_path)
        return {"text": text}


@router.get("/materials/info/{file_path:path}")
async def get_material_info(
    file_path: str = Path(..., description="File path relative to Materials/")
):
    """Get information about a material file.

    Returns the file type and metadata.
    Useful for determining how to display the file before loading it.
    """
    # Validate and resolve path (prevents path traversal)
    full_path = validate_materials_path(file_path)

    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_type = get_file_type(full_path)

    result = {
        "file_path": file_path,
        "file_name": full_path.name,
        "file_type": file_type,
        "size_bytes": full_path.stat().st_size
    }

    if file_type == 'slide_archive':
        archive_data = extract_slide_archive(full_path)
        if archive_data:
            result["num_pages"] = archive_data.num_pages
            result["slides"] = [
                {
                    "page_number": s.page_number,
                    "width": s.width,
                    "height": s.height,
                    "has_text": bool(s.text_content)
                }
                for s in archive_data.slides
            ]

    return result


# ============================================================================
# Text Extraction Endpoints
# ============================================================================

@router.get("/materials/extract/{file_path:path}")
async def extract_material_text(
    file_path: str = Path(..., description="Path to material file relative to Materials folder")
):
    """Extract text from any supported material file.

    Supports:
    - PDFs (real PDFs)
    - Slide Archives (ZIP with manifest.json)
    - Images (PNG, JPG, etc. via OCR)
    - DOCX files
    - Markdown/Text files
    - HTML files
    - JSON files

    Returns extracted text and metadata for use in LLM operations
    (quizzes, summaries, study guides, etc.)
    """
    # Validate and resolve path (prevents path traversal)
    full_path = validate_materials_path(file_path)

    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )

    result = extract_text(full_path)

    return {
        "file_path": result.file_path,
        "file_type": result.file_type,
        "success": result.success,
        "error": result.error,
        "text": result.text,
        "text_length": len(result.text),
        "metadata": result.metadata,
        "pages": result.pages
    }


@router.get("/materials/extract-batch")
async def extract_batch_text(
    folder: str = Query(..., description="Folder path relative to Materials"),
    recursive: bool = Query(True, description="Whether to search subdirectories")
):
    """Extract text from all supported files in a folder.

    Returns a summary of extraction results for batch processing.
    Useful for indexing all materials for a course.
    """
    from app.services.text_extractor import extract_all_from_folder, get_extraction_summary

    # Validate and resolve path (prevents path traversal)
    folder_path = validate_materials_path(folder)

    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder not found: {folder}"
        )

    results = extract_all_from_folder(folder_path, recursive=recursive)
    summary = get_extraction_summary(results)

    # Include abbreviated results (text truncated for response size)
    file_results = []
    for r in results:
        file_results.append({
            "file_path": r.file_path,
            "file_type": r.file_type,
            "success": r.success,
            "error": r.error,
            "text_preview": r.text[:500] + "..." if len(r.text) > 500 else r.text,
            "text_length": len(r.text)
        })

    return {
        "folder": folder,
        "summary": summary,
        "files": file_results
    }


# ============================================================================
# Document Upload Endpoints
# ============================================================================


class UploadResponse(BaseModel):
    """Response model for document upload."""
    success: bool
    material: UploadedMaterial
    message: str


class MaterialListResponse(BaseModel):
    """Response model for listing uploaded materials."""
    materials: List[UploadedMaterial]
    count: int


@router.post(
    "/{course_id}/materials/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document to course materials",
    description="""
    Upload a document (PDF, DOCX, image, text file) to course materials.

    The file will be:
    1. Validated (type, size)
    2. Stored in the appropriate Materials folder
    3. Text extracted automatically
    4. Metadata stored in Firestore

    Supported file types: PDF, DOCX, PPTX, PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP, TXT, MD, HTML
    Maximum file size: 50MB
    """
)
async def upload_course_material(
    course_id: str = Path(..., description="Course ID"),
    file: UploadFile = File(..., description="File to upload"),
    tier: str = Form(..., description="Material tier: syllabus, course_materials, or supplementary"),
    category: Optional[str] = Form(None, description="Category (for course_materials): lecture, reading, or case"),
    title: Optional[str] = Form(None, description="Display title (defaults to filename)"),
    description: Optional[str] = Form(None, description="Material description"),
    week_number: Optional[int] = Form(None, description="Week number to link to"),
    extract_text: bool = Form(True, description="Whether to extract text automatically"),
    generate_summary: bool = Form(True, description="Whether to generate AI summary automatically")
):
    """
    Upload a document to course materials.

    Args:
        course_id: Course ID
        file: File to upload
        tier: Material tier (syllabus, course_materials, supplementary)
        category: Optional category for course_materials tier
        title: Optional display title
        description: Optional description
        week_number: Optional week number to link to
        extract_text: Whether to extract text automatically
        generate_summary: Whether to generate AI summary automatically

    Returns:
        UploadResponse with material metadata
    """
    try:
        # Verify course exists
        service = get_course_service()
        course = service.get_course(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        # Read file content
        file_content = await file.read()

        # Upload document
        material = await upload_document(
            course_id=course_id,
            filename=file.filename,
            file_content=file_content,
            tier=tier,
            category=category,
            title=title,
            description=description,
            week_number=week_number,
            uploaded_by=None,  # TODO: Add user ID when auth is implemented
            extract_text_flag=extract_text,
            generate_summary_flag=generate_summary
        )

        return UploadResponse(
            success=True,
            material=material,
            message=f"Successfully uploaded {file.filename}"
        )

    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get(
    "/{course_id}/materials/uploads",
    response_model=MaterialListResponse,
    summary="List uploaded materials",
    description="Get all uploaded materials for a course."
)
async def list_uploaded_materials(
    course_id: str = Path(..., description="Course ID"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    week_number: Optional[int] = Query(None, description="Filter by week number")
):
    """
    List all uploaded materials for a course.

    Args:
        course_id: Course ID
        tier: Optional tier filter
        week_number: Optional week number filter

    Returns:
        MaterialListResponse with list of materials
    """
    try:
        # Verify course exists
        service = get_course_service()
        course = service.get_course(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        # Get materials from Firestore
        from app.services.gcp_service import get_firestore_client
        db = get_firestore_client()

        query = db.collection('courses').document(course_id).collection('uploadedMaterials')

        # Apply filters
        if tier:
            query = query.where('tier', '==', tier)
        if week_number is not None:
            query = query.where('weekNumber', '==', week_number)

        # Execute query
        docs = query.stream()
        materials = [UploadedMaterial(**doc.to_dict()) for doc in docs]

        # Sort by upload date (newest first)
        materials.sort(key=lambda m: m.uploadedAt, reverse=True)

        return MaterialListResponse(
            materials=materials,
            count=len(materials)
        )

    except Exception as e:
        logger.error(f"Failed to list uploaded materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list materials: {str(e)}"
        )


@router.get(
    "/{course_id}/materials/uploads/{material_id}",
    response_model=UploadedMaterial,
    summary="Get uploaded material details",
    description="Get details of a specific uploaded material."
)
async def get_uploaded_material(
    course_id: str = Path(..., description="Course ID"),
    material_id: str = Path(..., description="Material ID")
):
    """
    Get details of a specific uploaded material.

    Args:
        course_id: Course ID
        material_id: Material ID

    Returns:
        UploadedMaterial object
    """
    try:
        from app.services.gcp_service import get_firestore_client
        db = get_firestore_client()

        doc_ref = db.collection('courses').document(course_id).collection('uploadedMaterials').document(material_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found: {material_id}"
            )

        return UploadedMaterial(**doc.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get uploaded material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get material: {str(e)}"
        )


@router.delete(
    "/{course_id}/materials/uploads/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete uploaded material",
    description="Delete an uploaded material (file and metadata)."
)
async def delete_uploaded_material(
    course_id: str = Path(..., description="Course ID"),
    material_id: str = Path(..., description="Material ID")
):
    """
    Delete an uploaded material.

    This will:
    1. Delete the file from storage
    2. Delete the metadata from Firestore

    Args:
        course_id: Course ID
        material_id: Material ID
    """
    try:
        from app.services.gcp_service import get_firestore_client
        db = get_firestore_client()

        # Get material metadata
        doc_ref = db.collection('courses').document(course_id).collection('uploadedMaterials').document(material_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found: {material_id}"
            )

        material = UploadedMaterial(**doc.to_dict())

        # Delete file from storage
        file_path = pathlib.Path(material.storagePath)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")

        # Delete metadata from Firestore
        doc_ref.delete()
        logger.info(f"Deleted material metadata: {material_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete uploaded material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete material: {str(e)}"
        )


@router.get(
    "/{course_id}/materials/uploads/{material_id}/text",
    summary="Get extracted text from uploaded material",
    description="Get the extracted text content from an uploaded material."
)
async def get_material_text(
    course_id: str = Path(..., description="Course ID"),
    material_id: str = Path(..., description="Material ID")
):
    """
    Get extracted text from an uploaded material.

    Args:
        course_id: Course ID
        material_id: Material ID

    Returns:
        JSON with extracted text and metadata
    """
    try:
        from app.services.gcp_service import get_firestore_client
        db = get_firestore_client()

        doc_ref = db.collection('courses').document(course_id).collection('uploadedMaterials').document(material_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found: {material_id}"
            )

        material = UploadedMaterial(**doc.to_dict())

        return {
            "material_id": material.id,
            "filename": material.filename,
            "text_extracted": material.textExtracted,
            "text": material.extractedText,
            "text_length": material.textLength,
            "extraction_error": material.extractionError
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get material text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get material text: {str(e)}"
        )


@router.get(
    "/upload-config",
    summary="Get upload configuration",
    description="Get configuration for file uploads (supported types, size limits, etc.)."
)
async def get_upload_config():
    """
    Get upload configuration.

    Returns:
        Configuration for file uploads
    """
    return {
        "max_file_size": MAX_FILE_SIZE,
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
        "supported_extensions": sorted(list(SUPPORTED_EXTENSIONS)),
        "tiers": list(TIER_FOLDERS.keys()),
        "categories": list(CATEGORY_FOLDERS.keys()),
        "tier_folders": TIER_FOLDERS,
        "category_folders": CATEGORY_FOLDERS
    }


# ============================================================================
# Unified Materials Endpoints (Issue #51)
# ============================================================================


class UnifiedMaterialsResponse(BaseModel):
    """Response model for unified materials list."""
    materials: List[CourseMaterial]
    count: int
    stats: Optional[Dict] = None


class BatchProcessRequest(BaseModel):
    """Request model for batch processing."""
    material_ids: Optional[List[str]] = None  # If None, process all
    process_text: bool = True
    process_summary: bool = True


class BatchProcessResponse(BaseModel):
    """Response model for batch processing."""
    processed: int
    errors: int
    results: List[Dict]


@router.get(
    "/{course_id}/unified-materials",
    response_model=UnifiedMaterialsResponse,
    summary="List all course materials (unified)",
    description="Get all materials for a course from the unified collection."
)
async def list_unified_materials(
    course_id: str = Path(..., description="Course ID"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source (scanned/uploaded)"),
    text_extracted: Optional[bool] = Query(None, description="Filter by text extraction status"),
    summary_generated: Optional[bool] = Query(None, description="Filter by summary status"),
    include_stats: bool = Query(False, description="Include material statistics")
):
    """List all materials from the unified collection."""
    try:
        from app.services.course_materials_service import get_course_materials_service

        service = get_course_materials_service()
        materials = service.list_materials(
            course_id=course_id,
            tier=tier,
            category=category,
            source=source,
            text_extracted=text_extracted,
            summary_generated=summary_generated
        )

        stats = None
        if include_stats:
            stats = service.get_materials_stats(course_id)

        return UnifiedMaterialsResponse(
            materials=materials,
            count=len(materials),
            stats=stats
        )

    except Exception as e:
        logger.error(f"Failed to list unified materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list materials: {str(e)}"
        )


@router.get(
    "/{course_id}/unified-materials/stats",
    summary="Get materials statistics",
    description="Get statistics about materials for a course."
)
async def get_materials_stats(
    course_id: str = Path(..., description="Course ID")
):
    """Get statistics about materials for a course."""
    try:
        from app.services.course_materials_service import get_course_materials_service

        service = get_course_materials_service()
        stats = service.get_materials_stats(course_id)
        return stats

    except Exception as e:
        logger.error(f"Failed to get materials stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.get(
    "/{course_id}/unified-materials/{material_id}",
    response_model=CourseMaterial,
    summary="Get a specific material",
    description="Get details of a specific material from the unified collection."
)
async def get_unified_material(
    course_id: str = Path(..., description="Course ID"),
    material_id: str = Path(..., description="Material ID")
):
    """Get a specific material from the unified collection."""
    try:
        from app.services.course_materials_service import get_course_materials_service

        service = get_course_materials_service()
        material = service.get_material(course_id, material_id)

        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found: {material_id}"
            )

        return material

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get unified material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get material: {str(e)}"
        )




@router.post(
    "/{course_id}/unified-materials/{material_id}/extract-text",
    summary="Extract text from a material",
    description="Trigger text extraction for a specific material."
)
async def extract_material_text(
    course_id: str = Path(..., description="Course ID"),
    material_id: str = Path(..., description="Material ID")
):
    """Extract text from a specific material."""
    try:
        from app.services.course_materials_service import get_course_materials_service
        from app.services.text_extractor import extract_text

        service = get_course_materials_service()
        material = service.get_material(course_id, material_id)

        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found: {material_id}"
            )

        # Build full file path with security validation
        file_path = validate_materials_path(material.storagePath)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {material.storagePath}"
            )

        # Extract text
        result = extract_text(file_path)

        if result.success:
            updated = service.update_text_extraction(
                course_id=course_id,
                material_id=material_id,
                extracted_text=result.text,
                text_length=len(result.text)
            )
            return {
                "success": True,
                "material_id": material_id,
                "text_length": len(result.text),
                "preview": result.text[:500] if result.text else ""
            }
        else:
            service.update_text_extraction(
                course_id=course_id,
                material_id=material_id,
                extracted_text="",
                text_length=0,
                error=result.error
            )
            return {
                "success": False,
                "material_id": material_id,
                "error": result.error
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text: {str(e)}"
        )


@router.post(
    "/{course_id}/unified-materials/{material_id}/generate-summary",
    summary="Generate AI summary for a material",
    description="Generate an AI summary for a material that has extracted text."
)
async def generate_material_summary(
    course_id: str = Path(..., description="Course ID"),
    material_id: str = Path(..., description="Material ID")
):
    """Generate AI summary for a specific material."""
    try:
        from app.services.course_materials_service import get_course_materials_service
        from app.services.document_upload_service import generate_document_summary

        service = get_course_materials_service()
        material = service.get_material(course_id, material_id)

        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found: {material_id}"
            )

        if not material.textExtracted or not material.extractedText:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text must be extracted before generating summary"
            )

        # Generate summary
        summary = await generate_document_summary(
            text=material.extractedText,
            filename=material.filename
        )

        if summary:
            service.update_summary(
                course_id=course_id,
                material_id=material_id,
                summary=summary
            )
            return {
                "success": True,
                "material_id": material_id,
                "summary": summary
            }
        else:
            return {
                "success": False,
                "material_id": material_id,
                "error": "Failed to generate summary"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}"
        )


@router.post(
    "/{course_id}/unified-materials/batch-process",
    response_model=BatchProcessResponse,
    summary="Batch process materials",
    description="Extract text and/or generate summaries for multiple materials."
)
async def batch_process_materials(
    course_id: str = Path(..., description="Course ID"),
    request: BatchProcessRequest = None
):
    """Batch process materials for text extraction and summary generation."""
    try:
        from app.services.course_materials_service import get_course_materials_service
        from app.services.text_extractor import extract_text
        from app.services.document_upload_service import generate_document_summary

        service = get_course_materials_service()

        # Get materials to process
        if request and request.material_ids:
            materials = [service.get_material(course_id, mid) for mid in request.material_ids]
            materials = [m for m in materials if m is not None]
        else:
            # Get all materials
            materials = service.list_materials(course_id)

        process_text = request.process_text if request else True
        process_summary = request.process_summary if request else True

        results = []
        processed = 0
        errors = 0

        for material in materials:
            result = {"material_id": material.id, "filename": material.filename}

            # Extract text if needed
            if process_text and not material.textExtracted:
                storage_path = material.storagePath
                logger.debug(f"Processing material: {material.filename}, storagePath: {storage_path}")
                try:
                    # Check if path needs resolution (incomplete path)
                    corrected_path = resolve_incomplete_path(storage_path)
                    if corrected_path:
                        # Validate the corrected path exists before updating Firestore
                        corrected_full_path = (MATERIALS_BASE / corrected_path).resolve()
                        try:
                            corrected_full_path.relative_to(MATERIALS_BASE)
                            if corrected_full_path.exists():
                                # Only update Firestore if corrected path actually exists
                                service.update_storage_path(course_id, material.id, corrected_path)
                                storage_path = corrected_path
                                result["path_corrected"] = True
                                result["corrected_path"] = corrected_path
                                logger.info("Corrected storagePath for %s: %s", material.filename, corrected_path)
                            else:
                                logger.warning("Corrected path does not exist, skipping Firestore update: %s", corrected_full_path)
                        except ValueError:
                            logger.warning("Corrected path outside materials directory: %s", corrected_full_path)

                    # Validate path to prevent path traversal
                    file_path = validate_materials_path(storage_path)
                    logger.debug(f"Full file path: {file_path}")
                    if file_path.exists():
                        extraction = extract_text(file_path)
                        if extraction.success:
                            service.update_text_extraction(
                                course_id=course_id,
                                material_id=material.id,
                                extracted_text=extraction.text,
                                text_length=len(extraction.text)
                            )
                            result["text_extracted"] = True
                            result["text_length"] = len(extraction.text)
                            material.extractedText = extraction.text
                            material.textExtracted = True
                        else:
                            result["text_extracted"] = False
                            result["text_error"] = extraction.error
                            errors += 1
                    else:
                        result["text_extracted"] = False
                        result["text_error"] = f"File not found: {storage_path}"
                        errors += 1
                except HTTPException as e:
                    result["text_extracted"] = False
                    result["text_error"] = f"Invalid path: {e.detail}"
                    errors += 1
            elif material.textExtracted:
                result["text_extracted"] = True
                result["text_skipped"] = "Already extracted"

            # Generate summary if needed
            if process_summary and material.textExtracted and not material.summaryGenerated:
                if material.extractedText:
                    success, summary = await generate_document_summary(
                        extracted_text=material.extractedText,
                        filename=material.filename,
                        tier=material.tier or "course_materials",
                        category=material.category
                    )
                    if success and summary:
                        service.update_summary(
                            course_id=course_id,
                            material_id=material.id,
                            summary=summary
                        )
                        result["summary_generated"] = True
                        result["summary_preview"] = summary[:100] + "..." if len(summary) > 100 else summary
                    else:
                        result["summary_generated"] = False
                        result["summary_error"] = "Failed to generate"
                        errors += 1
            elif material.summaryGenerated:
                result["summary_generated"] = True
                result["summary_skipped"] = "Already generated"

            results.append(result)
            processed += 1

        return BatchProcessResponse(
            processed=processed,
            errors=errors,
            results=results
        )

    except Exception as e:
        import traceback
        logger.error(f"Failed to batch process materials: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch process: {str(e)}"
        )


@router.delete(
    "/{course_id}/unified-materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a material from unified collection",
    description="Delete a material from the unified collection (and optionally the file)."
)
async def delete_unified_material(
    course_id: str = Path(..., description="Course ID"),
    material_id: str = Path(..., description="Material ID"),
    delete_file: bool = Query(False, description="Also delete the physical file")
):
    """Delete a material from the unified collection."""
    try:
        from app.services.course_materials_service import get_course_materials_service

        service = get_course_materials_service()
        material = service.get_material(course_id, material_id)

        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found: {material_id}"
            )

        # Optionally delete the file (with path validation for security)
        if delete_file:
            file_path = validate_materials_path(material.storagePath)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")

        # Delete from unified collection
        service.delete_material(course_id, material_id)

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete unified material: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete material: {str(e)}"
        )


# ========== Anthropic Files API Management ==========


def _validate_course_id(course_id: str) -> str:
    """Validate course_id parameter.

    Args:
        course_id: The course ID to validate

    Returns:
        The validated (stripped) course ID

    Raises:
        HTTPException: If validation fails
    """
    course_id = course_id.strip()
    if not course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course_id: cannot be empty"
        )
    if len(course_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course_id: too long (max 100 characters)"
        )
    # Basic character validation (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course_id: only alphanumeric characters, hyphens, and underscores allowed"
        )
    return course_id


@router.post(
    "/courses/{course_id}/anthropic-files/refresh",
    summary="Refresh Anthropic file uploads for a course",
    description="Upload or re-upload course materials to Anthropic Files API. "
                "Files are automatically uploaded on-demand, but this endpoint "
                "allows proactive refresh before files expire."
)
async def refresh_anthropic_files(
    course_id: str = Path(..., description="Course ID", min_length=1, max_length=100),
    force: bool = Query(False, description="Force re-upload all files, even if not expired")
):
    """Refresh Anthropic file uploads for a course.

    This endpoint uploads course materials to Anthropic's Files API so they
    can be used for AI-powered content generation (quizzes, study guides, etc.).

    Files are automatically uploaded on-demand when needed, but this endpoint
    allows proactive refresh to ensure files are ready before they expire.
    """
    # Validate course_id
    course_id = _validate_course_id(course_id)

    try:
        from app.services.anthropic_file_manager import get_anthropic_file_manager
        from app.services.anthropic_file_manager import (
            AnthropicFileManagerError,
            LocalFileNotFoundError,
            PathTraversalError,
            FileValidationError,
        )

        file_manager = get_anthropic_file_manager()
        results = file_manager.refresh_course_files(course_id, force=force)

        return {
            "course_id": course_id,
            "force": force,
            "results": results
        }

    except (LocalFileNotFoundError, FileValidationError) as e:
        logger.warning(f"File validation error for {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PathTraversalError as e:
        logger.error(f"Path traversal attempt for {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path detected"
        )
    except AnthropicFileManagerError as e:
        logger.error(f"Anthropic file manager error for {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File manager error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error refreshing Anthropic files for {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh files: {str(e)}"
        )


@router.get(
    "/courses/{course_id}/anthropic-files/status",
    summary="Get Anthropic file status for a course",
    description="Check which materials have been uploaded to Anthropic and their expiry status."
)
async def get_anthropic_files_status(
    course_id: str = Path(..., description="Course ID", min_length=1, max_length=100)
):
    """Get Anthropic file upload status for a course.

    Returns information about which materials have been uploaded to Anthropic,
    their file IDs, and when they expire.
    """
    # Validate course_id
    course_id = _validate_course_id(course_id)

    try:
        from app.services.anthropic_file_manager import get_anthropic_file_manager
        from datetime import datetime, timezone

        file_manager = get_anthropic_file_manager()

        # Get materials needing upload
        needing_upload = file_manager.get_materials_needing_upload(course_id)

        # Get all materials to show full status
        if not file_manager.firestore:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firestore not available"
            )

        materials_ref = (
            file_manager.firestore
            .collection("courses")
            .document(course_id)
            .collection("materials")
        )

        # Use pagination to handle large collections with a total limit
        batch_size = 100
        max_materials_limit = 1000  # Prevent loading unlimited materials into memory
        materials_status = []
        now = datetime.now(timezone.utc)
        query = materials_ref.limit(batch_size)
        truncated = False

        while len(materials_status) < max_materials_limit:
            docs = list(query.stream())
            if not docs:
                break

            for doc in docs:
                if len(materials_status) >= max_materials_limit:
                    truncated = True
                    break
                data = doc.to_dict()
                if not data:
                    continue  # Skip materials with no data
                file_id = data.get("anthropicFileId")
                expiry = data.get("anthropicFileExpiry")

                status_info = {
                    "material_id": doc.id,
                    "filename": data.get("filename"),
                    "title": data.get("title"),
                    "tier": data.get("tier"),
                    "has_anthropic_file": bool(file_id),
                    "anthropic_file_id": file_id,
                    "expiry": expiry.isoformat() if expiry else None,
                    "is_expired": expiry < now if expiry else None,
                    "upload_error": data.get("anthropicUploadError")
                }
                materials_status.append(status_info)

            # Get next batch
            if len(docs) < batch_size or truncated:
                break
            query = materials_ref.start_after(docs[-1]).limit(batch_size)

        # Summary counts
        total = len(materials_status)
        uploaded = sum(1 for m in materials_status if m["has_anthropic_file"])
        expired = sum(1 for m in materials_status if m["is_expired"])
        with_errors = sum(1 for m in materials_status if m["upload_error"])

        return {
            "course_id": course_id,
            "summary": {
                "total_materials": total,
                "uploaded_to_anthropic": uploaded,
                "expired": expired,
                "needing_upload": len(needing_upload),
                "with_errors": with_errors,
                "truncated": truncated,
                "max_limit": max_materials_limit if truncated else None
            },
            "materials": materials_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Anthropic files status for {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )