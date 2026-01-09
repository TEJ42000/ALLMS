"""
Flashcard Notes API Routes

Endpoints for creating, reading, updating, and deleting flashcard notes.

Rate Limits:
- POST (create/update): 10 requests/minute per user
- GET (list): 60 requests/minute per user
- PUT (update): 20 requests/minute per user
- DELETE: 20 requests/minute per user
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict
import uuid
from google.cloud.firestore import transactional

logger = logging.getLogger(__name__)

from app.models.flashcard_models import (
    FlashcardNote,
    FlashcardNoteCreate,
    FlashcardNoteUpdate,
    FlashcardNotesList
)
from app.services.gcp_service import get_firestore_client
from app.services.auth_service import get_current_user
from app.services.rate_limiter import check_flashcard_rate_limit
from app.models.schemas import User

router = APIRouter(prefix="/api/flashcards/notes", tags=["Flashcard Notes"])


@transactional
def create_or_update_note_transactional(
    transaction,
    db,
    user_email: str,
    note_data: FlashcardNoteCreate
) -> Tuple[str, Dict]:
    """
    Transactional note creation/update to prevent race conditions.

    Args:
        transaction: Firestore transaction
        db: Firestore client
        user_email: User's email
        note_data: Note creation data

    Returns:
        Tuple of (note_id, note_dict)
    """
    # Query for existing note within transaction
    query = (
        db.collection('users')
        .document(user_email)
        .collection('flashcard_notes')
        .where('card_id', '==', note_data.card_id)
        .where('set_id', '==', note_data.set_id)
        .limit(1)
    )

    existing_notes = query.get(transaction=transaction)
    now = datetime.now(timezone.utc)

    if existing_notes:
        # Update existing note
        note_doc = existing_notes[0]
        note_id = note_doc.id

        transaction.update(note_doc.reference, {
            'note_text': note_data.note_text,
            'updated_at': now
        })

        # Return updated data
        note_dict = note_doc.to_dict()
        note_dict['note_text'] = note_data.note_text
        note_dict['updated_at'] = now
        note_dict['id'] = note_id

    else:
        # Create new note
        note_id = str(uuid.uuid4())
        note_dict = {
            'user_id': user_email,
            'card_id': note_data.card_id,
            'set_id': note_data.set_id,
            'note_text': note_data.note_text,
            'created_at': now,
            'updated_at': now
        }

        note_ref = (
            db.collection('users')
            .document(user_email)
            .collection('flashcard_notes')
            .document(note_id)
        )
        transaction.set(note_ref, note_dict)
        note_dict['id'] = note_id

    return note_id, note_dict



@router.post("", response_model=FlashcardNote, status_code=201)
async def create_note(
    note_data: FlashcardNoteCreate,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Create a new flashcard note or update existing one.

    Uses Firestore transactions to prevent race conditions when multiple
    requests try to create a note for the same card simultaneously.

    Rate Limit: 10 requests/minute per user

    Args:
        note_data: Note creation data
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Returns:
        Created or updated flashcard note

    Raises:
        HTTPException: If note creation fails or rate limit exceeded
    """
    # Rate limiting: 10 requests/minute per user
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "note_create", max_requests=10, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        db = get_firestore_client()
        transaction = db.transaction()

        # Use transactional create/update to prevent race conditions
        note_id, note_dict = create_or_update_note_transactional(
            transaction,
            db,
            user.email,
            note_data
        )

        logger.info(
            "Flashcard note created/updated successfully",
            extra={
                "user_id": user.email,
                "card_id": note_data.card_id,
                "set_id": note_data.set_id,
                "note_id": note_id
            }
        )
        return FlashcardNote(**note_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create flashcard note",
            extra={
                "user_id": user.email,
                "card_id": note_data.card_id,
                "set_id": note_data.set_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to create note. Please try again later."
        )


@router.get("/{card_id}", response_model=FlashcardNote)
async def get_note(
    card_id: str,
    set_id: str,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Get a flashcard note by card ID.

    Rate Limit: 60 requests/minute per user

    Args:
        card_id: Flashcard ID
        set_id: Flashcard set ID
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Returns:
        Flashcard note

    Raises:
        HTTPException: If note not found or rate limit exceeded
    """
    # Rate limiting: 60 requests/minute per user
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "note_get", max_requests=60, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        db = get_firestore_client()

        notes = (
            db.collection('users')
            .document(user.email)
            .collection('flashcard_notes')
            .where('card_id', '==', card_id)
            .where('set_id', '==', set_id)
            .limit(1)
            .get()
        )

        if not notes:
            raise HTTPException(status_code=404, detail="Note not found")

        note_doc = notes[0]
        note_dict = note_doc.to_dict()
        note_dict['id'] = note_doc.id

        return FlashcardNote(**note_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve flashcard note",
            extra={
                "user_id": user.email,
                "card_id": card_id,
                "set_id": set_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve note. Please try again later."
        )


@router.get("", response_model=FlashcardNotesList)
async def get_all_notes(
    set_id: Optional[str] = None,
    request: Request = None,
    user: User = Depends(get_current_user)
):
    """
    Get all flashcard notes for the current user.

    Rate Limit: 60 requests/minute per user

    Args:
        set_id: Optional flashcard set ID to filter by
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Returns:
        List of flashcard notes

    Raises:
        HTTPException: If retrieval fails or rate limit exceeded
    """
    # Rate limiting: 60 requests/minute per user
    client_ip = request.client.host if request and request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "note_list", max_requests=60, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        db = get_firestore_client()

        query = db.collection('users').document(user.email).collection('flashcard_notes')

        if set_id:
            query = query.where('set_id', '==', set_id)

        notes_docs = query.get()

        notes = []
        for doc in notes_docs:
            note_dict = doc.to_dict()
            note_dict['id'] = doc.id
            notes.append(FlashcardNote(**note_dict))

        return FlashcardNotesList(notes=notes, total=len(notes))

    except Exception as e:
        logger.error(
            "Failed to retrieve flashcard notes list",
            extra={
                "user_id": user.email,
                "set_id": set_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve notes. Please try again later."
        )


@router.put("/{note_id}", response_model=FlashcardNote)
async def update_note(
    note_id: str,
    note_data: FlashcardNoteUpdate,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Update a flashcard note.

    Rate Limit: 20 requests/minute per user

    Args:
        note_id: Note ID
        note_data: Updated note data
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Returns:
        Updated flashcard note

    Raises:
        HTTPException: If note not found, update fails, or rate limit exceeded
    """
    # Rate limiting: 20 requests/minute per user
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "note_update", max_requests=20, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        db = get_firestore_client()

        note_ref = db.collection('users').document(user.email).collection('flashcard_notes').document(note_id)
        note_doc = note_ref.get()

        if not note_doc.exists:
            raise HTTPException(status_code=404, detail="Note not found")

        # Update note
        note_ref.update({
            'note_text': note_data.note_text,
            'updated_at': datetime.now(timezone.utc)
        })

        # Get updated document
        updated_doc = note_ref.get()
        note_dict = updated_doc.to_dict()
        note_dict['id'] = note_id

        logger.info(
            "Flashcard note updated successfully",
            extra={
                "user_id": user.email,
                "note_id": note_id
            }
        )
        return FlashcardNote(**note_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update flashcard note",
            extra={
                "user_id": user.email,
                "note_id": note_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to update note. Please try again later."
        )


@router.delete("/card/{card_id}", status_code=204)
async def delete_note_by_card(
    card_id: str,
    set_id: str,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Delete a flashcard note by card ID.

    Rate Limit: 20 requests/minute per user

    Args:
        card_id: Flashcard ID
        set_id: Flashcard set ID
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Raises:
        HTTPException: If note not found, deletion fails, or rate limit exceeded
    """
    # Rate limiting: 20 requests/minute per user
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "note_delete", max_requests=20, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        db = get_firestore_client()

        notes = (
            db.collection('users')
            .document(user.email)
            .collection('flashcard_notes')
            .where('card_id', '==', card_id)
            .where('set_id', '==', set_id)
            .limit(1)
            .get()
        )

        if not notes:
            raise HTTPException(status_code=404, detail="Note not found")

        notes[0].reference.delete()
        logger.info(
            "Flashcard note deleted successfully",
            extra={
                "user_id": user.email,
                "card_id": card_id,
                "set_id": set_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete flashcard note",
            extra={
                "user_id": user.email,
                "card_id": card_id,
                "set_id": set_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to delete note. Please try again later."
        )

