"""
GDPR Compliance Routes

API endpoints for GDPR compliance features including data export,
deletion, and consent management.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, validator

from app.dependencies.auth import get_current_user
from app.models.auth_models import User
from app.services.gdpr_service import GDPRService
from app.services.gcp_service import get_firestore_client
from app.services.token_service import (
    generate_deletion_token,
    validate_deletion_token,
    send_deletion_confirmation_email
)
from app.models.gdpr_models import (
    ConsentType, ConsentStatus,
    GDPRExportRequest, GDPRDeleteRequest,
    PrivacySettings
)

logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis or similar)
_rate_limit_storage: Dict[str, Dict[str, any]] = defaultdict(lambda: {"count": 0, "reset_time": datetime.utcnow()})

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])


# Request models with validation
class ConsentRequest(BaseModel):
    """Request model for consent recording."""
    consent_type: ConsentType
    status: ConsentStatus

    @validator('consent_type')
    def validate_consent_type(cls, v):
        """Validate consent type is a valid enum value."""
        if v not in ConsentType.__members__.values():
            raise ValueError(f"Invalid consent type: {v}")
        return v

    @validator('status')
    def validate_status(cls, v):
        """Validate status is a valid enum value."""
        if v not in ConsentStatus.__members__.values():
            raise ValueError(f"Invalid consent status: {v}")
        return v


class DeleteAccountRequest(BaseModel):
    """Request model for account deletion with validation."""
    user_id: str
    email: EmailStr  # Validates email format
    confirmation_token: str
    delete_all_data: bool = True
    reason: Optional[str] = None

    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user ID is not empty."""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @validator('confirmation_token')
    def validate_token(cls, v):
        """Validate confirmation token is not empty."""
        if not v or not v.strip():
            raise ValueError("confirmation_token cannot be empty")
        return v.strip()

    @validator('reason')
    def validate_reason(cls, v):
        """Validate reason length if provided."""
        if v and len(v) > 500:
            raise ValueError("reason must not exceed 500 characters")
        return v


def check_rate_limit(user_id: str, endpoint: str, max_requests: int = 10, window_minutes: int = 60) -> bool:
    """Check if user has exceeded rate limit for endpoint.

    Args:
        user_id: User ID
        endpoint: Endpoint name
        max_requests: Maximum requests allowed in window
        window_minutes: Time window in minutes

    Returns:
        True if within rate limit, False if exceeded

    Raises:
        HTTPException: If rate limit exceeded
    """
    key = f"{user_id}:{endpoint}"
    now = datetime.utcnow()

    # Get or create rate limit entry
    limit_data = _rate_limit_storage[key]

    # Reset if window has passed
    if now >= limit_data["reset_time"]:
        limit_data["count"] = 0
        limit_data["reset_time"] = now + timedelta(minutes=window_minutes)

    # Check limit
    if limit_data["count"] >= max_requests:
        reset_in = (limit_data["reset_time"] - now).total_seconds()
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {int(reset_in)} seconds."
        )

    # Increment counter
    limit_data["count"] += 1
    return True


def get_gdpr_service() -> GDPRService:
    """Get GDPR service instance."""
    firestore_client = get_firestore_client()
    return GDPRService(firestore_client)


