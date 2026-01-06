"""AI Tutor API Routes for the LLS Study Portal.

Provides endpoints for AI-powered tutoring and topic discovery.
Supports both legacy mode (hardcoded topics) and course-aware mode
(topics from Firestore via CourseService).

Features:
- Course-aware mode with actual materials from FilesAPIService
- Response caching to reduce API costs
- Week/topic filtering for relevant materials
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_optional_user
from app.models.auth_models import User
from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.models.usage_models import UserContext
from app.services.anthropic_client import get_ai_tutor_response
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Cache settings
CACHE_COLLECTION = "tutor_response_cache"
CACHE_TTL_HOURS = 24  # Cache responses for 24 hours


def _generate_cache_key(course_id: str, context: str, message: str, week: Optional[int]) -> str:
    """Generate a cache key from request parameters.

    Uses full SHA-256 hash (64 chars) to minimize collision risk.
    """
    key_string = f"{course_id}:{context}:{message.lower().strip()}:{week or 'all'}"
    return hashlib.sha256(key_string.encode()).hexdigest()


def _get_cached_response(cache_key: str) -> Optional[str]:
    """Check cache for existing response."""
    try:
        db = get_firestore_client()
        if not db:
            return None

        doc_ref = db.collection(CACHE_COLLECTION).document(cache_key)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        created_at = data.get("created_at")

        # Check TTL
        if created_at:
            # Ensure timezone awareness for Firestore timestamps
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
            if age_hours > CACHE_TTL_HOURS:
                logger.info("Cache expired for key %s (age: %.1f hours)", cache_key, age_hours)
                return None

        logger.info("Cache HIT for tutor response: %s", cache_key)

        # Update hit count (best effort, don't fail on stats update)
        try:
            doc_ref.update({"hit_count": (data.get("hit_count", 0) or 0) + 1})
        except Exception:
            pass

        return data.get("response")

    except Exception as e:
        logger.warning("Error checking cache: %s", e)
        return None


def _cache_response(cache_key: str, response: str, course_id: str, context: str) -> None:
    """Cache a response for future use."""
    try:
        db = get_firestore_client()
        if not db:
            return

        doc_ref = db.collection(CACHE_COLLECTION).document(cache_key)
        doc_ref.set({
            "response": response,
            "course_id": course_id,
            "context": context,
            "created_at": datetime.now(timezone.utc),
            "hit_count": 0
        })
        logger.info("Cached tutor response: %s", cache_key)

    except Exception as e:
        logger.warning("Error caching response: %s", e)


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
async def chat_with_tutor(
    request: ChatRequest,
    course_id: Optional[str] = Query(
        None,
        description="Course ID for course-specific context (e.g., 'LLS-2025-2026')"
    ),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    Send a message to the AI tutor and get a formatted response.

    The AI tutor provides visual, formatted responses with:
    - Color-coded boxes (green tips, yellow warnings, red errors)
    - Article citations with blue badges
    - Step-by-step explanations
    - Structured headers and lists

    **Supports two modes:**
    1. **Legacy mode**: Uses default topics (backward compatible)
    2. **Course-aware mode**: Uses course-specific materials when `course_id` is provided

    **Example Request (legacy mode):**
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

    **Example Request (course-aware mode):**
    ```
    POST /api/tutor/chat?course_id=LLS-2025-2026
    {
        "message": "Explain Art. 6:74 DCC",
        "context": "Private Law"
    }
    ```

    **Example Response:**
    ```json
    {
        "content": "## Article 6:74 DCC - Damages\\n\\n...",
        "status": "success",
        "timestamp": "2026-01-02T19:30:00",
        "course_id": "LLS-2025-2026"
    }
    ```
    """
    try:
        # Support course_id from body (frontend) or query param (API docs)
        effective_course_id = request.course_id or course_id
        week_number = request.week_number

        logger.info(
            "AI Tutor request - Context: %s, Course: %s, Week: %s, Message length: %d",
            request.context, effective_course_id or "default", week_number, len(request.message)
        )

        # Convert Pydantic models to dict for service
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        # Check cache first (only for course-aware single-turn queries)
        # Conversations with history are unique and should not be cached
        materials_content = None
        cache_key = None
        if effective_course_id and not history:
            cache_key = _generate_cache_key(
                effective_course_id, request.context, request.message, week_number
            )
            cached_response = _get_cached_response(cache_key)
            if cached_response:
                return ChatResponse(
                    content=cached_response,
                    status="success",
                    course_id=effective_course_id
                )

        # Load course materials if course_id provided
        enhanced_context = request.context
        if effective_course_id:
            try:
                from app.services.files_api_service import get_files_api_service
                service = get_files_api_service()

                # Get materials with text content
                materials_with_text = await service.get_course_materials_with_text(
                    course_id=effective_course_id,
                    week_number=week_number,
                    limit=3  # Limit to 3 materials to manage context size
                )

                if materials_with_text:
                    materials_content = [
                        {"title": mat.title or mat.filename, "text": text}
                        for mat, text in materials_with_text
                    ]
                    logger.info(
                        "Loaded %d materials for tutor context (course=%s, week=%s)",
                        len(materials_content), effective_course_id, week_number
                    )

                # Enhance context string
                enhanced_context = f"{request.context} (Course: {effective_course_id})"
                if week_number:
                    enhanced_context += f", Week {week_number}"

            except Exception as e:
                logger.warning(
                    "Could not load materials for course %s: %s",
                    effective_course_id, str(e)
                )
                # Continue without materials

        # Build user context for usage tracking
        user_context = None
        if user:
            user_context = UserContext(
                email=user.email,
                user_id=user.user_id,
                course_id=effective_course_id,
            )

        # Get AI response
        response_content = await get_ai_tutor_response(
            message=request.message,
            context=enhanced_context,
            conversation_history=history,
            materials_content=materials_content,
            user_context=user_context,
        )

        logger.info("AI Tutor response generated - Length: %d", len(response_content))

        # Cache the response for future use
        if cache_key and effective_course_id:
            _cache_response(cache_key, response_content, effective_course_id, request.context)

        response_data = {
            "content": response_content,
            "status": "success"
        }

        # Include course_id in response if provided
        if effective_course_id:
            response_data["course_id"] = effective_course_id

        return ChatResponse(**response_data)

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
async def get_example_questions(
    course_id: Optional[str] = Query(
        None,
        description="Course ID to get course-specific examples"
    )
):
    """
    Get example questions to ask the AI tutor.

    Provides sample questions for each topic area. If course_id is provided,
    generates examples based on course topics.

    **Example Request (default):**
    ```
    GET /api/tutor/examples
    ```

    **Example Request (course-specific):**
    ```
    GET /api/tutor/examples?course_id=LLS-2025-2026
    ```
    """
    # If course_id provided, try to get course-specific examples
    if course_id:
        try:
            from app.services.files_api_service import get_files_api_service
            service = get_files_api_service()

            topics = service.get_course_topics(course_id)

            # Generate examples based on course topics
            examples = []
            for topic in topics[:5]:  # Limit to first 5 topics
                examples.append({
                    "topic": topic["name"],
                    "week": topic.get("week"),
                    "questions": [
                        f"Explain the key concepts from {topic['name']}",
                        f"What are the main legal principles in {topic['name']}?",
                        f"Can you provide an example case for {topic['name']}?"
                    ]
                })

            return {
                "examples": examples,
                "course_id": course_id,
                "status": "success"
            }
        except Exception as e:
            logger.warning("Could not get course-specific examples for course %s: %s", course_id, str(e))
            # Fall through to default examples

    # Default examples (backward compatibility)
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


