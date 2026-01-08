"""
GDPR Compliance Routes

API endpoints for GDPR compliance features including data export,
deletion, and consent management.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from app.dependencies.auth import get_current_user
from app.services.gdpr_service import GDPRService
from app.services.gcp_service import get_firestore_client
from app.models.gdpr_models import (
    ConsentType, ConsentStatus,
    GDPRExportRequest, GDPRDeleteRequest,
    PrivacySettings
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])


def get_gdpr_service() -> GDPRService:
    """Get GDPR service instance."""
    firestore_client = get_firestore_client()
    return GDPRService(firestore_client)


@router.post("/consent")
async def record_consent(
    request: Request,
    consent_type: ConsentType,
    status: ConsentStatus,
    current_user: dict = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Record user consent for data processing.
    
    Args:
        request: FastAPI request object
        consent_type: Type of consent
        status: Consent status (granted/revoked)
        current_user: Current authenticated user
        gdpr_service: GDPR service instance
        
    Returns:
        Consent record
    """
    try:
        user_id = current_user.get('uid')
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')
        
        consent = await gdpr_service.record_consent(
            user_id=user_id,
            consent_type=consent_type,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "success": True,
            "consent": consent.dict() if consent else None,
            "message": f"Consent {status.value} for {consent_type.value}"
        }
    except Exception as e:
        logger.error(f"Error recording consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consent")
async def get_consents(
    current_user: dict = Depends(get_current_user),
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
        user_id = current_user.get('uid')
        consents = await gdpr_service.get_user_consents(user_id)
        
        return {
            "success": True,
            "consents": [c.dict() for c in consents]
        }
    except Exception as e:
        logger.error(f"Error getting consents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_user_data(
    request: Request,
    current_user: dict = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Export all user data (GDPR Right to Access).
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        gdpr_service: GDPR service instance
        
    Returns:
        JSON file with all user data
    """
    try:
        user_id = current_user.get('uid')
        
        # Export all user data
        export_data = await gdpr_service.export_user_data(user_id)
        
        # Convert to JSON
        json_data = json.dumps(export_data.dict(), indent=2, default=str)
        
        # Return as downloadable file
        filename = f"user_data_export_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        return StreamingResponse(
            iter([json_data]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete")
async def delete_user_account(
    request: Request,
    delete_request: GDPRDeleteRequest,
    current_user: dict = Depends(get_current_user),
    gdpr_service: GDPRService = Depends(get_gdpr_service)
):
    """Delete user account and all data (GDPR Right to be Forgotten).
    
    Args:
        request: FastAPI request object
        delete_request: Deletion request details
        current_user: Current authenticated user
        gdpr_service: GDPR service instance
        
    Returns:
        Deletion confirmation
    """
    try:
        user_id = current_user.get('uid')
        
        # Verify user ID matches
        if delete_request.user_id != user_id:
            raise HTTPException(status_code=403, detail="User ID mismatch")
        
        # Verify email matches
        if delete_request.email != current_user.get('email'):
            raise HTTPException(status_code=403, detail="Email mismatch")
        
        # Perform soft delete with 30-day retention
        success = await gdpr_service.delete_user_data(
            user_id=user_id,
            soft_delete=True,
            retention_days=30
        )
        
        if success:
            return {
                "success": True,
                "message": "Account deletion initiated. Data will be permanently deleted in 30 days.",
                "permanent_deletion_date": (datetime.utcnow().replace(microsecond=0) + 
                                          timedelta(days=30)).isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Deletion failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy-settings")
async def get_privacy_settings(
    current_user: dict = Depends(get_current_user),
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
        user_id = current_user.get('uid')
        
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
    except Exception as e:
        logger.error(f"Error getting privacy settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/privacy-settings")
async def update_privacy_settings(
    settings: PrivacySettings,
    current_user: dict = Depends(get_current_user),
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
        user_id = current_user.get('uid')
        
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
        logger.error(f"Error updating privacy settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from datetime import timedelta

