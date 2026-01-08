"""
GDPR Compliance Models

Models for GDPR compliance features including consent management,
data subject requests, and audit logging.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ConsentType(str, Enum):
    """Types of consent that can be granted or revoked."""
    ESSENTIAL = "essential"  # Required for basic functionality
    FUNCTIONAL = "functional"  # Enhanced features
    ANALYTICS = "analytics"  # Usage analytics
    AI_TUTORING = "ai_tutoring"  # AI-powered features
    MARKETING = "marketing"  # Marketing communications


class ConsentStatus(str, Enum):
    """Status of user consent."""
    GRANTED = "granted"
    REVOKED = "revoked"
    PENDING = "pending"


class ConsentRecord(BaseModel):
    """Record of user consent for data processing."""
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    consent_version: str = "1.0"  # Version of privacy policy/terms
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    class Config:
        use_enum_values = True


class DataSubjectRequestType(str, Enum):
    """Types of GDPR data subject requests."""
    ACCESS = "access"  # Right to access
    ERASURE = "erasure"  # Right to be forgotten
    RECTIFICATION = "rectification"  # Right to rectification
    PORTABILITY = "portability"  # Right to data portability
    OBJECTION = "objection"  # Right to object
    RESTRICTION = "restriction"  # Right to restriction of processing


class RequestStatus(str, Enum):
    """Status of data subject request."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DataSubjectRequest(BaseModel):
    """GDPR data subject request."""
    request_id: str
    user_id: str
    request_type: DataSubjectRequestType
    status: RequestStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    requested_by_email: str
    notes: Optional[str] = None
    admin_notes: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AuditLogAction(str, Enum):
    """Types of actions that are audited."""
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_DELETED = "account_deleted"
    DATA_ACCESS = "data_access"
    PRIVACY_POLICY_VIEWED = "privacy_policy_viewed"
    TERMS_VIEWED = "terms_viewed"


class AuditLog(BaseModel):
    """Audit log entry for GDPR compliance."""
    log_id: str
    user_id: Optional[str] = None
    action: AuditLogAction
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class UserDataExport(BaseModel):
    """User data export package."""
    user_id: str
    export_date: datetime
    profile_data: Dict[str, Any]
    quiz_results: List[Dict[str, Any]] = []
    tutor_conversations: List[Dict[str, Any]] = []
    uploaded_materials: List[Dict[str, Any]] = []
    consent_records: List[Dict[str, Any]] = []
    course_progress: List[Dict[str, Any]] = []


class CookieConsent(BaseModel):
    """Cookie consent preferences."""
    user_id: Optional[str] = None  # None for anonymous users
    session_id: str
    essential: bool = True  # Always true, required for functionality
    functional: bool = False
    analytics: bool = False
    timestamp: datetime
    ip_address: Optional[str] = None


class PrivacySettings(BaseModel):
    """User privacy settings."""
    user_id: str
    ai_tutoring_enabled: bool = True
    analytics_enabled: bool = True
    marketing_emails_enabled: bool = False
    data_retention_days: int = 365  # How long to keep user data
    updated_at: datetime


class DataRetentionPolicy(BaseModel):
    """Data retention policy configuration."""
    data_type: str  # e.g., "quiz_results", "tutor_conversations"
    retention_days: int
    auto_delete: bool = True
    description: str


class GDPRExportRequest(BaseModel):
    """Request for GDPR data export."""
    user_id: str
    email: str
    include_quiz_results: bool = True
    include_tutor_conversations: bool = True
    include_uploaded_materials: bool = True
    include_consent_records: bool = True


class GDPRDeleteRequest(BaseModel):
    """Request for GDPR account deletion."""
    user_id: str
    email: str
    confirmation_token: str
    delete_all_data: bool = True
    reason: Optional[str] = None