@router.post("/consent")
async def record_consent(
    request: Request,
    consent_request: ConsentRequest,
    current_user: User = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Record user consent for data processing.

    Args:
        request: FastAPI request object
        consent_request: Consent request with validation
        current_user: Current authenticated user
        gdpr_service: GDPR service instance

    Returns:
        Consent record

    Raises:
        HTTPException: If validation fails or operation errors
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = current_user.user_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in session")

        # Rate limiting: 100 consent changes per hour
        check_rate_limit(user_id, "consent", max_requests=100, window_minutes=60)

        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')

        consent = await gdpr_service.record_consent(
            user_id=user_id,
            consent_type=consent_request.consent_type,
            status=consent_request.status,
            ip_address=ip_address,
            user_agent=user_agent
        )

        if not consent:
            logger.error(f"Failed to record consent for user {user_id}")
            raise HTTPException(status_code=500, detail="Failed to record consent")

        return {
            "success": True,
            "consent": consent.dict(),
            "message": f"Consent {consent_request.status.value} for {consent_request.consent_type.value}"
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error recording consent: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error recording consent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/consent")
async def get_consents(
    current_user: User = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Get all consent records for current user.

    Args:
        current_user: Current authenticated user
        gdpr_service: GDPR service instance

    Returns:
        List of consent records
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = current_user.user_id
        consents = await gdpr_service.get_user_consents(user_id)

        return {
            "success": True,
            "consents": [c.dict() for c in consents]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting consents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/export")
async def export_user_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Export all user data (GDPR Right to Access).

    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        gdpr_service: GDPR service instance

    Returns:
        JSON file with all user data

    Raises:
        HTTPException: If user not authenticated or export fails
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = current_user.user_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in session")

        # Rate limiting: 5 exports per day to prevent abuse
        check_rate_limit(user_id, "export", max_requests=5, window_minutes=1440)

        logger.info(f"Starting data export for user {user_id}")

        # Export all user data
        export_data = await gdpr_service.export_user_data(user_id)

        if not export_data:
            logger.error(f"No data returned for user {user_id}")
            raise HTTPException(status_code=500, detail="Failed to export data")

        # Convert to JSON with error handling
        try:
            json_data = json.dumps(export_data.dict(), indent=2, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Error serializing export data: {e}")
            raise HTTPException(status_code=500, detail="Failed to serialize export data")

        # Sanitize filename to prevent path traversal
        safe_user_id = re.sub(r'[^a-zA-Z0-9_-]', '', user_id[:50])
        filename = f"user_data_export_{safe_user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        logger.info(f"Data export completed for user {user_id}, size: {len(json_data)} bytes")

        return StreamingResponse(
            iter([json_data]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Content-Type-Options": "nosniff"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting user data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/delete/request")
async def request_account_deletion(
    request: Request,
    current_user: User = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Request account deletion - sends confirmation email with token.

    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        gdpr_service: GDPR service instance

    Returns:
        Confirmation that email was sent

    Raises:
        HTTPException: If user not authenticated or request fails
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = current_user.user_id
        user_email = current_user.email

        # Rate limiting: 3 deletion requests per day
        check_rate_limit(user_id, "delete_request", max_requests=3, window_minutes=1440)

        # Generate secure deletion token
        token, expiry = generate_deletion_token(user_id, user_email)

        # Send confirmation email
        email_sent = await send_deletion_confirmation_email(user_email, user_id, token, expiry)

        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send confirmation email")

        logger.info(f"Deletion request initiated for user {user_id}")

        return {
            "success": True,
            "message": "Confirmation email sent. Please check your email for the deletion token.",
            "email": user_email,
            "expires_at": expiry.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting account deletion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/delete")
async def delete_user_account(
    request: Request,
    delete_request: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Delete user account and all data (GDPR Right to be Forgotten).

    Args:
        request: FastAPI request object
        delete_request: Deletion request details with validation
        current_user: Current authenticated user
        gdpr_service: GDPR service instance

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If validation fails or deletion errors
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = current_user.user_id
        user_email = current_user.email

        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in session")

        if not user_email:
            raise HTTPException(status_code=401, detail="User email not found in session")

        # Rate limiting: 3 deletion attempts per day
        check_rate_limit(user_id, "delete", max_requests=3, window_minutes=1440)

        # Verify user ID matches
        if delete_request.user_id != user_id:
            logger.warning(f"User ID mismatch in deletion request: {user_id} vs {delete_request.user_id}")
            raise HTTPException(status_code=403, detail="User ID mismatch")

        # Verify email matches (case-insensitive)
        if delete_request.email.lower() != user_email.lower():
            logger.warning(f"Email mismatch in deletion request for user {user_id}")
            raise HTTPException(status_code=403, detail="Email mismatch")

        # Validate secure token
        is_valid, error_message = validate_deletion_token(
            delete_request.confirmation_token,
            user_id,
            user_email
        )

        if not is_valid:
            logger.warning(f"Invalid deletion token for user {user_id}: {error_message}")
            raise HTTPException(status_code=400, detail=f"Invalid confirmation token: {error_message}")

        logger.info(f"Initiating account deletion for user {user_id}")

        # Perform soft delete with 30-day retention
        success = await gdpr_service.delete_user_data(
            user_id=user_id,
            soft_delete=True,
            retention_days=30
        )

        if success:
            logger.info(f"Account deletion initiated for user {user_id}")
            permanent_deletion_date = datetime.utcnow().replace(microsecond=0) + timedelta(days=30)

            return {
                "success": True,
                "message": "Account deletion initiated. Data will be permanently deleted in 30 days.",
                "permanent_deletion_date": permanent_deletion_date.isoformat(),
                "user_id": user_id
            }
        else:
            logger.error(f"Deletion failed for user {user_id}")
            raise HTTPException(status_code=500, detail="Deletion failed")

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error in account deletion: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting user account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/privacy-settings")
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Get user's privacy settings.

    Args:
        current_user: Current authenticated user
        gdpr_service: GDPR service instance

    Returns:
        Privacy settings
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = current_user.user_id

        # Get privacy settings from Firestore
        if gdpr_service.db:
            settings_ref = gdpr_service.db.collection('privacy_settings').document(user_id)
            settings_doc = settings_ref.get()

            if settings_doc.exists:
                return {
                    "success": True,
                    "settings": settings_doc.to_dict()
                }

        # Return defaults if not found
        return {
            "success": True,
            "settings": {
                "user_id": user_id,
                "ai_tutoring_enabled": True,
                "analytics_enabled": True,
                "marketing_emails_enabled": False,
                "data_retention_days": 365,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting privacy settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/privacy-settings")
async def update_privacy_settings(
    settings: PrivacySettings,
    current_user: User = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Update user's privacy settings.

    Args:
        settings: New privacy settings
        current_user: Current authenticated user
        gdpr_service: GDPR service instance

    Returns:
        Updated settings
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = current_user.user_id

        # Verify user ID matches
        if settings.user_id != user_id:
            raise HTTPException(status_code=403, detail="User ID mismatch")

        # Update settings in Firestore
        if gdpr_service.db:
            settings.updated_at = datetime.utcnow()
            settings_ref = gdpr_service.db.collection('privacy_settings').document(user_id)
            settings_ref.set(settings.dict())

            return {
                "success": True,
                "settings": settings.dict(),
                "message": "Privacy settings updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Database unavailable")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating privacy settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


from datetime import timedelta

