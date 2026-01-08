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
    ) -> Optional[ConsentRecord]:
        """Record user consent.

        Args:
            user_id: User ID
            consent_type: Type of consent
            status: Consent status
            ip_address: User's IP address
            user_agent: User's browser user agent

        Returns:
            ConsentRecord object or None if Firestore unavailable

        Raises:
            ValueError: If user_id is empty or invalid
            Exception: If Firestore operation fails
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not self.db:
            logger.error("Firestore not available for consent recording")
            raise Exception("Database unavailable")

        try:
            consent = ConsentRecord(
                user_id=user_id.strip(),
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

            logger.info(f"Consent recorded for user {user_id}: {consent_type.value} - {status.value}")
            return consent

        except Exception as e:
            logger.error(f"Error recording consent for user {user_id}: {e}", exc_info=True)
            raise
    
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

        Raises:
            ValueError: If user_id is empty or database unavailable
            Exception: If export operation fails
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not self.db:
            logger.error("Firestore not available for data export")
            raise ValueError("Data export service unavailable")

        try:
            export_data = UserDataExport(
                user_id=user_id.strip(),
                export_date=datetime.utcnow(),
                profile_data={},
                quiz_results=[],
                tutor_conversations=[],
                uploaded_materials=[],
                consent_records=[],
                course_progress=[]
            )

            # Get user profile with error handling
            try:
                user_ref = self.db.collection('users').document(user_id)
                user_doc = user_ref.get()
                if user_doc.exists:
                    export_data.profile_data = user_doc.to_dict()
                else:
                    logger.warning(f"User profile not found for {user_id}")
            except Exception as e:
                logger.error(f"Error fetching user profile: {e}")
                export_data.profile_data = {"error": "Failed to fetch profile"}

            # Get quiz results with error handling
            try:
                quiz_ref = self.db.collection('quiz_results').where('user_id', '==', user_id)
                for doc in quiz_ref.stream():
                    export_data.quiz_results.append(doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching quiz results: {e}")

            # Get tutor conversations with error handling
            try:
                tutor_ref = self.db.collection('tutor_conversations').where('user_id', '==', user_id)
                for doc in tutor_ref.stream():
                    export_data.tutor_conversations.append(doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching tutor conversations: {e}")

            # Get uploaded materials with error handling
            try:
                materials_ref = self.db.collection('user_materials').where('user_id', '==', user_id)
                for doc in materials_ref.stream():
                    export_data.uploaded_materials.append(doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching uploaded materials: {e}")

            # Get consent records with error handling
            try:
                consent_records = await self.get_user_consents(user_id)
                export_data.consent_records = [c.dict() for c in consent_records]
            except Exception as e:
                logger.error(f"Error fetching consent records: {e}")

            # Get course progress with error handling
            try:
                progress_ref = self.db.collection('course_progress').where('user_id', '==', user_id)
                for doc in progress_ref.stream():
                    export_data.course_progress.append(doc.to_dict())
            except Exception as e:
                logger.error(f"Error fetching course progress: {e}")

            # Log the export
            try:
                export_size = len(json.dumps(export_data.dict(), default=str))
                await self.log_audit(
                    user_id=user_id,
                    action=AuditLogAction.DATA_EXPORT,
                    details={"export_size": export_size}
                )
            except Exception as e:
                logger.error(f"Error logging export audit: {e}")

            logger.info(f"Data export completed for user {user_id}")
            return export_data

        except Exception as e:
            logger.error(f"Error exporting user data for {user_id}: {e}", exc_info=True)
            raise
    
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

        Raises:
            ValueError: If user_id is empty or database unavailable
            Exception: If deletion operation fails
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not self.db:
            logger.error("Firestore not available for data deletion")
            raise ValueError("Data deletion service unavailable")

        if retention_days < 0:
            raise ValueError("retention_days must be non-negative")

        try:
            deletion_timestamp = datetime.utcnow()
            permanent_deletion_date = deletion_timestamp + timedelta(days=retention_days)

            if soft_delete:
                # Mark user as deleted but retain data
                try:
                    user_ref = self.db.collection('users').document(user_id)
                    user_ref.update({
                        'deleted': True,
                        'deleted_at': deletion_timestamp,
                        'permanent_deletion_date': permanent_deletion_date
                    })
                    logger.info(f"User {user_id} marked for deletion (soft delete)")
                except Exception as e:
                    logger.error(f"Error marking user for deletion: {e}")
                    raise
            else:
                # Permanently delete all user data
                await self._permanent_delete_user_data(user_id)
                logger.info(f"User {user_id} permanently deleted")

            # Log the deletion
            try:
                await self.log_audit(
                    user_id=user_id,
                    action=AuditLogAction.ACCOUNT_DELETED,
                    details={
                        "soft_delete": soft_delete,
                        "retention_days": retention_days if soft_delete else 0,
                        "permanent_deletion_date": permanent_deletion_date.isoformat() if soft_delete else None
                    }
                )
            except Exception as e:
                logger.error(f"Error logging deletion audit: {e}")

            return True

        except Exception as e:
            logger.error(f"Error deleting user data for {user_id}: {e}", exc_info=True)
            raise
    
    async def _permanent_delete_user_data(self, user_id: str):
        """Permanently delete all user data from all collections.

        Args:
            user_id: User ID

        Raises:
            Exception: If deletion from any collection fails
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

        deletion_errors = []

        for collection_name in collections:
            try:
                # Delete user document if it's the users collection
                if collection_name == 'users':
                    self.db.collection(collection_name).document(user_id).delete()
                    logger.info(f"Deleted user document from {collection_name}")
                else:
                    # Delete all documents where user_id matches
                    docs = self.db.collection(collection_name).where('user_id', '==', user_id).stream()
                    count = 0
                    for doc in docs:
                        doc.reference.delete()
                        count += 1
                    if count > 0:
                        logger.info(f"Deleted {count} documents from {collection_name}")
            except Exception as e:
                error_msg = f"Error deleting from {collection_name}: {e}"
                logger.error(error_msg)
                deletion_errors.append(error_msg)

        if deletion_errors:
            raise Exception(f"Errors during permanent deletion: {'; '.join(deletion_errors)}")
    
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

