"""Admin API Routes for User Allow List Management.

Provides CRUD endpoints for managing the allow list.
These endpoints require @mgms.eu domain authentication.
"""

import logging
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_mgms_domain
from app.models.auth_models import User
from app.models.allow_list_models import (
    AllowListCreateRequest,
    AllowListUpdateRequest,
    AllowListResponse,
    AllowListListResponse,
    AllowListEntry,
)
from app.services.allow_list_service import get_allow_list_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/users",
    tags=["Admin - Users"],
    dependencies=[Depends(require_mgms_domain)],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - requires @mgms.eu domain"},
        500: {"description": "Internal server error"},
    }
)


@router.get(
    "/allowed",
    response_model=AllowListListResponse,
    summary="List all allowed users",
    description="Get all users on the allow list. By default, only active, non-expired entries are returned.",
)
async def list_allowed_users(
    include_expired: bool = Query(False, description="Include expired entries"),
    include_inactive: bool = Query(False, description="Include inactive entries"),
    user: User = Depends(require_mgms_domain),
):
    """List all users on the allow list."""
    service = get_allow_list_service()

    if not service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Allow list service is not available"
        )

    # Get all entries once to avoid race conditions between queries
    all_entries = service.get_all_users(include_expired=True, include_inactive=True)

    # Filter for display based on parameters
    if include_expired and include_inactive:
        entries = all_entries
    else:
        entries = [
            e for e in all_entries
            if (include_inactive or e.active) and (include_expired or not e.is_expired)
        ]

    # Calculate counts from the same dataset
    active_count = sum(1 for e in all_entries if e.is_effective)
    expired_count = sum(1 for e in all_entries if e.active and e.is_expired)
    inactive_count = sum(1 for e in all_entries if not e.active)

    return AllowListListResponse(
        entries=[AllowListResponse.from_entry(e) for e in entries],
        total=len(all_entries),
        active_count=active_count,
        expired_count=expired_count,
        inactive_count=inactive_count,
    )


@router.post(
    "/allowed",
    response_model=AllowListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add user to allow list",
    description="Add a new user to the allow list. Cannot add @mgms.eu users.",
)
async def add_allowed_user(
    request: AllowListCreateRequest,
    user: User = Depends(require_mgms_domain),
):
    """Add a user to the allow list."""
    service = get_allow_list_service()

    if not service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Allow list service is not available"
        )

    try:
        entry = service.add_user(request, added_by=user.email)
        logger.info("User %s added %s to allow list", user.email, request.email)
        return AllowListResponse.from_entry(entry)
    except ValueError as e:
        # Provide helpful error message
        error_msg = str(e)
        logger.warning(
            "Failed to add user %s to allow list: %s",
            request.email, error_msg,
            extra={
                "admin_user": user.email,
                "target_email": request.email,
                "error": error_msg
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )


@router.get(
    "/allowed/{email:path}",
    response_model=AllowListResponse,
    summary="Get specific allowed user",
    description="Get details for a specific user on the allow list.",
)
async def get_allowed_user(
    email: str,
    user: User = Depends(require_mgms_domain),
):
    """Get a specific allow list entry."""
    service = get_allow_list_service()

    if not service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Allow list service is not available"
        )

    # URL decode the email
    decoded_email = unquote(email)
    entry = service.get_user(decoded_email)

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {decoded_email} not found in allow list"
        )

    return AllowListResponse.from_entry(entry)


@router.patch(
    "/allowed/{email:path}",
    response_model=AllowListResponse,
    summary="Update allowed user",
    description="Update an existing allow list entry.",
)
async def update_allowed_user(
    email: str,
    request: AllowListUpdateRequest,
    user: User = Depends(require_mgms_domain),
):
    """Update an allow list entry."""
    service = get_allow_list_service()

    if not service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Allow list service is not available"
        )

    decoded_email = unquote(email)

    try:
        entry = service.update_user(decoded_email, request)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {decoded_email} not found in allow list"
            )

        logger.info("User %s updated allow list entry for %s", user.email, decoded_email)
        return AllowListResponse.from_entry(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/allowed/{email:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from allow list",
    description="Remove a user from the allow list (soft delete - sets active=false).",
)
async def remove_allowed_user(
    email: str,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete"),
    user: User = Depends(require_mgms_domain),
):
    """Remove a user from the allow list."""
    service = get_allow_list_service()

    if not service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Allow list service is not available"
        )

    decoded_email = unquote(email)
    removed = service.remove_user(decoded_email, soft_delete=not hard_delete)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {decoded_email} not found in allow list"
        )

    logger.info(
        "User %s removed %s from allow list (hard_delete=%s)",
        user.email, decoded_email, hard_delete
    )
    return None

