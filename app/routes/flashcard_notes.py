"""
Flashcard Notes API Routes

Endpoints for creating, reading, updating, and deleting flashcard notes.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from typing import List
import uuid

from app.models.flashcard_models import (
    FlashcardNote,
    FlashcardNoteCreate,
    FlashcardNoteUpdate,
    FlashcardNotesList
)
from app.services.gcp_service import get_firestore_client
from app.services.auth_service import get_current_user
from app.models.schemas import User

router = APIRouter(prefix="/api/flashcards/notes", tags=["Flashcard Notes"])


@router.post("", response_model=FlashcardNote, status_code=201)
async def create_note(
    note_data: FlashcardNoteCreate,
    user: User = Depends(get_current_user)
):
    """
    Create a new flashcard note.
    
    Args:
        note_data: Note creation data
        user: Current authenticated user
        
    Returns:
        Created flashcard note
        
    Raises:
        HTTPException: If note creation fails
    """
    try:
        db = get_firestore_client()
        
        # Check if note already exists for this card
        existing_notes = (
            db.collection('users')
            .document(user.email)
            .collection('flashcard_notes')
            .where('card_id', '==', note_data.card_id)
            .where('set_id', '==', note_data.set_id)
            .limit(1)
            .get()
        )
        
        now = datetime.utcnow()
        
        if existing_notes:
            # Update existing note
            note_doc = existing_notes[0]
            note_id = note_doc.id
            
            note_doc.reference.update({
                'note_text': note_data.note_text,
                'updated_at': now
            })
            
            # Get updated document
            updated_doc = note_doc.reference.get()
            note_dict = updated_doc.to_dict()
            note_dict['id'] = note_id
            
        else:
            # Create new note
            note_id = str(uuid.uuid4())
            
            note_dict = {
                'user_id': user.email,
                'card_id': note_data.card_id,
                'set_id': note_data.set_id,
                'note_text': note_data.note_text,
                'created_at': now,
                'updated_at': now
            }
            
            db.collection('users').document(user.email).collection('flashcard_notes').document(note_id).set(note_dict)
            note_dict['id'] = note_id
        
        return FlashcardNote(**note_dict)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create note: {str(e)}")


@router.get("/{card_id}", response_model=FlashcardNote)
async def get_note(
    card_id: str,
    set_id: str,
    user: User = Depends(get_current_user)
):
    """
    Get a flashcard note by card ID.
    
    Args:
        card_id: Flashcard ID
        set_id: Flashcard set ID
        user: Current authenticated user
        
    Returns:
        Flashcard note
        
    Raises:
        HTTPException: If note not found
    """
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
        raise HTTPException(status_code=500, detail=f"Failed to get note: {str(e)}")


@router.get("", response_model=FlashcardNotesList)
async def get_all_notes(
    set_id: str = None,
    user: User = Depends(get_current_user)
):
    """
    Get all flashcard notes for the current user.
    
    Args:
        set_id: Optional flashcard set ID to filter by
        user: Current authenticated user
        
    Returns:
        List of flashcard notes
    """
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
        raise HTTPException(status_code=500, detail=f"Failed to get notes: {str(e)}")


@router.put("/{note_id}", response_model=FlashcardNote)
async def update_note(
    note_id: str,
    note_data: FlashcardNoteUpdate,
    user: User = Depends(get_current_user)
):
    """
    Update a flashcard note.
    
    Args:
        note_id: Note ID
        note_data: Updated note data
        user: Current authenticated user
        
    Returns:
        Updated flashcard note
        
    Raises:
        HTTPException: If note not found or update fails
    """
    try:
        db = get_firestore_client()
        
        note_ref = db.collection('users').document(user.email).collection('flashcard_notes').document(note_id)
        note_doc = note_ref.get()
        
        if not note_doc.exists:
            raise HTTPException(status_code=404, detail="Note not found")
        
        # Update note
        note_ref.update({
            'note_text': note_data.note_text,
            'updated_at': datetime.utcnow()
        })
        
        # Get updated document
        updated_doc = note_ref.get()
        note_dict = updated_doc.to_dict()
        note_dict['id'] = note_id
        
        return FlashcardNote(**note_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update note: {str(e)}")


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: str,
    user: User = Depends(get_current_user)
):
    """
    Delete a flashcard note.
    
    Args:
        note_id: Note ID
        user: Current authenticated user
        
    Raises:
        HTTPException: If note not found or deletion fails
    """
    try:
        db = get_firestore_client()
        
        note_ref = db.collection('users').document(user.email).collection('flashcard_notes').document(note_id)
        note_doc = note_ref.get()
        
        if not note_doc.exists:
            raise HTTPException(status_code=404, detail="Note not found")
        
        note_ref.delete()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete note: {str(e)}")


@router.delete("/card/{card_id}", status_code=204)
async def delete_note_by_card(
    card_id: str,
    set_id: str,
    user: User = Depends(get_current_user)
):
    """
    Delete a flashcard note by card ID.
    
    Args:
        card_id: Flashcard ID
        set_id: Flashcard set ID
        user: Current authenticated user
        
    Raises:
        HTTPException: If note not found or deletion fails
    """
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete note: {str(e)}")

