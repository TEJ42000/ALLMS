"""
Flashcard Models

Pydantic models for flashcard notes and issue reporting.
"""

import html
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class FlashcardNoteCreate(BaseModel):
    """Request model for creating a flashcard note"""
    card_id: str = Field(..., min_length=1, max_length=100, description="Unique identifier for the flashcard")
    set_id: str = Field(..., min_length=1, max_length=100, description="Flashcard set identifier")
    note_text: str = Field(..., min_length=1, max_length=5000, description="Note content")

    @field_validator('note_text')
    @classmethod
    def validate_note_text(cls, v: str) -> str:
        """Validate note text is not empty after stripping and sanitize HTML"""
        v = v.strip()
        if not v:
            raise ValueError('Note text cannot be empty')
        # Escape HTML to prevent XSS
        return html.escape(v)


class FlashcardNoteUpdate(BaseModel):
    """Request model for updating a flashcard note"""
    note_text: str = Field(..., min_length=1, max_length=5000, description="Updated note content")

    @field_validator('note_text')
    @classmethod
    def validate_note_text(cls, v: str) -> str:
        """Validate note text is not empty after stripping and sanitize HTML"""
        v = v.strip()
        if not v:
            raise ValueError('Note text cannot be empty')
        # Escape HTML to prevent XSS
        return html.escape(v)


class FlashcardNote(BaseModel):
    """Response model for a flashcard note"""
    id: str = Field(..., description="Note ID")
    user_id: str = Field(..., description="User ID who created the note")
    card_id: str = Field(..., description="Flashcard ID")
    set_id: str = Field(..., description="Flashcard set ID")
    note_text: str = Field(..., description="Note content")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FlashcardIssueCreate(BaseModel):
    """Request model for reporting a flashcard issue"""
    card_id: str = Field(..., min_length=1, max_length=100, description="Flashcard ID")
    set_id: str = Field(..., min_length=1, max_length=100, description="Flashcard set ID")
    issue_type: str = Field(..., description="Type of issue")
    description: str = Field(..., min_length=1, max_length=2000, description="Issue description")

    @field_validator('issue_type')
    @classmethod
    def validate_issue_type(cls, v: str) -> str:
        """Validate issue type is one of the allowed values"""
        allowed_types = ['incorrect', 'typo', 'unclear', 'other']
        if v not in allowed_types:
            raise ValueError(f'Issue type must be one of: {", ".join(allowed_types)}')
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is not empty after stripping and sanitize HTML"""
        v = v.strip()
        if not v:
            raise ValueError('Description cannot be empty')
        # Escape HTML to prevent XSS
        return html.escape(v)


class FlashcardIssueUpdate(BaseModel):
    """Request model for updating a flashcard issue (admin only)"""
    status: str = Field(..., description="Issue status")
    admin_notes: Optional[str] = Field(None, max_length=2000, description="Admin notes")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of the allowed values"""
        allowed_statuses = ['open', 'in_review', 'resolved', 'closed']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

    @field_validator('admin_notes')
    @classmethod
    def validate_admin_notes(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and convert empty to None, sanitize HTML"""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # Escape HTML to prevent XSS
            return html.escape(v)
        return v


class FlashcardIssue(BaseModel):
    """Response model for a flashcard issue"""
    id: str = Field(..., description="Issue ID")
    user_id: str = Field(..., description="User ID who reported the issue")
    card_id: str = Field(..., description="Flashcard ID")
    set_id: str = Field(..., description="Flashcard set ID")
    issue_type: str = Field(..., description="Type of issue")
    description: str = Field(..., description="Issue description")
    status: str = Field(..., description="Issue status")
    created_at: datetime = Field(..., description="Creation timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    admin_notes: Optional[str] = Field(None, description="Admin notes")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FlashcardNotesList(BaseModel):
    """Response model for list of flashcard notes"""
    notes: list[FlashcardNote] = Field(..., description="List of notes")
    total: int = Field(..., description="Total number of notes")


class FlashcardIssuesList(BaseModel):
    """Response model for list of flashcard issues"""
    issues: list[FlashcardIssue] = Field(..., description="List of issues")
    total: int = Field(..., description="Total number of issues")

