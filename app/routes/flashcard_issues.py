"""
Flashcard Issues API Routes

Endpoints for reporting and managing flashcard issues.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from typing import Optional
import uuid

from app.models.flashcard_models import (
    FlashcardIssue,
    FlashcardIssueCreate,
    FlashcardIssueUpdate,
    FlashcardIssuesList
)
from app.services.gcp_service import get_firestore_client
from app.services.auth_service import get_current_user
from app.models.schemas import User

router = APIRouter(prefix="/api/flashcards/issues", tags=["Flashcard Issues"])


@router.post("", response_model=FlashcardIssue, status_code=201)
async def create_issue(
    issue_data: FlashcardIssueCreate,
    user: User = Depends(get_current_user)
):
    """
    Report a flashcard issue.
    
    Args:
        issue_data: Issue creation data
        user: Current authenticated user
        
    Returns:
        Created flashcard issue
        
    Raises:
        HTTPException: If issue creation fails
    """
    try:
        db = get_firestore_client()
        
        issue_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        issue_dict = {
            'user_id': user.email,
            'card_id': issue_data.card_id,
            'set_id': issue_data.set_id,
            'issue_type': issue_data.issue_type,
            'description': issue_data.description,
            'status': 'open',
            'created_at': now,
            'resolved_at': None,
            'admin_notes': None
        }
        
        db.collection('flashcard_issues').document(issue_id).set(issue_dict)
        issue_dict['id'] = issue_id
        
        return FlashcardIssue(**issue_dict)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create issue: {str(e)}")


@router.get("/{issue_id}", response_model=FlashcardIssue)
async def get_issue(
    issue_id: str,
    user: User = Depends(get_current_user)
):
    """
    Get a flashcard issue by ID.
    
    Args:
        issue_id: Issue ID
        user: Current authenticated user
        
    Returns:
        Flashcard issue
        
    Raises:
        HTTPException: If issue not found
    """
    try:
        db = get_firestore_client()
        
        issue_doc = db.collection('flashcard_issues').document(issue_id).get()
        
        if not issue_doc.exists:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        issue_dict = issue_doc.to_dict()
        issue_dict['id'] = issue_id
        
        # Users can only see their own issues unless they're admin
        if issue_dict['user_id'] != user.email and not user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FlashcardIssue(**issue_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get issue: {str(e)}")


@router.get("", response_model=FlashcardIssuesList)
async def get_all_issues(
    set_id: Optional[str] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """
    Get all flashcard issues.
    
    For regular users: returns only their own issues
    For admins: returns all issues
    
    Args:
        set_id: Optional flashcard set ID to filter by
        status: Optional status to filter by
        user: Current authenticated user
        
    Returns:
        List of flashcard issues
    """
    try:
        db = get_firestore_client()
        
        query = db.collection('flashcard_issues')
        
        # Regular users can only see their own issues
        if not user.is_admin:
            query = query.where('user_id', '==', user.email)
        
        if set_id:
            query = query.where('set_id', '==', set_id)
        
        if status:
            query = query.where('status', '==', status)
        
        issues_docs = query.get()
        
        issues = []
        for doc in issues_docs:
            issue_dict = doc.to_dict()
            issue_dict['id'] = doc.id
            issues.append(FlashcardIssue(**issue_dict))
        
        return FlashcardIssuesList(issues=issues, total=len(issues))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get issues: {str(e)}")


@router.patch("/{issue_id}", response_model=FlashcardIssue)
async def update_issue(
    issue_id: str,
    issue_data: FlashcardIssueUpdate,
    user: User = Depends(get_current_user)
):
    """
    Update a flashcard issue (admin only).
    
    Args:
        issue_id: Issue ID
        issue_data: Updated issue data
        user: Current authenticated user
        
    Returns:
        Updated flashcard issue
        
    Raises:
        HTTPException: If not admin, issue not found, or update fails
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        db = get_firestore_client()
        
        issue_ref = db.collection('flashcard_issues').document(issue_id)
        issue_doc = issue_ref.get()
        
        if not issue_doc.exists:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        update_data = {
            'status': issue_data.status,
            'admin_notes': issue_data.admin_notes
        }
        
        # Set resolved_at if status is resolved or closed
        if issue_data.status in ['resolved', 'closed']:
            update_data['resolved_at'] = datetime.utcnow()
        
        issue_ref.update(update_data)
        
        # Get updated document
        updated_doc = issue_ref.get()
        issue_dict = updated_doc.to_dict()
        issue_dict['id'] = issue_id
        
        return FlashcardIssue(**issue_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update issue: {str(e)}")


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(
    issue_id: str,
    user: User = Depends(get_current_user)
):
    """
    Delete a flashcard issue (admin only).
    
    Args:
        issue_id: Issue ID
        user: Current authenticated user
        
    Raises:
        HTTPException: If not admin, issue not found, or deletion fails
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        db = get_firestore_client()
        
        issue_ref = db.collection('flashcard_issues').document(issue_id)
        issue_doc = issue_ref.get()
        
        if not issue_doc.exists:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        issue_ref.delete()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete issue: {str(e)}")

