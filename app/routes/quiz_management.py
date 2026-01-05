"""API Routes for Quiz Management and Persistence.

Provides endpoints for:
- Listing available quizzes for a course
- Getting a specific quiz
- Creating/generating a new quiz with persistence
- Submitting quiz answers and saving results
- Getting user quiz history

Uses simulated user IDs until authentication is implemented.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query

from app.models.schemas import (
    CreateQuizRequest,
    QuizSubmitRequest,
    StoredQuiz,
    StoredQuizSummary,
    QuizAttemptResult,
    QuizHistoryItem,
)
from app.services.quiz_persistence_service import get_quiz_persistence_service
from app.services.files_api_service import get_files_api_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/quizzes",
    tags=["Quiz Management"]
)




def get_or_create_user_id(user_id_header: Optional[str] = None) -> str:
    """Get user ID from header or generate a simulated one.

    In production, this would come from authentication.
    For now, we accept a header or generate a UUID.

    Note: When no header is provided, a new user ID is generated each time.
    The frontend should persist the user ID in localStorage and send it
    with the X-User-ID header to maintain quiz history across sessions.

    Args:
        user_id_header: Optional X-User-ID header value

    Returns:
        User ID string (either from header or newly generated)
    """
    if user_id_header:
        return user_id_header
    # Generate a simulated user ID (frontend should persist this)
    new_user_id = f"sim-{uuid.uuid4().hex[:12]}"
    logger.warning(
        "No X-User-ID header provided, generating new simulated user ID: %s. "
        "Frontend should persist this ID to maintain quiz history.",
        new_user_id
    )
    return new_user_id


@router.get("/courses/{course_id}")
async def list_course_quizzes(
    course_id: str,
    topic: Optional[str] = Query(None, description="Filter by topic"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    week: Optional[int] = Query(None, ge=1, le=52, description="Filter by week"),
    limit: int = Query(20, ge=1, le=100, description="Max results")
):
    """List available quizzes for a course.

    Returns quiz summaries without full question data.
    Use GET /api/quizzes/courses/{course_id}/{quiz_id} to get full quiz.
    """
    try:
        service = get_quiz_persistence_service()
        quizzes = await service.list_quizzes(
            course_id=course_id,
            topic=topic,
            difficulty=difficulty,
            week_number=week,
            limit=limit
        )

        return {
            "quizzes": quizzes,
            "count": len(quizzes),
            "course_id": course_id
        }

    except Exception as e:
        logger.error("Error listing quizzes: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/courses/{course_id}/{quiz_id}")
async def get_quiz(course_id: str, quiz_id: str):
    """Get a specific quiz with all questions.

    Returns the full quiz including all questions and answers.
    """
    try:
        service = get_quiz_persistence_service()
        quiz = await service.get_quiz(course_id, quiz_id)

        if not quiz:
            raise HTTPException(404, detail=f"Quiz {quiz_id} not found")

        return {"quiz": quiz}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting quiz: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.post("/courses/{course_id}")
async def create_quiz(
    course_id: str,
    request: CreateQuizRequest
):
    """Generate and save a new quiz.

    Generates a quiz using AI from course materials, checks for duplicates,
    and saves to Firestore for future use.

    If a duplicate is detected and allow_duplicate is False, the existing
    quiz is returned instead of generating a new one.
    """
    try:
        persistence = get_quiz_persistence_service()
        files_service = get_files_api_service()

        topic = request.topic or "Course Materials"

        # Generate quiz
        logger.info(
            "Generating quiz for course %s: %d questions, %s difficulty",
            course_id, request.num_questions, request.difficulty
        )

        quiz_data = await files_service.generate_quiz_from_course(
            course_id=course_id,
            topic=topic,
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            week_number=request.week
        )

        questions = quiz_data.get("questions", [])
        if not questions:
            # Log details to help debug quiz generation failures
            logger.error(
                "Quiz generation failed for course %s (topic=%s, difficulty=%s, week=%s): "
                "No questions were generated. This may indicate missing course materials, "
                "API issues, or content that could not be processed.",
                course_id, topic, request.difficulty, request.week
            )
            raise HTTPException(
                status_code=400,
                detail=f"No questions could be generated for course '{course_id}'. "
                       f"Please ensure course materials are available and try again."
            )

        # Check for duplicates
        if not request.allow_duplicate:
            duplicate = await persistence.find_duplicate_quiz(
                course_id=course_id,
                topic=topic,
                difficulty=request.difficulty,
                questions=questions,
                week_number=request.week
            )
            if duplicate:
                logger.info("Returning existing quiz %s", duplicate.get("id"))
                return {
                    "quiz": duplicate,
                    "is_new": False,
                    "message": "Existing quiz returned (duplicate detected)"
                }

        # Save new quiz
        saved_quiz = await persistence.save_quiz(
            course_id=course_id,
            topic=topic,
            difficulty=request.difficulty,
            questions=questions,
            week_number=request.week,
            title=request.title
        )

        return {
            "quiz": saved_quiz,
            "is_new": True,
            "message": "New quiz generated and saved"
        }

    except ValueError as e:
        logger.warning("Invalid request: %s", e)
        raise HTTPException(400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating quiz: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.post("/submit")
async def submit_quiz(
    request: QuizSubmitRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Submit quiz answers and save results.

    Calculates score, saves the result, and returns detailed feedback.

    Args:
        request: Quiz submission with quiz_id, course_id, and answers
        x_user_id: Optional user ID header (simulated if not provided)

    Returns:
        Score, percentage, and per-question results
    """
    try:
        service = get_quiz_persistence_service()
        user_id = request.user_id or get_or_create_user_id(x_user_id)

        # Verify quiz exists using the service layer
        quiz = await service.get_quiz(request.course_id, request.quiz_id)
        if not quiz:
            raise HTTPException(404, detail=f"Quiz {request.quiz_id} not found in course {request.course_id}")

        # Calculate score
        score, total, question_results = await service.calculate_score(
            quiz_id=request.quiz_id,
            course_id=request.course_id,
            answers=request.answers
        )

        # Save result
        result = await service.save_quiz_result(
            quiz_id=request.quiz_id,
            course_id=request.course_id,
            user_id=user_id,
            answers=request.answers,
            score=score,
            total_questions=total,
            time_taken_seconds=request.time_taken_seconds
        )

        return {
            "result_id": result.get("id"),
            "score": score,
            "total_questions": total,
            "percentage": result.get("percentage"),
            "question_results": question_results,
            "user_id": user_id,
            "message": "Quiz submitted successfully"
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("Invalid submission: %s", e)
        raise HTTPException(400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error submitting quiz: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/history/{user_id}")
async def get_quiz_history(
    user_id: str,
    course_id: Optional[str] = Query(None, description="Filter by course"),
    limit: int = Query(20, ge=1, le=100, description="Max results")
):
    """Get a user's quiz history.

    Returns list of past quiz attempts with scores and metadata.
    """
    try:
        service = get_quiz_persistence_service()
        history = await service.get_user_quiz_history(
            user_id=user_id,
            course_id=course_id,
            limit=limit
        )

        return {
            "history": history,
            "count": len(history),
            "user_id": user_id
        }

    except Exception as e:
        logger.error("Error getting quiz history: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/my-history")
async def get_my_quiz_history(
    x_user_id: str = Header(..., alias="X-User-ID"),
    course_id: Optional[str] = Query(None, description="Filter by course"),
    limit: int = Query(20, ge=1, le=100, description="Max results")
):
    """Get current user's quiz history.

    Requires X-User-ID header. Returns list of past quiz attempts.
    """
    try:
        service = get_quiz_persistence_service()
        history = await service.get_user_quiz_history(
            user_id=x_user_id,
            course_id=course_id,
            limit=limit
        )

        return {
            "history": history,
            "count": len(history),
            "user_id": x_user_id
        }

    except Exception as e:
        logger.error("Error getting quiz history: %s", e)
        raise HTTPException(500, detail=str(e)) from e

