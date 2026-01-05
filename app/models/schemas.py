"""Pydantic Models for API Requests/Responses."""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


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

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate that message is not empty."""
        if len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for AI tutor chat."""

    content: str = Field(..., description="AI-generated response")
    status: str = Field(default="success", description="Response status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    course_id: Optional[str] = Field(None, description="Course ID if course-aware mode was used")


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

    @field_validator('answer')
    @classmethod
    def validate_answer(cls, v: str) -> str:
        """Validate that answer has minimum length."""
        if len(v.strip()) < 10:
            raise ValueError('Answer must be at least 10 characters')
        return v.strip()

    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v: str) -> str:
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
# Stored Quiz Models (Firestore Persistence)
# ============================================================================

class StoredQuizQuestion(BaseModel):
    """Model for a question in a stored quiz."""

    question: str = Field(..., description="Question text")
    options: List[str] = Field(..., min_items=2, max_items=6, description="Answer options")
    correct_index: int = Field(..., ge=0, description="Index of correct answer")
    explanation: str = Field(..., description="Explanation of correct answer")
    difficulty: Optional[str] = Field(None, description="Question difficulty")
    articles: Optional[List[str]] = Field(default_factory=list, description="Related articles")
    topic: Optional[str] = Field(None, description="Question topic")


class StoredQuiz(BaseModel):
    """Model for a quiz stored in Firestore."""

    id: str = Field(..., description="Unique quiz ID")
    course_id: str = Field(..., description="Course ID this quiz belongs to")
    topic: str = Field(..., description="Quiz topic")
    difficulty: str = Field(..., description="Quiz difficulty: easy, medium, hard")
    week_number: Optional[int] = Field(None, description="Week number if filtered")
    num_questions: int = Field(..., description="Number of questions")
    questions: List[StoredQuizQuestion] = Field(..., description="Quiz questions")
    content_hash: str = Field(..., description="Hash for duplicate detection")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp (UTC)")
    title: Optional[str] = Field(None, description="Optional quiz title")


class StoredQuizSummary(BaseModel):
    """Summary of a stored quiz for listing."""

    id: str = Field(..., description="Quiz ID")
    course_id: str = Field(..., description="Course ID")
    topic: str = Field(..., description="Quiz topic")
    difficulty: str = Field(..., description="Difficulty level")
    week_number: Optional[int] = Field(None, description="Week number")
    num_questions: int = Field(..., description="Number of questions")
    created_at: datetime = Field(..., description="Creation timestamp")
    title: Optional[str] = Field(None, description="Quiz title")


class QuizAttemptResult(BaseModel):
    """Model for storing a user's quiz attempt result."""

    id: str = Field(..., description="Result ID")
    quiz_id: str = Field(..., description="Quiz ID")
    course_id: str = Field(..., description="Course ID")
    user_id: str = Field(..., description="User ID (simulated)")
    answers: List[int] = Field(..., description="User's answer indices")
    score: int = Field(..., ge=0, description="Number of correct answers")
    total_questions: int = Field(..., ge=1, description="Total questions in quiz")
    percentage: float = Field(..., ge=0, le=100, description="Score percentage")
    time_taken_seconds: Optional[int] = Field(None, description="Time taken in seconds")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Completion timestamp (UTC)")


class QuizSubmitRequest(BaseModel):
    """Request model for submitting quiz answers."""

    quiz_id: str = Field(..., description="Quiz ID")
    course_id: str = Field(..., description="Course ID the quiz belongs to")
    answers: List[int] = Field(..., description="User's answer indices for each question")
    user_id: Optional[str] = Field(None, description="User ID (generated if not provided)")
    time_taken_seconds: Optional[int] = Field(None, ge=0, description="Time taken in seconds")

    @field_validator('answers')
    @classmethod
    def validate_answers(cls, v: List[int]) -> List[int]:
        """Validate that answer indices are non-negative."""
        if any(answer < 0 for answer in v):
            raise ValueError('Answer indices must be non-negative')
        return v


class QuizHistoryItem(BaseModel):
    """Item in user's quiz history."""

    result_id: str = Field(..., description="Result ID")
    quiz_id: str = Field(..., description="Quiz ID")
    course_id: str = Field(..., description="Course ID")
    topic: str = Field(..., description="Quiz topic")
    difficulty: str = Field(..., description="Difficulty level")
    score: int = Field(..., description="Score achieved")
    total_questions: int = Field(..., description="Total questions")
    percentage: float = Field(..., description="Score percentage")
    completed_at: datetime = Field(..., description="Completion timestamp")


class CreateQuizRequest(BaseModel):
    """Request model for creating/generating a new quiz."""

    course_id: str = Field(..., min_length=1, max_length=100, description="Course ID")
    topic: Optional[str] = Field(None, description="Topic for the quiz")
    week: Optional[int] = Field(None, ge=1, le=52, description="Week number filter")
    num_questions: int = Field(10, ge=1, le=50, description="Number of questions")
    difficulty: str = Field("medium", description="Difficulty: easy, medium, hard")
    title: Optional[str] = Field(None, max_length=200, description="Optional quiz title")
    allow_duplicate: bool = Field(False, description="Allow duplicate quiz if one exists")


# ============================================================================
# Study Guide Persistence Models
# ============================================================================

class StoredStudyGuide(BaseModel):
    """Model for a study guide stored in Firestore."""

    id: str = Field(..., description="Unique study guide ID")
    course_id: str = Field(..., description="Course ID this guide belongs to")
    title: str = Field(..., description="Study guide title")
    content: str = Field(..., description="Markdown content of the study guide")
    week_numbers: Optional[List[int]] = Field(None, description="Week numbers covered")
    content_hash: str = Field(..., description="Hash for duplicate detection")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp (UTC)"
    )
    word_count: int = Field(0, description="Approximate word count")


class StoredStudyGuideSummary(BaseModel):
    """Summary of a stored study guide for listing."""

    id: str = Field(..., description="Study guide ID")
    course_id: str = Field(..., description="Course ID")
    title: str = Field(..., description="Study guide title")
    week_numbers: Optional[List[int]] = Field(None, description="Week numbers covered")
    created_at: datetime = Field(..., description="Creation timestamp")
    word_count: int = Field(0, description="Approximate word count")


class CreateStudyGuideRequest(BaseModel):
    """Request model for creating/generating a new study guide."""

    course_id: str = Field(..., min_length=1, max_length=100, description="Course ID")
    weeks: Optional[List[int]] = Field(None, description="Week numbers to cover")
    title: Optional[str] = Field(None, max_length=200, description="Optional study guide title")
    allow_duplicate: bool = Field(False, description="Allow duplicate if one exists")


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
