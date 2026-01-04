"""AI Tutor API Routes for the LLS Study Portal.

Provides endpoints for AI-powered tutoring and topic discovery.
Supports both legacy mode (hardcoded topics) and course-aware mode
(topics from Firestore via CourseService).
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.anthropic_client import get_ai_tutor_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tutor",
    tags=["AI Tutor"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)

# Default topics for backward compatibility (legacy mode)
DEFAULT_TOPICS = [
    {
        "id": "constitutional",
        "name": "Constitutional Law",
        "description": "Dutch Constitution, separation of powers, judicial review"
    },
    {
        "id": "administrative",
        "name": "Administrative Law",
        "description": "GALA provisions, orders, appeals, legal protection"
    },
    {
        "id": "criminal",
        "name": "Criminal Law",
        "description": "Trial procedures, decision models, defences"
    },
    {
        "id": "private",
        "name": "Private Law",
        "description": "Contract law, damages, breach remedies"
    },
    {
        "id": "international",
        "name": "International Law",
        "description": "ICJ, ECHR, treaties, customary law"
    }
]


@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(request: ChatRequest):
    """
    Send a message to the AI tutor and get a formatted response.

    The AI tutor provides visual, formatted responses with:
    - Color-coded boxes (green tips, yellow warnings, red errors)
    - Article citations with blue badges
    - Step-by-step explanations
    - Structured headers and lists

    **Example Request:**
    ```json
    {
        "message": "Explain Art. 6:74 DCC",
        "context": "Private Law",
        "conversation_history": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello! How can I help?"}
        ]
    }
    ```

    **Example Response:**
    ```json
    {
        "content": "## Article 6:74 DCC - Damages\\n\\n...",
        "status": "success",
        "timestamp": "2026-01-02T19:30:00"
    }
    ```
    """
    try:
        logger.info(
            "AI Tutor request - Context: %s, Message length: %d",
            request.context, len(request.message)
        )

        # Convert Pydantic models to dict for service
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        # Get AI response
        response_content = await get_ai_tutor_response(
            message=request.message,
            context=request.context,
            conversation_history=history
        )

        logger.info("AI Tutor response generated - Length: %d", len(response_content))

        return ChatResponse(
            content=response_content,
            status="success"
        )

    except ValueError as e:
        logger.error("Validation error in AI Tutor: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error("Error in AI Tutor endpoint: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI response. Please try again."
        ) from e


@router.get("/topics")
async def get_topics(
    course_id: Optional[str] = Query(
        None,
        description="Course ID to get topics from (e.g., 'LLS-2025-2026'). "
                    "If not provided, returns default topics."
    )
):
    """
    Get list of available study topics.

    Returns a list of law topics. If course_id is provided, topics are
    retrieved from the course in Firestore. Otherwise, returns default topics.

    **Example Request (default topics):**
    ```
    GET /api/tutor/topics
    ```

    **Example Request (course-specific topics):**
    ```
    GET /api/tutor/topics?course_id=LLS-2025-2026
    ```

    **Example Response:**
    ```json
    {
        "topics": [
            {"id": "constitutional", "name": "Constitutional Law", ...}
        ],
        "course_id": "LLS-2025-2026",
        "status": "success"
    }
    ```
    """
    if course_id:
        try:
            from app.services.files_api_service import get_files_api_service
            service = get_files_api_service()
            topics = service.get_course_topics(course_id)
            return {
                "topics": topics,
                "course_id": course_id,
                "status": "success"
            }
        except ValueError as e:
            logger.warning("Course not found: %s", course_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error("Error getting course topics: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve course topics"
            ) from e

    # Return default topics (backward compatibility)
    return {
        "topics": DEFAULT_TOPICS,
        "status": "success"
    }


@router.get("/examples")
async def get_example_questions():
    """
    Get example questions to ask the AI tutor.
    
    Provides sample questions for each topic area.
    """
    return {
        "examples": [
            {
                "topic": "Constitutional Law",
                "questions": [
                    "Explain Article 120 of the Dutch Constitution",
                    "What is the separation of powers?",
                    "How does judicial review work in the Netherlands?"
                ]
            },
            {
                "topic": "Administrative Law",
                "questions": [
                    "Explain the GALA appeal process",
                    "What is an 'interested party' under GALA?",
                    "What are the grounds for legal protection?"
                ]
            },
            {
                "topic": "Criminal Law",
                "questions": [
                    "Explain the criminal trial procedure",
                    "What is the decision model under Articles 348-350 CCP?",
                    "What are the main criminal defences?"
                ]
            },
            {
                "topic": "Private Law",
                "questions": [
                    "Explain Art. 6:74 DCC on damages",
                    "What are the 4 requirements for a valid contract?",
                    "What remedies exist for breach of contract?"
                ]
            },
            {
                "topic": "International Law",
                "questions": [
                    "What is the role of the ICJ?",
                    "How does the ECHR work?",
                    "What are the requirements for customary international law?"
                ]
            }
        ],
        "status": "success"
    }


# For testing during development
if __name__ == "__main__":
    print("AI Tutor routes module loaded successfully")
    print("Available endpoints:")
    print("  POST /api/tutor/chat")
    print("  GET  /api/tutor/topics")
    print("  GET  /api/tutor/examples")