@router.get("/course-info")
async def get_course_info(
    course_id: str = Query(..., description="Course ID (e.g., 'LLS-2025-2026')")
):
    """
    Get comprehensive course information for AI tutor context.

    Returns course details including topics, weeks, and available materials.
    This helps the AI tutor provide course-specific assistance.

    **Example Request:**
    ```
    GET /api/tutor/course-info?course_id=LLS-2025-2026
    ```

    **Example Response:**
    ```json
    {
        "course_id": "LLS-2025-2026",
        "name": "Law & Legal Skills",
        "topics": [...],
        "weeks": [...],
        "materials_count": 45,
        "status": "success"
    }
    ```
    """
    try:
        from app.services.files_api_service import get_files_api_service
        from app.services.course_service import get_course_service

        files_service = get_files_api_service()
        course_service = get_course_service()

        # Get course details
        course = course_service.get_course(course_id, include_weeks=True)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        # Get topics
        topics = files_service.get_course_topics(course_id)

        # Get week summaries
        weeks = []
        for week in course.weeks or []:
            weeks.append({
                "number": week.weekNumber,
                "title": week.title,
                "topics": week.topics or [],
                "materials_count": len(week.materials) if week.materials else 0
            })

        # Count total materials
        total_materials = sum(w["materials_count"] for w in weeks)

        return {
            "course_id": course_id,
            "name": course.name,
            "description": course.description,
            "topics": topics,
            "weeks": weeks,
            "materials_count": total_materials,
            "active": course.active,
            "status": "success"
        }

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except ValueError as e:
        logger.warning("Course not found: %s", course_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error("Error getting course info: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve course information"
        ) from e


# For testing during development
if __name__ == "__main__":
    print("AI Tutor routes module loaded successfully")
    print("Available endpoints:")
    print("  POST /api/tutor/chat")
    print("  GET  /api/tutor/topics")
    print("  GET  /api/tutor/examples")
    print("  GET  /api/tutor/course-info")
