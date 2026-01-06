"""AI Assessment API Routes for the LLS Study Portal.

Provides endpoints for:
- Legacy assessment (quick answer grading)
- Essay question generation with persistence
- Essay answer submission and AI evaluation
- Assessment history and retakes
"""

import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status

from app.dependencies.auth import get_optional_user
from app.models.auth_models import User
from app.models.schemas import (
    AssessmentRequest,
    AssessmentResponse,
    ErrorResponse,
    GenerateEssayQuestionRequest,
    EssayQuestion,
    SubmitEssayAnswerRequest,
    EssayEvaluationResponse,
    EssayAssessmentSummary,
    EssayAssessmentHistoryItem,
)
from app.models.usage_models import UserContext
from app.services.anthropic_client import (
    get_assessment_response,
    generate_essay_question,
    evaluate_essay_answer,
)
from app.services.assessment_persistence_service import get_assessment_persistence_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/assessment",
    tags=["AI Assessment"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


def get_or_create_user_id(user_id_header: Optional[str] = None) -> str:
    """Get user ID from header or generate a simulated one."""
    if user_id_header:
        return user_id_header
    new_user_id = f"sim-{uuid.uuid4().hex[:12]}"
    logger.warning(
        "No X-User-ID header provided, generating new simulated user ID: %s",
        new_user_id
    )
    return new_user_id


def extract_grade(feedback: str) -> int:
    """
    Extract numeric grade from AI feedback.

    Args:
        feedback: AI-generated feedback text

    Returns:
        Grade as integer (0-10), or None if not found
    """
    # Look for patterns like "GRADE: 7/10" or "Grade: 8/10"
    grade_patterns = [
        r'GRADE:\s*(\d+)/10',
        r'Grade:\s*(\d+)/10',
        r'##\s*GRADE:\s*(\d+)/10',
        r'Score:\s*(\d+)/10'
    ]

    for pattern in grade_patterns:
        match = re.search(pattern, feedback, re.IGNORECASE)
        if match:
            extracted_grade = int(match.group(1))
            if 0 <= extracted_grade <= 10:
                return extracted_grade

    return None


@router.post("/assess", response_model=AssessmentResponse)
async def assess_answer(
    request: AssessmentRequest,
    user: Optional[User] = Depends(get_optional_user),
):
    """
    Assess and grade a student's answer using AI.

    The AI provides:
    - A grade out of 10
    - Detailed strengths and weaknesses
    - Specific corrections with article citations
    - Step-by-step improvement suggestions
    - Key takeaways for exam preparation

    **Grading Rubric:**
    - 9-10: Excellent (complete, accurate, well-structured)
    - 7-8: Good (mostly correct, minor errors)
    - 5-6: Satisfactory (basic understanding, some gaps)
    - 3-4: Poor (significant errors)
    - 0-2: Fail (fundamental misunderstanding)

    **Example Request:**
    ```json
    {
        "topic": "Private Law",
        "question": "What are the requirements for a valid contract?",
        "answer": "A contract needs agreement between parties."
    }
    ```

    **Example Response:**
    ```json
    {
        "feedback": "## GRADE: 5/10\\n\\n### Overall Assessment\\n...",
        "grade": 5,
        "status": "success",
        "timestamp": "2026-01-02T19:30:00"
    }
    ```
    """
    try:
        logger.info(
            "Assessment request - Topic: %s, Answer length: %d",
            request.topic, len(request.answer)
        )

        # Build user context for usage tracking
        user_context = None
        if user:
            user_context = UserContext(
                email=user.email,
                user_id=user.user_id,
            )

        # Get AI assessment
        feedback = await get_assessment_response(
            topic=request.topic,
            question=request.question,
            answer=request.answer,
            user_context=user_context,
        )

        # Extract grade from feedback
        result_grade = extract_grade(feedback)

        if result_grade is None:
            logger.warning("Could not extract grade from AI feedback")
        else:
            logger.info("Assessment complete - Grade: %d/10", result_grade)

        return AssessmentResponse(
            feedback=feedback,
            grade=result_grade,
            status="success"
        )

    except ValueError as e:
        logger.error("Validation error in assessment: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error("Error in assessment endpoint: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate assessment. Please try again."
        ) from e


@router.get("/rubric")
async def get_grading_rubric():
    """
    Get the grading rubric used for assessments.

    Returns detailed criteria for each grade level.
    """
    return {
        "rubric": {
            "9-10": {
                "label": "Excellent",
                "criteria": [
                    "Complete and accurate answer",
                    "Well-structured and clear",
                    "Correct article citations",
                    "Demonstrates deep understanding",
                    "Uses proper legal terminology"
                ]
            },
            "7-8": {
                "label": "Good",
                "criteria": [
                    "Mostly correct",
                    "Minor errors or omissions",
                    "Could be more detailed",
                    "Good structure",
                    "Basic article citations present"
                ]
            },
            "5-6": {
                "label": "Satisfactory",
                "criteria": [
                    "Basic understanding shown",
                    "Missing some key elements",
                    "Some errors present",
                    "Limited article citations",
                    "Could be better structured"
                ]
            },
            "3-4": {
                "label": "Poor",
                "criteria": [
                    "Significant errors",
                    "Missing crucial information",
                    "Weak structure",
                    "Few or no article citations",
                    "Shows misunderstanding"
                ]
            },
            "0-2": {
                "label": "Fail",
                "criteria": [
                    "Fundamental misunderstanding",
                    "Mostly incorrect",
                    "No proper structure",
                    "No article citations",
                    "Does not address the question"
                ]
            }
        },
        "topics": [
            "Constitutional Law",
            "Administrative Law",
            "Criminal Law",
            "Private Law",
            "International Law"
        ],
        "status": "success"
    }


@router.get("/sample-answers")
async def get_sample_answers():
    """
    Get sample answers for different topics with expected grades.

    Useful for understanding what different grade levels look like.
    """
    return {
        "samples": [
            {
                "topic": "Private Law",
                "question": "What are the requirements for a valid contract?",
                "answers": [
                    {
                        "grade": 9,
                        "text": (
                            "A valid contract requires four elements under Dutch law: "
                            "(1) Capacity (Art. 3:32 DCC) - parties must have legal capacity; "
                            "(2) Consensus (Art. 3:33 DCC) - meeting of the minds; "
                            "(3) Permissible content (Art. 3:40 DCC) - must not violate law or "
                            "morality; (4) Determinability (Art. 6:227 DCC) - content must be "
                            "sufficiently certain. All four must be present for a valid contract."
                        )
                    },
                    {
                        "grade": 6,
                        "text": (
                            "A contract needs agreement between parties (consensus), they must "
                            "be able to make contracts (capacity), the content must be legal, "
                            "and it must be clear what the contract is about. These are the "
                            "four requirements."
                        )
                    },
                    {
                        "grade": 3,
                        "text": (
                            "A contract requires that both parties agree to something and "
                            "sign the document."
                        )
                    }
                ]
            },
            {
                "topic": "Criminal Law",
                "question": "What is the purpose of the decision model in Arts. 348-350 CCP?",
                "answers": [
                    {
                        "grade": 9,
                        "text": (
                            "The decision model in Articles 348-350 CCP provides a structured "
                            "framework for criminal courts to make decisions. It ensures "
                            "systematic consideration of: whether the indictment can be proven "
                            "(factual determination), whether the proven facts constitute a "
                            "criminal offense (legal qualification), whether the accused is "
                            "punishable (culpability), and what sanction should be imposed. "
                            "This prevents arbitrary decisions and ensures thorough legal "
                            "reasoning."
                        )
                    },
                    {
                        "grade": 5,
                        "text": (
                            "The decision model helps judges decide criminal cases by looking "
                            "at whether the facts are proven, if it's a crime, and what "
                            "punishment to give."
                        )
                    }
                ]
            }
        ],
        "status": "success"
    }


# ============================================================================
# Essay Assessment Endpoints (New)
# ============================================================================


@router.post("/essay/generate")
async def generate_essay_assessment(
    request: GenerateEssayQuestionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Generate a new essay question for a topic.

    Creates an essay-style question similar to those seen on law exams.
    The question is saved to the database and can be answered later.

    Questions are designed to require 3-7 paragraph answers.
    """
    try:
        user_id = get_or_create_user_id(x_user_id)
        topic = request.topic or "Law & Legal Skills"

        logger.info(
            "Generating essay question - Course: %s, Topic: %s",
            request.course_id, topic
        )

        # Generate question using AI
        question_data = await generate_essay_question(topic=topic)

        # Save assessment to database
        persistence = get_assessment_persistence_service()
        assessment = await persistence.save_assessment(
            course_id=request.course_id,
            user_id=user_id,
            question=question_data.get("question", ""),
            topic=question_data.get("topic", topic),
            week_number=request.week_number,
            expected_paragraphs="3-7",
            key_concepts=question_data.get("key_concepts", [])
        )

        return {
            "assessment_id": assessment.get("id"),
            "question": question_data.get("question"),
            "topic": question_data.get("topic", topic),
            "expected_paragraphs": "3-7",
            "key_concepts": question_data.get("key_concepts", []),
            "guidance": question_data.get("guidance"),
            "status": "success"
        }

    except Exception as e:
        logger.error("Error generating essay question: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate essay question. Please try again."
        ) from e


@router.post("/essay/submit")
async def submit_essay_answer(
    request: SubmitEssayAnswerRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Submit an essay answer for evaluation.

    The AI evaluates the answer based on:
    - Accuracy of legal knowledge
    - Quality of legal reasoning
    - Use of article citations
    - Structure and organization
    - Completeness

    Returns a grade (1-10) with detailed feedback.
    """
    try:
        user_id = get_or_create_user_id(x_user_id)

        logger.info(
            "Essay submission - Assessment: %s, Answer length: %d",
            request.assessment_id, len(request.answer)
        )

        persistence = get_assessment_persistence_service()

        # Get the assessment details
        assessment = await persistence.get_assessment(
            request.course_id,
            request.assessment_id
        )

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment {request.assessment_id} not found"
            )

        # Evaluate the answer using AI
        evaluation = await evaluate_essay_answer(
            question=assessment.get("question", ""),
            answer=request.answer,
            topic=assessment.get("topic", ""),
            key_concepts=assessment.get("keyConcepts", [])
        )

        # Save the attempt
        attempt = await persistence.save_attempt(
            assessment_id=request.assessment_id,
            course_id=request.course_id,
            user_id=user_id,
            answer=request.answer,
            grade=evaluation.get("grade", 5),
            feedback=evaluation.get("feedback", ""),
            strengths=evaluation.get("strengths", []),
            improvements=evaluation.get("improvements", [])
        )

        return EssayEvaluationResponse(
            attempt_id=attempt.get("id"),
            assessment_id=request.assessment_id,
            grade=evaluation.get("grade", 5),
            feedback=evaluation.get("feedback", ""),
            strengths=evaluation.get("strengths", []),
            improvements=evaluation.get("improvements", []),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error evaluating essay: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate essay. Please try again."
        ) from e


@router.get("/essay/courses/{course_id}")
async def list_essay_assessments(
    course_id: str,
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    List essay assessments for a course.

    Returns assessments with attempt counts and grades.
    Can optionally filter to show only the current user's assessments.
    """
    try:
        user_id = get_or_create_user_id(x_user_id) if x_user_id else None
        persistence = get_assessment_persistence_service()

        assessments = await persistence.list_assessments(
            course_id=course_id,
            user_id=user_id,
            topic=topic,
            limit=limit
        )

        return {
            "assessments": assessments,
            "count": len(assessments),
            "course_id": course_id
        }

    except Exception as e:
        logger.error("Error listing assessments: %s", str(e))
        raise HTTPException(500, detail=str(e)) from e


@router.get("/essay/courses/{course_id}/{assessment_id}")
async def get_essay_assessment(
    course_id: str,
    assessment_id: str,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """
    Get a specific essay assessment with all details.

    Returns the question, topic, and all previous attempts.
    Users can only view their own assessments.
    """
    try:
        persistence = get_assessment_persistence_service()
        assessment = await persistence.get_assessment(course_id, assessment_id)

        if not assessment:
            raise HTTPException(404, detail=f"Assessment {assessment_id} not found")

        # Authorization check: users can only view their own assessments
        if assessment.get("userId") != x_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this assessment"
            )

        # Get attempts only for this user
        attempts = await persistence.get_assessment_attempts(
            course_id, assessment_id, user_id=x_user_id
        )

        return {
            "assessment": assessment,
            "attempts": attempts,
            "attempt_count": len(attempts)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting assessment: %s", str(e))
        raise HTTPException(500, detail=str(e)) from e


@router.get("/essay/history/{user_id}")
async def get_essay_history(
    user_id: str,
    course_id: Optional[str] = Query(None, description="Filter by course"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """
    Get a user's essay assessment history.

    Returns list of past essay attempts with grades and timestamps.
    Users can only view their own history.
    """
    try:
        # Authorization check: users can only view their own history
        if user_id != x_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this user's history"
            )

        persistence = get_assessment_persistence_service()
        history = await persistence.get_user_assessment_history(
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
        logger.error("Error getting assessment history: %s", str(e))
        raise HTTPException(500, detail=str(e)) from e


@router.get("/essay/my-history")
async def get_my_essay_history(
    x_user_id: str = Header(..., alias="X-User-ID"),
    course_id: Optional[str] = Query(None, description="Filter by course"),
    limit: int = Query(20, ge=1, le=100, description="Max results")
):
    """
    Get current user's essay assessment history.

    Requires X-User-ID header. Returns list of past essay attempts.
    """
    try:
        persistence = get_assessment_persistence_service()
        history = await persistence.get_user_assessment_history(
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
        logger.error("Error getting assessment history: %s", str(e))
        raise HTTPException(500, detail=str(e)) from e


@router.get("/essay/attempt/{attempt_id}")
async def get_essay_attempt(
    attempt_id: str,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """
    Get details of a specific essay attempt.

    Returns the answer, grade, feedback, and all evaluation details.
    Users can only view their own attempts.
    """
    try:
        persistence = get_assessment_persistence_service()
        attempt = await persistence.get_attempt(attempt_id)

        if not attempt:
            raise HTTPException(404, detail=f"Attempt {attempt_id} not found")

        # Authorization check: users can only view their own attempts
        if attempt.get("userId") != x_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this attempt"
            )

        return {"attempt": attempt}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting attempt: %s", str(e))
        raise HTTPException(500, detail=str(e)) from e


# For testing during development
if __name__ == "__main__":
    # Test grade extraction
    TEST_FEEDBACK = """## GRADE: 7/10

    ### Overall Assessment
    This is a good answer but could be improved.
    """

    test_grade = extract_grade(TEST_FEEDBACK)
    print("Extracted grade: %d" % test_grade)

    print("\nAssessment routes module loaded successfully")
    print("Available endpoints:")
    print("  POST /api/assessment/assess")
    print("  GET  /api/assessment/rubric")
    print("  GET  /api/assessment/sample-answers")
    print("  POST /api/assessment/essay/generate")
    print("  POST /api/assessment/essay/submit")
    print("  GET  /api/assessment/essay/courses/{course_id}")
    print("  GET  /api/assessment/essay/courses/{course_id}/{assessment_id}")
    print("  GET  /api/assessment/essay/history/{user_id}")
    print("  GET  /api/assessment/essay/my-history")
    print("  GET  /api/assessment/essay/attempt/{attempt_id}")
