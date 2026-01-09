"""
Flashcard Issues API Routes

Endpoints for reporting and managing flashcard issues.

Rate Limits:
- POST (create): 10 requests/minute per user
- GET (list/get): 60 requests/minute per user
- PATCH (update): 20 requests/minute per user (admin only)
- DELETE: 20 requests/minute per user (admin only)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

from app.models.flashcard_models import (
    FlashcardIssue,
    FlashcardIssueCreate,
    FlashcardIssueUpdate,
    FlashcardIssuesList
)
from app.services.gcp_service import get_firestore_client
from app.services.rate_limiter import check_flashcard_rate_limit
from app.dependencies.auth import get_current_user
from app.models.auth_models import User

router = APIRouter(prefix="/api/flashcards/issues", tags=["Flashcard Issues"])


@router.post("", response_model=FlashcardIssue, status_code=201)
async def create_issue(
    issue_data: FlashcardIssueCreate,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Report a flashcard issue.

    Rate Limit: 10 requests/minute per user

    Args:
        issue_data: Issue creation data
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Returns:
        Created flashcard issue

    Raises:
        HTTPException: If issue creation fails or rate limit exceeded
    """
    # Rate limiting: 10 requests/minute per user
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "issue_create", max_requests=10, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        db = get_firestore_client()

        issue_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

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

        logger.info(
            "Flashcard issue created successfully",
            extra={
                "user_id": user.email,
                "issue_id": issue_id,
                "card_id": issue_data.card_id,
                "set_id": issue_data.set_id,
                "issue_type": issue_data.issue_type
            }
        )
        return FlashcardIssue(**issue_dict)

    except Exception as e:
        logger.error(
            "Failed to create flashcard issue",
            extra={
                "user_id": user.email,
                "card_id": issue_data.card_id,
                "set_id": issue_data.set_id,
                "issue_type": issue_data.issue_type,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to report issue. Please try again later."
        )


@router.get("/{issue_id}", response_model=FlashcardIssue)
async def get_issue(
    issue_id: str,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Get a flashcard issue by ID.

    Rate Limit: 60 requests/minute per user

    Args:
        issue_id: Issue ID
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Returns:
        Flashcard issue

    Raises:
        HTTPException: If issue not found, access denied, or rate limit exceeded
    """
    # Rate limiting: 60 requests/minute per user
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "issue_get", max_requests=60, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

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
        logger.error(
            "Failed to retrieve flashcard issue",
            extra={
                "user_id": user.email,
                "issue_id": issue_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve issue. Please try again later."
        )


@router.get("", response_model=FlashcardIssuesList)
async def get_all_issues(
    set_id: Optional[str] = None,
    status: Optional[str] = None,
    request: Request = None,
    user: User = Depends(get_current_user)
):
    """
    Get all flashcard issues.

    For regular users: returns only their own issues
    For admins: returns all issues

    Rate Limit: 60 requests/minute per user

    Args:
        set_id: Optional flashcard set ID to filter by
        status: Optional status to filter by
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Returns:
        List of flashcard issues

    Raises:
        HTTPException: If retrieval fails or rate limit exceeded
    """
    # Rate limiting: 60 requests/minute per user
    client_ip = request.client.host if request and request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "issue_list", max_requests=60, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

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
        logger.error(
            "Failed to retrieve flashcard issues list",
            extra={
                "user_id": user.email,
                "set_id": set_id,
                "status": status,
                "is_admin": user.is_admin,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve issues. Please try again later."
        )


@router.patch("/{issue_id}", response_model=FlashcardIssue)
async def update_issue(
    issue_id: str,
    issue_data: FlashcardIssueUpdate,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Update a flashcard issue (admin only).

    Rate Limit: 20 requests/minute per user

    Args:
        issue_id: Issue ID
        issue_data: Updated issue data
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Returns:
        Updated flashcard issue

    Raises:
        HTTPException: If not admin, issue not found, update fails, or rate limit exceeded
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Rate limiting: 20 requests/minute per user
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "issue_update", max_requests=20, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

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
            update_data['resolved_at'] = datetime.now(timezone.utc)

        issue_ref.update(update_data)

        # Get updated document
        updated_doc = issue_ref.get()
        issue_dict = updated_doc.to_dict()
        issue_dict['id'] = issue_id

        logger.info(
            "Flashcard issue updated successfully",
            extra={
                "admin_id": user.email,
                "issue_id": issue_id,
                "new_status": issue_data.status
            }
        )
        return FlashcardIssue(**issue_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update flashcard issue",
            extra={
                "admin_id": user.email,
                "issue_id": issue_id,
                "new_status": issue_data.status,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to update issue. Please try again later."
        )


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(
    issue_id: str,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Delete a flashcard issue (admin only).

    Rate Limit: 20 requests/minute per user

    Args:
        issue_id: Issue ID
        request: FastAPI request object (for rate limiting)
        user: Current authenticated user

    Raises:
        HTTPException: If not admin, issue not found, deletion fails, or rate limit exceeded
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Rate limiting: 20 requests/minute per user
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, error_msg = check_flashcard_rate_limit(
        user.email, client_ip, "issue_delete", max_requests=20, window_seconds=60
    )
    if not is_allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        db = get_firestore_client()

        issue_ref = db.collection('flashcard_issues').document(issue_id)
        issue_doc = issue_ref.get()

        if not issue_doc.exists:
            raise HTTPException(status_code=404, detail="Issue not found")

        issue_ref.delete()
        logger.info(
            "Flashcard issue deleted successfully",
            extra={
                "admin_id": user.email,
                "issue_id": issue_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete flashcard issue",
            extra={
                "admin_id": user.email,
                "issue_id": issue_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to delete issue. Please try again later."
        )

