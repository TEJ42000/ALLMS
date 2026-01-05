"""Pydantic models for Course Management System.

Based on the schema from Materials/Course_Materials/LLS/LLS Essential/course_data.json.
These models represent the course structure stored in Firestore.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Course Components
# ============================================================================


class CourseComponent(BaseModel):
    """Part of a course (e.g., Part A: Law, Part B: Legal Skills)."""

    id: str
    name: str
    maxPoints: int
    description: Optional[str] = None


class KeyConcept(BaseModel):
    """Legal concept with definition and source."""

    term: str
    definition: str
    source: Optional[str] = None  # Made optional for UI flexibility
    citation: Optional[str] = None


class DecisionModelStep(BaseModel):
    """Single step in a decision model framework."""

    stepNumber: int
    question: str
    legalBasis: Optional[str] = None
    guidance: str


class DecisionModel(BaseModel):
    """Legal decision-making framework (e.g., 8-Question Framework)."""

    name: str
    description: Optional[str] = None
    steps: List[DecisionModelStep] = []


class WeekMaterial(BaseModel):
    """Material reference for a specific week."""

    type: str  # reader, lecture, reading, case, etc.
    file: str  # Path relative to Materials/
    title: Optional[str] = None  # Display title
    chapters: Optional[List[str]] = None
    fileId: Optional[str] = None  # Link to file_ids.json


class Week(BaseModel):
    """Course week with topics, materials, and concepts."""

    weekNumber: int
    title: str
    topics: List[str] = []
    materials: List[WeekMaterial] = []
    keyConcepts: List[KeyConcept] = []
    decisionModel: Optional[DecisionModel] = None


# ============================================================================
# Legal Skills
# ============================================================================


class LegalSkillStep(BaseModel):
    """Single step in a legal skill framework."""

    stepNumber: int
    question: str
    legalBasis: Optional[str] = None
    guidance: str
    citation: Optional[str] = None


class CriticalDistinction(BaseModel):
    """Critical distinction in legal analysis."""

    concept: str
    explanation: str


class ExampleCase(BaseModel):
    """Example case reference."""

    file: Optional[str] = None
    citation: str


class LegalSkill(BaseModel):
    """Legal skill framework (e.g., ECtHR Case Analysis)."""

    name: str
    description: Optional[str] = None
    steps: List[LegalSkillStep] = []
    criticalDistinctions: List[CriticalDistinction] = []
    exampleCase: Optional[ExampleCase] = None


# ============================================================================
# Materials Registry
# ============================================================================


class CoreTextbook(BaseModel):
    """Core textbook reference."""

    title: str
    file: str
    size: Optional[str] = None
    type: str = "primary"
    description: Optional[str] = None


class Lecture(BaseModel):
    """Lecture material reference."""

    title: str
    week: Optional[int] = None
    file: str
    size: Optional[str] = None


class Reading(BaseModel):
    """Reading material reference."""

    title: str
    week: Optional[int] = None
    file: str
    size: Optional[str] = None


class CaseStudy(BaseModel):
    """Case study reference."""

    title: str
    court: str
    appNumber: Optional[str] = None
    file: str
    size: Optional[str] = None
    relevantRights: List[str] = []
    topics: List[str] = []


class MockExam(BaseModel):
    """Mock exam reference."""

    title: str
    file: str
    size: Optional[str] = None
    type: str = "practice"


class MaterialsRegistry(BaseModel):
    """Complete materials registry for a course."""

    coreTextbooks: List[CoreTextbook] = []
    lectures: List[Lecture] = []
    readings: List[Reading] = []
    caseStudies: List[CaseStudy] = []
    mockExams: List[MockExam] = []


# ============================================================================
# External Resources
# ============================================================================


class LegalDatabase(BaseModel):
    """External legal database reference."""

    name: str
    url: str
    coverage: str


class ExternalResources(BaseModel):
    """External resources for a course."""

    legalDatabases: List[LegalDatabase] = []


# ============================================================================
# Statutory Interpretation & Legal Skills Configuration
# ============================================================================


class InterpretationMethod(BaseModel):
    """Statutory interpretation method."""

    name: str
    description: str
    when: Optional[str] = None


class CitationFormat(BaseModel):
    """Legal citation format."""

    type: str
    format: str
    example: str
    notes: Optional[str] = None


class SourceHierarchyLevel(BaseModel):
    """Source hierarchy level for legal research."""

    level: int
    type: str
    sources: List[str] = []
    authority: str


class LegalSkillsConfig(BaseModel):
    """Configuration for legal skills section."""

    statutoryInterpretation: Optional[Dict[str, List[InterpretationMethod]]] = None
    legalCitation: Optional[Dict[str, List[CitationFormat]]] = None
    legalResearch: Optional[Dict[str, List[SourceHierarchyLevel]]] = None


# ============================================================================
# Unified Course Materials (Issue #51)
# ============================================================================


class CourseMaterial(BaseModel):
    """Unified material model for both scanned and uploaded files.

    Stored in Firestore: courses/{course_id}/materials/{material_id}

    This replaces both the old UploadedMaterial model and the MaterialsRegistry
    nested structure, providing a single queryable collection for all materials.
    """

    id: str  # Hash of storagePath for deduplication

    # File info
    filename: str  # Original filename
    storagePath: str  # Path relative to Materials/ (e.g., "Course_Materials/LLS/Readings/file.pdf")
    fileSize: int  # Bytes
    fileType: str  # 'pdf', 'docx', 'slide_archive', 'image', 'text', etc.
    mimeType: Optional[str] = None

    # Categorization
    tier: str  # 'syllabus', 'course_materials', 'supplementary'
    category: Optional[str] = None  # 'lecture', 'reading', 'case', 'textbook', 'exam', 'other'

    # Display metadata
    title: str  # Display title (AI-enhanced or parsed from filename)
    description: Optional[str] = None
    weekNumber: Optional[int] = None  # Link to specific week (extracted from filename or manual)

    # Source tracking
    source: str  # 'scanned' or 'uploaded'
    uploadedBy: Optional[str] = None  # User ID (for uploaded files)

    # Text extraction
    textExtracted: bool = False
    extractedText: Optional[str] = None  # Extracted text content
    textLength: int = 0
    extractionError: Optional[str] = None

    # AI Summary
    summary: Optional[str] = None  # LLM-generated summary
    summaryGenerated: bool = False

    # Anthropic Files API integration
    anthropicFileId: Optional[str] = None  # Anthropic file ID (e.g., "file_abc123...")
    anthropicFileExpiry: Optional[datetime] = None  # When the file expires in Anthropic
    anthropicUploadedAt: Optional[datetime] = None  # When last uploaded to Anthropic
    anthropicUploadError: Optional[str] = None  # Last upload error message

    # Timestamps
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Legacy model - kept for backward compatibility during migration
class UploadedMaterial(BaseModel):
    """DEPRECATED: Use CourseMaterial instead.

    Uploaded material record for course documents.
    This model is kept for backward compatibility during migration.
    """

    id: str  # UUID
    filename: str  # Original filename
    storagePath: str  # Path in Materials/
    tier: str  # 'syllabus', 'course_materials', 'supplementary'
    category: Optional[str] = None  # 'lecture', 'reading', 'case', etc.
    fileType: str  # 'pdf', 'docx', 'image', etc.
    fileSize: int  # Bytes
    mimeType: str
    uploadedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uploadedBy: Optional[str] = None  # User ID when auth is implemented

    # Text extraction
    textExtracted: bool = False
    extractedText: Optional[str] = None  # Stored text (or reference to external storage)
    textLength: Optional[int] = None
    extractionError: Optional[str] = None

    # Metadata
    title: Optional[str] = None  # Display title (defaults to filename)
    description: Optional[str] = None
    weekNumber: Optional[int] = None  # Link to specific week

    # AI-generated summary
    summary: Optional[str] = None  # LLM-generated summary of document content
    summaryGenerated: bool = False  # Whether summary was successfully generated


# ============================================================================
# Main Course Model
# ============================================================================


class CourseMetadata(BaseModel):
    """Core course metadata (stored in main document)."""

    id: str
    name: str
    program: Optional[str] = None
    institution: Optional[str] = None
    academicYear: str
    totalPoints: Optional[int] = None
    passingThreshold: Optional[int] = None
    components: List[CourseComponent] = []


class Course(BaseModel):
    """Complete course data model.

    This is the full course structure including:
    - Course metadata
    - Weeks with topics, materials, and key concepts
    - Legal skills frameworks
    - Materials registry
    - Abbreviations and external resources

    In Firestore:
    - Main document: courses/{course_id} contains metadata, abbreviations, etc.
    - Subcollection: courses/{course_id}/weeks contains week documents
    - Subcollection: courses/{course_id}/legalSkills contains skill documents
    """

    # Core metadata
    id: str
    name: str
    program: Optional[str] = None
    institution: Optional[str] = None
    academicYear: str
    totalPoints: Optional[int] = None
    passingThreshold: Optional[int] = None
    components: List[CourseComponent] = []

    # Material linking (maps to subjects in file_ids.json)
    materialSubjects: List[str] = []

    # Abbreviations dictionary
    abbreviations: Dict[str, str] = {}

    # External resources
    externalResources: Optional[ExternalResources] = None

    # Materials registry
    materials: Optional[MaterialsRegistry] = None

    # Status
    active: bool = True

    # Timestamps
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # These are typically loaded from subcollections
    weeks: List[Week] = []
    legalSkills: Dict[str, LegalSkill] = {}


# ============================================================================
# API Request/Response Models
# ============================================================================


class CourseCreate(BaseModel):
    """Request model for creating a new course."""

    id: str
    name: str
    program: Optional[str] = None
    institution: Optional[str] = None
    academicYear: str
    totalPoints: Optional[int] = None
    passingThreshold: Optional[int] = None
    components: List[CourseComponent] = []
    materialSubjects: List[str] = []
    abbreviations: Dict[str, str] = {}


class CourseUpdate(BaseModel):
    """Request model for updating a course."""

    name: Optional[str] = None
    program: Optional[str] = None
    institution: Optional[str] = None
    academicYear: Optional[str] = None
    totalPoints: Optional[int] = None
    passingThreshold: Optional[int] = None
    components: Optional[List[CourseComponent]] = None
    materialSubjects: Optional[List[str]] = None
    abbreviations: Optional[Dict[str, str]] = None
    materials: Optional[MaterialsRegistry] = None
    active: Optional[bool] = None


class CourseSummary(BaseModel):
    """Summary view of a course for list endpoints."""

    id: str
    name: str
    program: Optional[str] = None
    institution: Optional[str] = None
    academicYear: str
    weekCount: int = 0
    active: bool = True


class WeekCreate(BaseModel):
    """Request model for creating/updating a week."""

    weekNumber: int
    title: str
    topics: List[str] = []
    materials: List[WeekMaterial] = []
    keyConcepts: List[KeyConcept] = []
    decisionModel: Optional[DecisionModel] = None

