"""API Routes using Anthropic Files API for the LLS Study Portal.

Provides endpoints for AI-powered content generation (quizzes, study guides,
flashcards, etc.) using uploaded course materials.

Supports two modes:
1. **Legacy mode**: Uses topic parameter with hardcoded mappings
2. **Course-aware mode**: Uses course_id to get materials from Firestore

The course-aware mode is activated by providing a course_id parameter.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from app.services.files_api_service import get_files_api_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/files-content",
    tags=["Files API Content Generation"]
)


# ========== Request Models ==========

class FilesQuizRequest(BaseModel):
    """Generate quiz using uploaded files.

    Uses Firestore-based file management with automatic upload to Anthropic.
    A course_id is required to identify which course materials to use.
    """

    course_id: str = Field(
        ...,
        description="Course ID (e.g., 'LLS-2025-2026'). "
                    "Materials are retrieved from Firestore.",
        min_length=1,
        max_length=100
    )
    topic: Optional[str] = Field(
        None,
        description="Optional topic name for context (e.g., 'Constitutional Law'). "
                    "If not provided, defaults to 'Course Materials'."
    )
    week: Optional[int] = Field(
        None,
        ge=1,
        le=52,
        description="Week number to filter materials (1-52)"
    )
    num_questions: int = Field(10, ge=1, le=50)
    difficulty: str = Field("medium", description="easy, medium, hard")


class FilesStudyGuideRequest(BaseModel):
    """Generate study guide from files.

    Supports both legacy mode (topic) and course-aware mode (course_id).
    """

    topic: Optional[str] = Field(
        None,
        description="Topic name. Required if course_id is not provided."
    )
    course_id: Optional[str] = Field(
        None,
        description="Course ID for Firestore lookup."
    )
    weeks: Optional[List[int]] = Field(
        None,
        description="Specific weeks to include (each must be 1-52)"
    )

    @validator('weeks', each_item=True)
    def validate_weeks_range(cls, week):  # noqa: N805
        """Validate each week is within valid range (1-52)."""
        if week < 1 or week > 52:
            raise ValueError(f"Week {week} is invalid. Must be between 1 and 52.")
        return week


class ArticleExplainRequest(BaseModel):
    """Explain article using files."""

    article: str = Field(..., description="Article number (e.g., '6:74')")
    code: str = Field("DCC", description="DCC, GALA, PC, CCP, ECHR")
    course_id: Optional[str] = Field(
        None,
        description="Course ID for context-aware explanation."
    )


class CaseAnalysisRequest(BaseModel):
    """Analyze case using files."""

    case_facts: str = Field(..., min_length=50)
    topic: Optional[str] = Field(
        None,
        description="Topic name. Required if course_id is not provided."
    )
    course_id: Optional[str] = Field(
        None,
        description="Course ID for Firestore lookup."
    )


class FlashcardsRequest(BaseModel):
    """Generate flashcards from files.

    Supports both legacy mode (topic) and course-aware mode (course_id).
    """

    topic: Optional[str] = Field(
        None,
        description="Topic name. Required if course_id is not provided."
    )
    course_id: Optional[str] = Field(
        None,
        description="Course ID for Firestore lookup."
    )
    week: Optional[int] = Field(
        None,
        ge=1,
        le=52,
        description="Week number to filter materials"
    )
    num_cards: int = Field(20, ge=5, le=50)


# ========== Helper Functions ==========

def _validate_week_parameter(week: Optional[int]) -> None:
    """
    Validate week parameter is within valid range.

    Args:
        week: Week number to validate (1-52)

    Raises:
        HTTPException: If week is outside valid range
    """
    if week is not None and (week < 1 or week > 52):
        raise HTTPException(
            400,
            detail="Week number must be between 1 and 52"
        )


def _add_course_context(
    response: dict,
    course_id: Optional[str] = None,
    week: Optional[int] = None,
    weeks: Optional[List[int]] = None
) -> dict:
    """
    Add course context to response dictionary.

    Args:
        response: Response dictionary to augment
        course_id: Optional course ID
        week: Optional single week number
        weeks: Optional list of week numbers

    Returns:
        Response dictionary with course context added
    """
    if course_id:
        response["course_id"] = course_id
    if week is not None:
        response["week"] = week
    if weeks:
        response["weeks"] = weeks
    return response


def _get_file_keys(
    service,
    topic: Optional[str] = None,
    course_id: Optional[str] = None,
    week: Optional[int] = None
) -> List[str]:
    """
    Get file keys based on topic or course_id.

    Args:
        service: FilesAPIService instance
        topic: Topic name (legacy mode)
        course_id: Course ID (course-aware mode)
        week: Optional week number for filtering (1-52)

    Returns:
        List of file keys

    Raises:
        HTTPException: If neither topic nor course_id provided, course not found,
                       or week is outside valid range
    """
    # Validate week parameter
    _validate_week_parameter(week)

    if course_id:
        # Course-aware mode: get files from Firestore
        try:
            return service.get_files_for_course(course_id, week_number=week)
        except ValueError as e:
            logger.warning("Course not found: %s", course_id)
            raise HTTPException(404, detail=str(e)) from e
    elif topic:
        # Legacy mode: use hardcoded topic mappings
        file_keys = service.get_topic_files(topic)
        # Add week-specific lecture if provided
        if week:
            lecture_key = f"lecture_week_{week}"
            if lecture_key not in file_keys:
                file_keys.insert(0, lecture_key)
        return file_keys
    else:
        raise HTTPException(
            400,
            detail="Either 'topic' or 'course_id' must be provided"
        )


# ========== Routes ==========

@router.post("/quiz")
async def generate_quiz_from_files(request: FilesQuizRequest):
    """
    Generate quiz questions from uploaded course materials.

    Uses Anthropic Files API with Firestore-based file management.
    Files are automatically uploaded to Anthropic on-demand.

    **Benefits:**
    - 90% cost savings with automatic caching
    - No manual file management needed
    - Automatic file expiry handling
    - Claude can cite page numbers

    **Example:**
    ```json
    {
        "course_id": "LLS-2025-2026",
        "week": 3,
        "num_questions": 10,
        "difficulty": "medium"
    }
    ```
    """
    try:
        service = get_files_api_service()

        # Determine topic for quiz generation
        topic = request.topic or "Course Materials"

        logger.info(
            "Generating quiz: course=%s, week=%s, questions=%d",
            request.course_id, request.week, request.num_questions
        )

        quiz = await service.generate_quiz_from_course(
            course_id=request.course_id,
            topic=topic,
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            week_number=request.week
        )

        response = {
            "quiz": quiz,
            "course_id": request.course_id,
            "week": request.week,
            "cached": True
        }

        logger.info(
            "Generated quiz for course %s, week %s, %d questions",
            request.course_id, request.week, request.num_questions
        )

        return response

    except HTTPException:
        raise
    except ValueError as e:
        # Course not found or other value errors
        logger.warning("Invalid request for quiz: %s", e)
        raise HTTPException(400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error generating quiz: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.post("/study-guide")
async def generate_study_guide(request: FilesStudyGuideRequest):
    """
    Generate comprehensive study guide from uploaded files.

    Includes:
    - Key concepts
    - Important articles
    - Common mistakes
    - Exam tips
    - Practice scenarios

    **Modes:**
    - **Legacy mode**: Provide `topic` parameter
    - **Course-aware mode**: Provide `course_id` parameter

    **Example (legacy):**
    ```json
    {
        "topic": "Private Law",
        "weeks": [2]
    }
    ```

    **Example (course-aware):**
    ```json
    {
        "course_id": "LLS-2025-2026",
        "weeks": [2, 3]
    }
    ```
    """
    try:
        service = get_files_api_service()

        # Note: weeks are validated by Pydantic @validator

        # Get files (supports both legacy and course-aware modes)
        if request.course_id:
            # Course-aware mode: fetch course data once to avoid N+1 queries
            try:
                if request.weeks:
                    # Use batch method for multiple weeks - single Firestore read
                    file_keys = service.get_files_for_course_weeks(
                        request.course_id,
                        week_numbers=request.weeks
                    )
                else:
                    file_keys = service.get_files_for_course(request.course_id)
            except ValueError as e:
                logger.warning("Course not found: %s", request.course_id)
                raise HTTPException(404, detail=str(e)) from e
        elif request.topic:
            # Legacy mode
            file_keys = service.get_topic_files(request.topic)
            # Add week-specific content
            if request.weeks:
                for week in request.weeks:
                    if week in [3, 4, 6]:
                        file_keys.append(f"lecture_week_{week}")
                    if week in [1, 2]:
                        file_keys.append(f"readings_week_{week}")
        else:
            raise HTTPException(
                400,
                detail="Either 'topic' or 'course_id' must be provided"
            )

        topic = request.topic or "Course Materials"

        guide = await service.generate_study_guide(
            topic=topic,
            file_keys=file_keys
        )

        response = {
            "guide": guide,
            "topic": topic,
            "files_used": file_keys
        }

        # Add course context to response
        _add_course_context(response, course_id=request.course_id, weeks=request.weeks)

        # Log successful generation
        if request.course_id:
            logger.info(
                "Generated study guide for course %s, weeks %s",
                request.course_id, request.weeks
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating study guide: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.post("/explain-article")
async def explain_article(request: ArticleExplainRequest):
    """
    Explain legal article using course materials.

    Uses LLS Reader and other course materials to provide:
    - Full article text
    - Purpose and context
    - Key elements
    - Common applications
    - Related articles
    - Exam tips

    **Example:**
    ```json
    {
        "article": "6:74",
        "code": "DCC"
    }
    ```
    """
    try:
        service = get_files_api_service()

        explanation = await service.explain_article(
            article=request.article,
            code=request.code,
            use_reader=True
        )

        return {
            "article": "Art. %s %s" % (request.article, request.code),
            "explanation": explanation
        }

    except Exception as e:
        logger.error("Error explaining article: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.post("/case-analysis")
async def analyze_case(request: CaseAnalysisRequest):
    """
    Analyze case using course materials.

    Provides step-by-step legal analysis:
    1. Identify legal questions
    2. Applicable law
    3. Systematic analysis
    4. Conclusion

    **Example:**
    ```json
    {
        "case_facts": "A municipality denied a permit without proper hearing...",
        "topic": "Administrative Law"
    }
    ```
    """
    try:
        service = get_files_api_service()

        # Get relevant files
        file_keys = service.get_topic_files(request.topic)

        analysis = await service.generate_case_analysis(
            case_facts=request.case_facts,
            topic=request.topic,
            relevant_files=file_keys
        )

        return {
            "analysis": analysis,
            "topic": request.topic,
            "files_used": file_keys
        }

    except Exception as e:
        logger.error("Error analyzing case: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.post("/flashcards")
async def generate_flashcards(request: FlashcardsRequest):
    """
    Generate flashcards from course materials.

    Creates front/back flashcards with:
    - Article definitions
    - Key legal concepts
    - Important principles

    **Modes:**
    - **Legacy mode**: Provide `topic` parameter
    - **Course-aware mode**: Provide `course_id` parameter

    **Example (legacy):**
    ```json
    {
        "topic": "Criminal Law",
        "num_cards": 20
    }
    ```

    **Example (course-aware):**
    ```json
    {
        "course_id": "LLS-2025-2026",
        "week": 3,
        "num_cards": 20
    }
    ```
    """
    try:
        service = get_files_api_service()

        # Get file keys (supports both legacy and course-aware modes)
        file_keys = _get_file_keys(
            service,
            topic=request.topic,
            course_id=request.course_id,
            week=request.week
        )

        topic = request.topic or "Course Materials"

        flashcards = await service.generate_flashcards(
            topic=topic,
            file_keys=file_keys,
            num_cards=request.num_cards
        )

        response = {
            "flashcards": flashcards,
            "count": len(flashcards),
            "topic": topic
        }

        # Add course context to response
        _add_course_context(response, course_id=request.course_id, week=request.week)

        # Log successful generation
        if request.course_id:
            logger.info(
                "Generated %d flashcards for course %s, week %s",
                len(flashcards), request.course_id, request.week
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating flashcards: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/available-files")
async def list_available_files():
    """
    List all files uploaded to Anthropic Files API.

    Shows:
    - File IDs
    - Filenames
    - Sizes
    - Upload dates
    """
    try:
        service = get_files_api_service()
        files = await service.list_available_files()

        return {
            "files": files,
            "count": len(files),
            "total_size_mb": sum(f["size_mb"] for f in files)
        }

    except Exception as e:
        logger.error("Error listing files: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/topic-files/{topic}")
async def get_topic_files(topic: str):
    """
    Get recommended files for a specific topic.

    Returns which uploaded files are relevant for generating
    content about this topic.
    """
    try:
        service = get_files_api_service()
        file_keys = service.get_topic_files(topic)

        # Get file details
        files_info = []
        for key in file_keys:
            try:
                file_id = service.get_file_id(key)
                files_info.append({
                    "key": key,
                    "file_id": file_id,
                    "filename": service.file_ids[key].get("filename", "")
                })
            except (KeyError, ValueError):
                # Skip files that don't exist in file_ids.json
                logger.warning("File key '%s' not found in file_ids.json", key)
                pass

        return {
            "topic": topic,
            "file_keys": file_keys,
            "files": files_info
        }

    except Exception as e:
        logger.error("Error getting topic files: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/course-files/{course_id}")
async def get_course_files(
    course_id: str,
    week: Optional[int] = None
):
    """
    Get files for a specific course from Firestore.

    Returns which uploaded files are relevant for the course,
    optionally filtered by week number.

    **Example:**
    ```
    GET /api/files-content/course-files/LLS-2025-2026
    GET /api/files-content/course-files/LLS-2025-2026?week=3
    ```
    """
    try:
        service = get_files_api_service()
        file_keys = service.get_files_for_course(course_id, week_number=week)

        # Get file details - use .get() to avoid KeyError
        files_info = []
        for key in file_keys:
            try:
                file_id = service.get_file_id(key)
                file_info = service.file_ids.get(key, {})
                files_info.append({
                    "key": key,
                    "file_id": file_id,
                    "filename": file_info.get("filename", ""),
                    "tier": file_info.get("tier", "unknown")
                })
            except (KeyError, ValueError):
                logger.warning("File key '%s' not found in file_ids.json", key)

        response = {
            "course_id": course_id,
            "file_keys": file_keys,
            "files": files_info,
            "count": len(files_info)
        }

        if week:
            response["week"] = week

        return response

    except ValueError as e:
        logger.warning("Course not found: %s", course_id)
        raise HTTPException(404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting course files: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/status")
async def check_files_api_status():
    """
    Check if Files API is properly configured.

    Verifies:
    - file_ids.json exists
    - Files are accessible
    - API key is set
    """
    try:
        service = get_files_api_service()

        # Check if files are loaded
        files_loaded = len(service.file_ids) > 0

        # Try to list files from API
        try:
            api_files = await service.list_available_files()
            api_accessible = True
            api_file_count = len(api_files)
        except Exception:  # pylint: disable=broad-except
            api_accessible = False
            api_file_count = 0

        status_ok = files_loaded and api_accessible
        return {
            "status": "ok" if status_ok else "error",
            "files_loaded": files_loaded,
            "local_file_count": len(service.file_ids),
            "api_accessible": api_accessible,
            "api_file_count": api_file_count,
            "message": "Files API ready!" if status_ok else "Run upload_files_script.py first"
        }

    except Exception as e:  # pylint: disable=broad-except
        return {
            "status": "error",
            "message": str(e)
        }


# ========== Examples ==========

@router.get("/examples")
async def get_usage_examples():
    """
    Get example requests for Files API endpoints.
    """
    return {
        "quiz": {
            "endpoint": "/api/files-content/quiz",
            "method": "POST",
            "example": {
                "topic": "Administrative Law",
                "week": 3,
                "num_questions": 10,
                "difficulty": "medium"
            }
        },
        "study_guide": {
            "endpoint": "/api/files-content/study-guide",
            "method": "POST",
            "example": {
                "topic": "Private Law",
                "weeks": [2]
            }
        },
        "explain_article": {
            "endpoint": "/api/files-content/explain-article",
            "method": "POST",
            "example": {
                "article": "6:74",
                "code": "DCC"
            }
        },
        "case_analysis": {
            "endpoint": "/api/files-content/case-analysis",
            "method": "POST",
            "example": {
                "case_facts": "Party A sold goods to Party B...",
                "topic": "Private Law"
            }
        },
        "flashcards": {
            "endpoint": "/api/files-content/flashcards",
            "method": "POST",
            "example": {
                "topic": "Criminal Law",
                "num_cards": 20
            }
        }
    }
