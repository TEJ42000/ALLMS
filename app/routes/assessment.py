"""AI Assessment API Routes for the LLS Study Portal."""

import logging
import re

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import AssessmentRequest, AssessmentResponse, ErrorResponse
from app.services.anthropic_client import get_assessment_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/assessment",
    tags=["AI Assessment"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


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
async def assess_answer(request: AssessmentRequest):
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

        # Get AI assessment
        feedback = await get_assessment_response(
            topic=request.topic,
            question=request.question,
            answer=request.answer
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
