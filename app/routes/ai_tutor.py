# app/routes/ai_tutor.py - AI Tutor API Routes

from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.anthropic_client import get_ai_tutor_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tutor",
    tags=["AI Tutor"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


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
        logger.info(f"AI Tutor request - Context: {request.context}, Message length: {len(request.message)}")
        
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
        
        logger.info(f"AI Tutor response generated - Length: {len(response_content)}")
        
        return ChatResponse(
            content=response_content,
            status="success"
        )
        
    except ValueError as e:
        logger.error(f"Validation error in AI Tutor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in AI Tutor endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI response. Please try again."
        )


@router.get("/topics")
async def get_topics():
    """
    Get list of available study topics.
    
    Returns a list of law topics covered by the LLS course.
    """
    return {
        "topics": [
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
        ],
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
