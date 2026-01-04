"""Course Service for managing courses in Firestore.

This service provides CRUD operations for courses, weeks, and legal skills
using Firestore as the data store.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from google.cloud.firestore_v1 import FieldFilter

from app.models.course_models import (
    Course,
    CourseSummary,
    CourseCreate,
    CourseUpdate,
    Week,
    WeekCreate,
    LegalSkill,
)
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Collection names
COURSES_COLLECTION = "courses"
WEEKS_SUBCOLLECTION = "weeks"
LEGAL_SKILLS_SUBCOLLECTION = "legalSkills"


class CourseService:
    """Service for managing courses in Firestore."""

    def __init__(self):
        """Initialize the course service with Firestore client."""
        self.db = get_firestore_client()
        if self.db is None:
            raise RuntimeError(
                "Firestore client not available. "
                "Ensure ADC is configured: gcloud auth application-default login"
            )

    # ========================================================================
    # Course CRUD Operations
    # ========================================================================

    def get_all_courses(self, include_inactive: bool = False) -> List[CourseSummary]:
        """
        Get all courses as summaries.

        Args:
            include_inactive: Whether to include inactive courses

        Returns:
            List of course summaries
        """
        courses_ref = self.db.collection(COURSES_COLLECTION)

        if not include_inactive:
            courses_ref = courses_ref.where(filter=FieldFilter("active", "==", True))

        courses = []
        for doc in courses_ref.stream():
            data = doc.to_dict()
            # Count weeks in subcollection
            week_count = len(list(doc.reference.collection(WEEKS_SUBCOLLECTION).stream()))

            courses.append(CourseSummary(
                id=doc.id,
                name=data.get("name", ""),
                program=data.get("program"),
                institution=data.get("institution"),
                academicYear=data.get("academicYear", ""),
                weekCount=week_count,
                active=data.get("active", True)
            ))

        logger.info("Retrieved %d courses", len(courses))
        return courses

    def get_course(self, course_id: str, include_weeks: bool = True) -> Optional[Course]:
        """
        Get a course by ID.

        Args:
            course_id: The course ID
            include_weeks: Whether to include weeks subcollection

        Returns:
            Course object or None if not found
        """
        doc_ref = self.db.collection(COURSES_COLLECTION).document(course_id)
        doc = doc_ref.get()

        if not doc.exists:
            logger.warning("Course not found: %s", course_id)
            return None

        data = doc.to_dict()

        # Build course object
        course = Course(
            id=doc.id,
            name=data.get("name", ""),
            program=data.get("program"),
            institution=data.get("institution"),
            academicYear=data.get("academicYear", ""),
            totalPoints=data.get("totalPoints"),
            passingThreshold=data.get("passingThreshold"),
            components=data.get("components", []),
            materialSubjects=data.get("materialSubjects", []),
            abbreviations=data.get("abbreviations", {}),
            externalResources=data.get("externalResources"),
            materials=data.get("materials"),
            active=data.get("active", True),
            createdAt=data.get("createdAt", datetime.utcnow()),
            updatedAt=data.get("updatedAt", datetime.utcnow()),
        )

        # Load weeks if requested
        if include_weeks:
            course.weeks = self.get_course_weeks(course_id)
            course.legalSkills = self.get_legal_skills(course_id)

        logger.info("Retrieved course: %s", course_id)
        return course

    def create_course(self, course_data: CourseCreate) -> Course:
        """
        Create a new course.

        Args:
            course_data: Course creation data

        Returns:
            Created course object
        """
        doc_ref = self.db.collection(COURSES_COLLECTION).document(course_data.id)

        # Check if already exists
        if doc_ref.get().exists:
            raise ValueError(f"Course already exists: {course_data.id}")

        now = datetime.utcnow()
        data = {
            **course_data.model_dump(),
            "active": True,
            "createdAt": now,
            "updatedAt": now,
        }

        doc_ref.set(data)
        logger.info("Created course: %s", course_data.id)

        return self.get_course(course_data.id, include_weeks=False)

    def update_course(self, course_id: str, updates: CourseUpdate) -> Optional[Course]:
        """
        Update a course.

        Args:
            course_id: The course ID
            updates: Fields to update

        Returns:
            Updated course or None if not found
        """
        doc_ref = self.db.collection(COURSES_COLLECTION).document(course_id)

        if not doc_ref.get().exists:
            logger.warning("Course not found for update: %s", course_id)
            return None

        # Only include non-None fields
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
        update_data["updatedAt"] = datetime.utcnow()

        doc_ref.update(update_data)
        logger.info("Updated course: %s", course_id)

        return self.get_course(course_id, include_weeks=False)

    def deactivate_course(self, course_id: str) -> bool:
        """
        Deactivate a course (soft delete).

        Args:
            course_id: The course ID

        Returns:
            True if deactivated, False if not found
        """
        doc_ref = self.db.collection(COURSES_COLLECTION).document(course_id)

        if not doc_ref.get().exists:
            return False

        doc_ref.update({
            "active": False,
            "updatedAt": datetime.utcnow()
        })
        logger.info("Deactivated course: %s", course_id)
        return True

    # ========================================================================
    # Week Operations
    # ========================================================================

    def get_course_weeks(self, course_id: str) -> List[Week]:
        """
        Get all weeks for a course.

        Args:
            course_id: The course ID

        Returns:
            List of weeks sorted by week number
        """
        weeks_ref = (
            self.db.collection(COURSES_COLLECTION)
            .document(course_id)
            .collection(WEEKS_SUBCOLLECTION)
        )

        weeks = []
        for doc in weeks_ref.stream():
            data = doc.to_dict()
            weeks.append(Week(**data))

        # Sort by week number
        weeks.sort(key=lambda w: w.weekNumber)
        logger.info("Retrieved %d weeks for course %s", len(weeks), course_id)
        return weeks

    def get_week(self, course_id: str, week_number: int) -> Optional[Week]:
        """
        Get a specific week.

        Args:
            course_id: The course ID
            week_number: The week number

        Returns:
            Week object or None if not found
        """
        doc_ref = (
            self.db.collection(COURSES_COLLECTION)
            .document(course_id)
            .collection(WEEKS_SUBCOLLECTION)
            .document(f"week-{week_number}")
        )

        doc = doc_ref.get()
        if not doc.exists:
            return None

        return Week(**doc.to_dict())

    def upsert_week(self, course_id: str, week_data: WeekCreate) -> Week:
        """
        Create or update a week.

        Args:
            course_id: The course ID
            week_data: Week data

        Returns:
            Created/updated week
        """
        doc_ref = (
            self.db.collection(COURSES_COLLECTION)
            .document(course_id)
            .collection(WEEKS_SUBCOLLECTION)
            .document(f"week-{week_data.weekNumber}")
        )

        doc_ref.set(week_data.model_dump())

        # Update course's updatedAt
        self.db.collection(COURSES_COLLECTION).document(course_id).update({
            "updatedAt": datetime.utcnow()
        })

        logger.info("Upserted week %d for course %s", week_data.weekNumber, course_id)
        return Week(**week_data.model_dump())

    def delete_week(self, course_id: str, week_number: int) -> bool:
        """
        Delete a week.

        Args:
            course_id: The course ID
            week_number: The week number

        Returns:
            True if deleted, False if not found
        """
        doc_ref = (
            self.db.collection(COURSES_COLLECTION)
            .document(course_id)
            .collection(WEEKS_SUBCOLLECTION)
            .document(f"week-{week_number}")
        )

        if not doc_ref.get().exists:
            return False

        doc_ref.delete()
        logger.info("Deleted week %d from course %s", week_number, course_id)
        return True

    # ========================================================================
    # Legal Skills Operations
    # ========================================================================

    def get_legal_skills(self, course_id: str) -> Dict[str, LegalSkill]:
        """
        Get all legal skills for a course.

        Args:
            course_id: The course ID

        Returns:
            Dictionary of skill_id -> LegalSkill
        """
        skills_ref = (
            self.db.collection(COURSES_COLLECTION)
            .document(course_id)
            .collection(LEGAL_SKILLS_SUBCOLLECTION)
        )

        skills = {}
        for doc in skills_ref.stream():
            data = doc.to_dict()
            skills[doc.id] = LegalSkill(**data)

        logger.info("Retrieved %d legal skills for course %s", len(skills), course_id)
        return skills

    def upsert_legal_skill(
        self, course_id: str, skill_id: str, skill: LegalSkill
    ) -> LegalSkill:
        """
        Create or update a legal skill.

        Args:
            course_id: The course ID
            skill_id: The skill identifier (e.g., "ecthrCaseAnalysis")
            skill: The legal skill data

        Returns:
            Created/updated legal skill
        """
        doc_ref = (
            self.db.collection(COURSES_COLLECTION)
            .document(course_id)
            .collection(LEGAL_SKILLS_SUBCOLLECTION)
            .document(skill_id)
        )

        doc_ref.set(skill.model_dump())

        # Update course's updatedAt
        self.db.collection(COURSES_COLLECTION).document(course_id).update({
            "updatedAt": datetime.utcnow()
        })

        logger.info("Upserted legal skill '%s' for course %s", skill_id, course_id)
        return skill


# ============================================================================
# Singleton Instance
# ============================================================================

_course_service: Optional[CourseService] = None


def get_course_service() -> CourseService:
    """Get or create CourseService singleton."""
    global _course_service
    if _course_service is None:
        _course_service = CourseService()
    return _course_service

