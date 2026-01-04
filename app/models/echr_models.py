"""Pydantic models for ECHR (European Court of Human Rights) case law.

These models represent case law data retrieved from the ECHR Open Data API
(https://echr-opendata.eu/api/v1/) and cached locally.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Core ECHR Case Models
# ============================================================================


class ECHRParty(BaseModel):
    """Party involved in an ECHR case."""

    id: Optional[str] = None
    name: str
    role: Optional[str] = None  # applicant, respondent, third-party


class ECHRRepresentative(BaseModel):
    """Legal representative in an ECHR case."""

    id: Optional[str] = None
    name: str
    role: Optional[str] = None


class ECHRConclusion(BaseModel):
    """Conclusion/finding in an ECHR case."""

    id: Optional[str] = None
    article: Optional[str] = None
    base_article: Optional[str] = None
    type: Optional[str] = None  # violation, no-violation, preliminary-objection, etc.
    description: Optional[str] = None
    details: Optional[str] = None


class ECHRDocumentSection(BaseModel):
    """Section within an ECHR document (e.g., facts, law, operative provisions)."""

    section_name: str
    content: str
    elements: List["ECHRDocumentSection"] = []


class ECHRDocument(BaseModel):
    """Document associated with an ECHR case (judgment, decision, etc.)."""

    doc_type: str  # JUDGMENT, DECISION, COMMUNICATED, etc.
    doc_id: Optional[str] = None
    language: str = "ENG"
    content: Optional[str] = None
    sections: Dict[str, str] = Field(default_factory=dict)  # section_name -> text


class ECHRCase(BaseModel):
    """Complete ECHR case record.

    This is the primary data model for case law from the ECHR Open Data API.
    Fields are based on the HUDOC database structure.
    """

    # Primary identifiers
    item_id: str = Field(..., description="Unique HUDOC item identifier")
    application_number: Optional[str] = Field(None, alias="appno", description="Application number (e.g., 12345/67)")
    ecli: Optional[str] = Field(None, description="European Case Law Identifier")

    # Case name and title
    case_name: Optional[str] = Field(None, alias="docname", description="Full case name")
    title: Optional[str] = None

    # Document type and classification
    document_type: Optional[str] = Field(None, alias="doctype", description="Document type code")
    document_type_branch: Optional[str] = Field(None, alias="doctypebranch")
    type_description: Optional[str] = Field(None, alias="typedescription")
    importance_level: Optional[int] = Field(None, alias="importance", ge=1, le=4, description="Case importance (1=key, 4=low)")

    # Dates
    judgment_date: Optional[datetime] = Field(None, alias="judgementdate")
    decision_date: Optional[datetime] = Field(None, alias="decisiondate")
    introduction_date: Optional[datetime] = Field(None, alias="introductiondate")
    kp_date: Optional[datetime] = Field(None, alias="kpdate", description="Key phrase date")

    # Respondent state
    respondent_state: Optional[str] = Field(None, alias="respondent")
    respondent_order: Optional[int] = Field(None, alias="respondentOrderEng")

    # Articles and legal basis
    articles: List[str] = Field(default_factory=list, alias="article", description="Convention articles invoked")
    separate_opinion: Optional[bool] = Field(None, alias="separateopinion")
    rules_of_court: Optional[str] = Field(None, alias="rulesofcourt")

    # Conclusions and findings
    conclusion: Optional[str] = None
    violations: List[str] = Field(default_factory=list, alias="violation")
    non_violations: List[str] = Field(default_factory=list, alias="nonviolation")
    conclusions: List[ECHRConclusion] = Field(default_factory=list)

    # Classification
    scl: Optional[str] = Field(None, description="Subject classification")
    issue: Optional[str] = None
    kp_thesaurus: Optional[str] = Field(None, alias="kpthesaurus", description="Key phrase thesaurus terms")

    # Parties and representatives
    parties: List[ECHRParty] = Field(default_factory=list)
    representatives: List[ECHRRepresentative] = Field(default_factory=list)
    represented_by: Optional[str] = Field(None, alias="representedby")

    # Origin and publication
    originating_body: Optional[str] = Field(None, alias="originatingbody")
    published_by: Optional[str] = Field(None, alias="publishedby")
    external_sources: Optional[str] = Field(None, alias="externalsources")

    # Document collections
    document_collection_id: Optional[str] = Field(None, alias="documentcollectionid")
    document_collection_id2: Optional[str] = Field(None, alias="documentcollectionid2")

    # Language
    language: str = Field("ENG", alias="languageisocode")

    # Linked cases
    cited_apps: List[str] = Field(default_factory=list, description="Cited application numbers")

    # Full text content (loaded separately)
    documents: List[ECHRDocument] = Field(default_factory=list)

    # Entities extracted from the case
    entities: List[Dict[str, Any]] = Field(default_factory=list)

    # Cache metadata
    cached_at: Optional[datetime] = Field(None, description="When this record was cached")
    last_updated: Optional[datetime] = Field(None, description="Last API sync time")

    class Config:
        """Pydantic config."""

        populate_by_name = True  # Allow both field names and aliases


class ECHRCaseSummary(BaseModel):
    """Lightweight summary of an ECHR case for list views."""

    item_id: str
    application_number: Optional[str] = None
    case_name: Optional[str] = None
    respondent_state: Optional[str] = None
    judgment_date: Optional[datetime] = None
    decision_date: Optional[datetime] = None
    articles: List[str] = Field(default_factory=list)
    importance_level: Optional[int] = None
    document_type: Optional[str] = None


# ============================================================================
# Classification and Metadata Models
# ============================================================================


class ECHRSubjectClassification(BaseModel):
    """Subject classification (SCL) from ECHR thesaurus."""

    id: str
    code: Optional[str] = None
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None


class ECHRArticle(BaseModel):
    """ECHR Convention article reference."""

    number: str  # e.g., "6", "6-1", "P1-1"
    title: str
    description: Optional[str] = None


# ============================================================================
# API Request/Response Models
# ============================================================================


class ECHRSearchRequest(BaseModel):
    """Request model for searching ECHR cases."""

    query: Optional[str] = Field(None, description="Free text search query")
    articles: Optional[List[str]] = Field(None, description="Filter by Convention articles")
    respondent: Optional[str] = Field(None, description="Filter by respondent state")
    date_from: Optional[datetime] = Field(None, description="Judgment/decision date from")
    date_to: Optional[datetime] = Field(None, description="Judgment/decision date to")
    importance: Optional[int] = Field(None, ge=1, le=4, description="Filter by importance level")
    document_type: Optional[str] = Field(None, description="Filter by document type")
    violation: Optional[bool] = Field(None, description="Filter cases with violations")
    use_cache: bool = Field(True, description="Use local cache (faster, may be slightly outdated)")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Results per page")


class ECHRSearchResponse(BaseModel):
    """Response model for case search results."""

    cases: List[ECHRCaseSummary]
    total: int
    page: int
    limit: int
    has_more: bool


class ECHRCaseResponse(BaseModel):
    """Response model for a single case lookup."""

    case: ECHRCase
    status: str = "success"


class ECHRSyncStatus(BaseModel):
    """Status of ECHR database synchronization."""

    last_sync: Optional[datetime] = None
    total_cases: int = 0
    cases_synced: int = 0
    sync_in_progress: bool = False
    next_sync: Optional[datetime] = None
    error: Optional[str] = None


class ECHRStatsResponse(BaseModel):
    """Statistics from the ECHR Open Data API."""

    total_cases: int
    last_update: Optional[datetime] = None
    build_version: Optional[str] = None
    respondent_states: List[str] = Field(default_factory=list)
    document_types: List[str] = Field(default_factory=list)


# Enable forward references for nested models
ECHRDocumentSection.model_rebuild()
