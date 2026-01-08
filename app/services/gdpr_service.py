"""
GDPR Compliance Service

Handles GDPR-related operations including data export, deletion,
consent management, and audit logging.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid

from google.cloud import firestore

from app.models.gdpr_models import (
    ConsentRecord, ConsentType, ConsentStatus,
    DataSubjectRequest, DataSubjectRequestType, RequestStatus,
    AuditLog, AuditLogAction,
    UserDataExport, PrivacySettings
)

logger = logging.getLogger(__name__)


class GDPRService:
    """Service for GDPR compliance operations."""
    
    def __init__(self, firestore_client: Optional[firestore.Client] = None):
        """Initialize GDPR service.
        
        Args:
            firestore_client: Firestore client instance
        """
        self.db = firestore_client
        
    # ========== Consent Management ==========
    
    async def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        status: ConsentStatus,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ConsentRecord:
        """Record user consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent
            status: Consent status
            ip_address: User's IP address
            user_agent: User's browser user agent
            
        Returns:
            ConsentRecord object
        """
        if not self.db:
            logger.warning("Firestore not available for consent recording")
            return None
            
        consent = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            status=status,
            granted_at=datetime.utcnow() if status == ConsentStatus.GRANTED else None,
            revoked_at=datetime.utcnow() if status == ConsentStatus.REVOKED else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store in Firestore
        consent_ref = self.db.collection('consent_records').document()
        consent_ref.set(consent.dict())
        
        # Log the action
        await self.log_audit(
            user_id=user_id,
            action=AuditLogAction.CONSENT_GRANTED if status == ConsentStatus.GRANTED else AuditLogAction.CONSENT_REVOKED,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"consent_type": consent_type.value}
        )
        
        return consent
    
    async def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        """Get all consent records for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of ConsentRecord objects
        """
        if not self.db:
            return []
            
        consents_ref = self.db.collection('consent_records').where('user_id', '==', user_id)
        consents = []
        
        for doc in consents_ref.stream():
            consent_data = doc.to_dict()
            consents.append(ConsentRecord(**consent_data))
            
        return consents
    
    # ========== Data Export (Right to Access) ==========
    
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all user data for GDPR compliance.
        
        Args:
            user_id: User ID
            
        Returns:
            UserDataExport object with all user data
        """
        if not self.db:
            logger.error("Firestore not available for data export")
            raise ValueError("Data export service unavailable")
        
        export_data = UserDataExport(
            user_id=user_id,
            export_date=datetime.utcnow(),
            profile_data={},
            quiz_results=[],
            tutor_conversations=[],
            uploaded_materials=[],
            consent_records=[],
            course_progress=[]
        )
        
        # Get user profile
        user_ref = self.db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            export_data.profile_data = user_doc.to_dict()
        
        # Get quiz results
        quiz_ref = self.db.collection('quiz_results').where('user_id', '==', user_id)
        for doc in quiz_ref.stream():
            export_data.quiz_results.append(doc.to_dict())
        
        # Get tutor conversations
        tutor_ref = self.db.collection('tutor_conversations').where('user_id', '==', user_id)
        for doc in tutor_ref.stream():
            export_data.tutor_conversations.append(doc.to_dict())
        
        # Get uploaded materials
        materials_ref = self.db.collection('user_materials').where('user_id', '==', user_id)
        for doc in materials_ref.stream():
            export_data.uploaded_materials.append(doc.to_dict())
        
        # Get consent records
        consent_records = await self.get_user_consents(user_id)
        export_data.consent_records = [c.dict() for c in consent_records]
        
        # Get course progress
        progress_ref = self.db.collection('course_progress').where('user_id', '==', user_id)
        for doc in progress_ref.stream():
            export_data.course_progress.append(doc.to_dict())
        
        # Log the export
        await self.log_audit(
            user_id=user_id,
            action=AuditLogAction.DATA_EXPORT,
            details={"export_size": len(json.dumps(export_data.dict()))}
        )
        
        return export_data
    
    # ========== Data Deletion (Right to be Forgotten) ==========
    
    async def delete_user_data(
        self,
        user_id: str,
        soft_delete: bool = True,
        retention_days: int = 30
    ) -> bool:
        """Delete all user data for GDPR compliance.
        
        Args:
            user_id: User ID
            soft_delete: If True, mark as deleted but retain for retention period
            retention_days: Days to retain data before permanent deletion
            
        Returns:
            True if successful
        """
        if not self.db:
            logger.error("Firestore not available for data deletion")
            raise ValueError("Data deletion service unavailable")
        
        deletion_timestamp = datetime.utcnow()
        permanent_deletion_date = deletion_timestamp + timedelta(days=retention_days)
        
        if soft_delete:
            # Mark user as deleted but retain data
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                'deleted': True,
                'deleted_at': deletion_timestamp,
                'permanent_deletion_date': permanent_deletion_date
            })
        else:
            # Permanently delete all user data
            await self._permanent_delete_user_data(user_id)
        
        # Log the deletion
        await self.log_audit(
            user_id=user_id,
            action=AuditLogAction.ACCOUNT_DELETED,
            details={
                "soft_delete": soft_delete,
                "retention_days": retention_days if soft_delete else 0
            }
        )
        
        return True
    
    async def _permanent_delete_user_data(self, user_id: str):
        """Permanently delete all user data from all collections.
        
        Args:
            user_id: User ID
        """
        # Collections to delete from
        collections = [
            'users',
            'quiz_results',
            'tutor_conversations',
            'user_materials',
            'consent_records',
            'course_progress',
            'flashcard_sessions',
            'assessment_results'
        ]
        
        for collection_name in collections:
            # Delete user document if it's the users collection
            if collection_name == 'users':
                self.db.collection(collection_name).document(user_id).delete()
            else:
                # Delete all documents where user_id matches
                docs = self.db.collection(collection_name).where('user_id', '==', user_id).stream()
                for doc in docs:
                    doc.reference.delete()
    
    # ========== Audit Logging ==========
    
    async def log_audit(
        self,
        action: AuditLogAction,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an audit event.
        
        Args:
            action: Action being logged
            user_id: User ID (if applicable)
            ip_address: IP address
            user_agent: User agent string
            details: Additional details
        """
        if not self.db:
            return
        
        audit_log = AuditLog(
            log_id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.db.collection('audit_logs').document(audit_log.log_id).set(audit_log.dict())

