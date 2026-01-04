"""Pydantic Models for API Requests/Responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


# ============================================================================
# AI Tutor Models
# ============================================================================

class ConversationMessage(BaseModel):
    """Single message in conversation history."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for AI tutor chat."""

    message: str = Field(..., min_length=1, max_length=5000, description="User's message")
    context: str = Field(default="Law & Legal Skills", description="Subject area context")
    conversation_history: Optional[List[ConversationMessage]] = Field(
        default=None, description="Previous conversation"
    )

    @validator('message')
    def validate_message(cls, v):  # noqa: N805
        """Validate that message is not empty."""
        if len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for AI tutor chat."""

    content: str = Field(..., description="AI-generated response")
    status: str = Field(default="success", description="Response status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


# ============================================================================
# Assessment Models
# ============================================================================

class AssessmentRequest(BaseModel):
    """Request model for answer assessment."""

    topic: str = Field(
        ..., description="Subject area (e.g., 'Private Law', 'Criminal Law')"
    )
    question: Optional[str] = Field(default=None, description="Optional question/prompt")
    answer: str = Field(
        ..., min_length=10, max_length=10000, description="Student's answer"
    )

    @validator('answer')
    def validate_answer(cls, v):  # noqa: N805
        """Validate that answer has minimum length."""
        if len(v.strip()) < 10:
            raise ValueError('Answer must be at least 10 characters')
        return v.strip()

    @validator('topic')
    def validate_topic(cls, v):  # noqa: N805
        """Validate that topic is one of the allowed values.

        Note: These are the default topics for backward compatibility.
        Course-specific topics can be retrieved from Firestore via
        the /api/tutor/topics?course_id=... endpoint.
        """
        # Default topics for backward compatibility
        valid_topics = [
            "Constitutional Law",
            "Administrative Law",
            "Criminal Law",
            "Private Law",
            "International Law"
        ]
        if v not in valid_topics:
            raise ValueError(f'Topic must be one of: {", ".join(valid_topics)}')
        return v


class AssessmentResponse(BaseModel):
    """Response model for answer assessment."""

    feedback: str = Field(..., description="AI-generated detailed feedback")
    grade: Optional[int] = Field(default=None, ge=0, le=10, description="Grade out of 10")
    status: str = Field(default="success", description="Response status")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )


# ============================================================================
# Practice & Quiz Models
# ============================================================================

class QuizQuestion(BaseModel):
    """Model for a quiz question."""

    id: str = Field(..., description="Question ID")
    topic: str = Field(..., description="Subject area")
    question: str = Field(..., description="Question text")
    options: List[str] = Field(..., min_items=2, max_items=6, description="Answer options")
    correct_answer: int = Field(..., ge=0, description="Index of correct answer")
    explanation: str = Field(..., description="Explanation of correct answer")


class QuizSubmission(BaseModel):
    """Model for quiz answer submission."""

    question_id: str = Field(..., description="Question ID")
    user_answer: int = Field(..., ge=0, description="Index of user's selected answer")


class QuizResult(BaseModel):
    """Model for quiz result."""

    correct: bool = Field(..., description="Whether answer was correct")
    user_answer: int = Field(..., description="Index of user's answer")
    correct_answer: int = Field(..., description="Index of correct answer")
    explanation: str = Field(..., description="Explanation")
    status: str = Field(default="success", description="Result status")


# ============================================================================
# User Progress Models (Optional - for database integration)
# ============================================================================

class UserProgress(BaseModel):
    """Model for tracking user progress."""

    user_id: str = Field(..., description="User identifier")
    practice_questions_completed: int = Field(
        default=0, description="Number of practice questions done"
    )
    mock_exams_taken: int = Field(default=0, description="Number of mock exams taken")
    average_score: Optional[float] = Field(default=None, description="Average quiz score")
    topics_studied: List[str] = Field(default_factory=list, description="Topics studied")
    last_active: datetime = Field(
        default_factory=datetime.now, description="Last activity timestamp"
    )


class ProgressUpdate(BaseModel):
    """Model for updating user progress."""

    practice_questions_completed: Optional[int] = None
    mock_exams_taken: Optional[int] = None
    average_score: Optional[float] = None
    topics_studied: Optional[List[str]] = None


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(..., description="Error message")
    status: str = Field(default="error", description="Error status")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )


class ValidationError(BaseModel):
    """Validation error details."""

    loc: List[str] = Field(..., description="Location of error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example: Create a chat request
    chat_req = ChatRequest(
        message="Explain Art. 6:74 DCC",
        context="Private Law"
    )
    print("Chat Request:")
    print(chat_req.json(indent=2))
    print()

    # Example: Create an assessment request
    assessment_req = AssessmentRequest(
        topic="Private Law",
        question="What are the requirements for a valid contract?",
        answer="A contract requires capacity, consensus, permissible content, and determinability."
    )
    print("Assessment Request:")
    print(assessment_req.json(indent=2))
    print()

    # Example: Create a chat response
    chat_resp = ChatResponse(
        content="## Article 6:74 DCC - Damages\n\nThis article establishes..."
    )
    print("Chat Response:")
    print(chat_resp.json(indent=2))
