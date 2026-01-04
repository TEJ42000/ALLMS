"""Admin API Routes for Course Management.

Provides CRUD endpoints for managing courses, weeks, and legal skills.
These endpoints are intended for administrative use only.

Note: Authentication middleware will be added in Phase 5.
See Issue #29 for the implementation plan.
"""

import logging
import pathlib
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
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
    UploadedMaterial,
)
from app.services.course_service import get_course_service
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


def validate_materials_path(file_path: str) -> pathlib.Path:
    """
    Validate and resolve a file path within the Materials directory.

    This function prevents path traversal attacks by ensuring the resolved
    path is within the Materials directory.

    Args:
        file_path: Relative path within Materials directory

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
    structured course information including weeks, readings, and lecturers.

    The extracted data can be reviewed before creating/updating a course.
    Also includes raw text and source information for storage with the course.
    """
    try:
        from app.services.syllabus_parser import extract_text_from_folder
        from app.services.syllabus_extractor import extract_course_data

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

        # Use AI to extract structured data
        logger.info("Extracting course data with AI...")
        extracted = await extract_course_data(raw_text)

        # Add materialSubjects derived from syllabus folder
        if subject:
            extracted["materialSubjects"] = [subject]

        # Add raw text and source info for storage
        extracted["rawText"] = raw_text
        extracted["sourceFolder"] = source_folder
        extracted["sourceFiles"] = source_files

        return ImportSyllabusResponse(
            success=True,
            extracted_data=ExtractedCourseData(**extracted),
            message=f"Successfully extracted course data from {len(source_files)} file(s)"
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
