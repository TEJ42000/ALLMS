"""API Routes using Anthropic Files API for the LLS Study Portal."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.files_api_service import get_files_api_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/files-content",
    tags=["Files API Content Generation"]
)


# ========== Request Models ==========

class FilesQuizRequest(BaseModel):
    """Generate quiz using uploaded files."""

    topic: str = Field(
        ..., description="Constitutional, Administrative, Criminal, Private, or International Law"
    )
    week: Optional[int] = Field(None, description="Week number (3, 4, or 6)")
    num_questions: int = Field(10, ge=1, le=50)
    difficulty: str = Field("medium", description="easy, medium, hard")


class FilesStudyGuideRequest(BaseModel):
    """Generate study guide from files."""

    topic: str
    weeks: Optional[List[int]] = Field(None, description="Specific weeks to include")


class ArticleExplainRequest(BaseModel):
    """Explain article using files."""

    article: str = Field(..., description="Article number (e.g., '6:74')")
    code: str = Field("DCC", description="DCC, GALA, PC, CCP, ECHR")


class CaseAnalysisRequest(BaseModel):
    """Analyze case using files."""

    case_facts: str = Field(..., min_length=50)
    topic: str


class FlashcardsRequest(BaseModel):
    """Generate flashcards from files."""

    topic: str
    num_cards: int = Field(20, ge=5, le=50)


# ========== Routes ==========

@router.post("/quiz")
async def generate_quiz_from_files(request: FilesQuizRequest):
    """
    Generate quiz questions from uploaded course materials.

    Uses Anthropic Files API - automatically references your uploaded PDFs!

    **Benefits:**
    - 90% cost savings with automatic caching
    - No file re-upload needed
    - Claude can cite page numbers

    **Example:**
    ```json
    {
        "topic": "Administrative Law",
        "week": 3,
        "num_questions": 10,
        "difficulty": "medium"
    }
    ```
    """
    try:
        service = get_files_api_service()

        # Get file keys for topic and week
        file_keys = service.get_topic_files(request.topic)

        # Add week-specific lecture if provided
        if request.week:
            lecture_key = "lecture_week_%d" % request.week
            if lecture_key not in file_keys:
                file_keys.insert(0, lecture_key)

        quiz = await service.generate_quiz_from_files(
            file_keys=file_keys,
            topic=request.topic,
            num_questions=request.num_questions,
            difficulty=request.difficulty
        )

        return {
            "quiz": quiz,
            "files_used": file_keys,
            "cached": True  # Files API auto-caches
        }

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

    **Example:**
    ```json
    {
        "topic": "Private Law",
        "weeks": [2]
    }
    ```
    """
    try:
        service = get_files_api_service()

        # Get files for topic
        file_keys = service.get_topic_files(request.topic)

        # Add week-specific content
        if request.weeks:
            for week in request.weeks:
                if week in [3, 4, 6]:
                    file_keys.append("lecture_week_%d" % week)
                if week in [1, 2]:
                    file_keys.append("readings_week_%d" % week)

        guide = await service.generate_study_guide(
            topic=request.topic,
            file_keys=file_keys
        )

        return {
            "guide": guide,
            "topic": request.topic,
            "files_used": file_keys
        }

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

    **Example:**
    ```json
    {
        "topic": "Criminal Law",
        "num_cards": 20
    }
    ```
    """
    try:
        service = get_files_api_service()

        file_keys = service.get_topic_files(request.topic)

        flashcards = await service.generate_flashcards(
            topic=request.topic,
            file_keys=file_keys,
            num_cards=request.num_cards
        )

        return {
            "flashcards": flashcards,
            "count": len(flashcards),
            "topic": request.topic
        }

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
