"""Course Service for managing courses in Firestore.

This service provides CRUD operations for courses, weeks, and legal skills
using Firestore as the data store.

Firestore Index Requirements:
    The following composite indexes are required for production:
    - Collection: courses, Fields: active (Ascending)

    See firestore.indexes.json for the full index configuration.
"""

import functools
import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from google.api_core import exceptions as google_exceptions
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

# ============================================================================
# Custom Exceptions
# ============================================================================


class CourseServiceError(Exception):
    """Base exception for CourseService errors."""
    pass


class CourseNotFoundError(CourseServiceError):
    """Raised when a course is not found."""
    pass


class CourseAlreadyExistsError(CourseServiceError):
    """Raised when attempting to create a course that already exists."""
    pass


class ServiceValidationError(CourseServiceError):
    """Raised when a validation error occurs in the service."""
    pass


class FirestoreOperationError(CourseServiceError):
    """Raised when a Firestore operation fails."""
    pass


logger = logging.getLogger(__name__)

# Collection names
COURSES_COLLECTION = "courses"
WEEKS_SUBCOLLECTION = "weeks"
LEGAL_SKILLS_SUBCOLLECTION = "legalSkills"

# Validation patterns
# Course IDs: alphanumeric, hyphens, underscores, 1-100 chars
COURSE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")
# Week numbers: positive integers 1-52
MIN_WEEK_NUMBER = 1
MAX_WEEK_NUMBER = 52

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY_SECONDS = 0.5

# Firestore batch limit (max operations per batch)
FIRESTORE_BATCH_LIMIT = 500
MAX_RETRY_DELAY_SECONDS = 8.0
RETRY_MULTIPLIER = 2.0

# Firestore batch limit
FIRESTORE_BATCH_LIMIT = 500


# ============================================================================
# Retry Logic
# ============================================================================

def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (transient Firestore error)."""
    return isinstance(error, (
        google_exceptions.ServiceUnavailable,
        google_exceptions.DeadlineExceeded,
        google_exceptions.ResourceExhausted,
        google_exceptions.Aborted,
    ))


def with_retry(
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_RETRY_DELAY_SECONDS,
    max_delay: float = MAX_RETRY_DELAY_SECONDS,
    multiplier: float = RETRY_MULTIPLIER,
):
    """
    Decorator that retries a function on transient Firestore errors.

    Uses exponential backoff with configurable parameters.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        multiplier: Multiplier for exponential backoff
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = None
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not is_retryable_error(e) or attempt >= max_retries:
                        raise

                    logger.warning(
                        "Transient error in %s (attempt %d/%d): %s. Retrying in %.1fs...",
                        func.__name__, attempt + 1, max_retries + 1, str(e), delay
                    )
                    time.sleep(delay)
                    delay = min(delay * multiplier, max_delay)

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper
    return decorator


def validate_course_id(course_id: str) -> str:
    """
    Validate and sanitize a course ID.

    Args:
        course_id: The course ID to validate

    Returns:
        The validated course ID

    Raises:
        ValueError: If the course ID is invalid
    """
    if not course_id:
        raise ValueError("Course ID cannot be empty")

    if not COURSE_ID_PATTERN.match(course_id):
        raise ValueError(
            f"Invalid course ID '{course_id}'. "
            "Must be 1-100 characters, alphanumeric with hyphens and underscores only."
        )

    return course_id


def validate_week_number(week_number: int) -> int:
    """
    Validate a week number.

    Args:
        week_number: The week number to validate

    Returns:
        The validated week number

    Raises:
        ValueError: If the week number is invalid
    """
    if not isinstance(week_number, int):
        raise ValueError(f"Week number must be an integer, got {type(week_number).__name__}")

    if week_number < MIN_WEEK_NUMBER or week_number > MAX_WEEK_NUMBER:
        raise ValueError(
            f"Week number must be between {MIN_WEEK_NUMBER} and {MAX_WEEK_NUMBER}, "
            f"got {week_number}"
        )

    return week_number


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

    @with_retry()
    def get_all_courses(
        self,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[CourseSummary], int]:
        """
        Get all courses as summaries with pagination.

        Args:
            include_inactive: Whether to include inactive courses
            limit: Maximum number of courses to return (1-100)
            offset: Number of courses to skip for pagination

        Returns:
            Tuple of (list of course summaries, total count)

        Raises:
            ServiceValidationError: If limit or offset is invalid
            FirestoreOperationError: If Firestore operation fails
        """
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            raise ServiceValidationError(f"Limit must be between 1 and 100, got {limit}")
        if offset < 0:
            raise ServiceValidationError(f"Offset must be non-negative, got {offset}")

        try:
            courses_ref = self.db.collection(COURSES_COLLECTION)

            if not include_inactive:
                courses_ref = courses_ref.where(filter=FieldFilter("active", "==", True))

            # Get total count efficiently using select([]) to only fetch document IDs
            # This reduces bandwidth by not fetching all document data
            count_query = courses_ref.select([])
            total_count = len(list(count_query.stream()))

            # Use Firestore native pagination with offset() and limit()
            # Note: For large datasets (10k+), consider cursor-based pagination
            paginated_query = courses_ref.offset(offset).limit(limit)
            paginated_docs = list(paginated_query.stream())

            courses = []
            for doc in paginated_docs:
                data = doc.to_dict()
                # Use stored weekCount if available, otherwise default to 0
                # This avoids N+1 queries - weekCount should be updated when weeks change
                week_count = data.get("weekCount", 0)

                courses.append(CourseSummary(
                    id=doc.id,
                    name=data.get("name", ""),
                    program=data.get("program"),
                    institution=data.get("institution"),
                    academicYear=data.get("academicYear", ""),
                    weekCount=week_count,
                    active=data.get("active", True)
                ))

            logger.info("Retrieved %d courses (offset=%d, limit=%d, total=%d)", len(courses), offset, limit, total_count)
            return courses, total_count

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error getting courses: %s", str(e))
            raise FirestoreOperationError("Failed to retrieve courses") from e

    @with_retry()
    def get_course(self, course_id: str, include_weeks: bool = True) -> Optional[Course]:
        """
        Get a course by ID.

        Args:
            course_id: The course ID
            include_weeks: Whether to include weeks and legal skills

        Returns:
            Course object or None if not found

        Raises:
            ServiceValidationError: If course_id is invalid
            FirestoreOperationError: If Firestore operation fails
        """
        try:
            course_id = validate_course_id(course_id)
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e

        try:
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
                createdAt=data.get("createdAt", datetime.now(timezone.utc)),
                updatedAt=data.get("updatedAt", datetime.now(timezone.utc)),
            )

            # Load weeks if requested
            if include_weeks:
                course.weeks = self.get_course_weeks(course_id)
                course.legalSkills = self.get_legal_skills(course_id)

            logger.info("Retrieved course: %s", course_id)
            return course

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error getting course %s: %s", course_id, str(e))
            raise FirestoreOperationError(f"Failed to get course {course_id}: {str(e)}") from e

    @with_retry()
    def create_course(
        self,
        course_data: CourseCreate,
        initial_weeks: Optional[List[WeekCreate]] = None,
        initial_skills: Optional[Dict[str, LegalSkill]] = None,
    ) -> Course:
        """
        Create a new course with optional initial weeks and skills using batch write.

        Args:
            course_data: Course creation data
            initial_weeks: Optional list of weeks to create with the course
            initial_skills: Optional dict of skill_id -> LegalSkill to create

        Returns:
            Created course object

        Raises:
            ServiceValidationError: If course_id is invalid
            CourseAlreadyExistsError: If course already exists
            FirestoreOperationError: If Firestore operation fails
        """
        try:
            course_id = validate_course_id(course_data.id)
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e

        # Calculate total batch operations and validate against Firestore limit
        weeks_count = len(initial_weeks or [])
        skills_count = len(initial_skills or {})
        total_ops = 1 + weeks_count + skills_count  # 1 for course document

        if total_ops > FIRESTORE_BATCH_LIMIT:
            raise ServiceValidationError(
                f"Total operations ({total_ops}) exceeds Firestore batch limit ({FIRESTORE_BATCH_LIMIT}). "
                f"Reduce initial_weeks ({weeks_count}) or initial_skills ({skills_count})."
            )

        try:
            doc_ref = self.db.collection(COURSES_COLLECTION).document(course_id)

            # Check if already exists
            if doc_ref.get().exists:
                raise CourseAlreadyExistsError(f"Course already exists: {course_id}")

            now = datetime.now(timezone.utc)
            data = {
                **course_data.model_dump(),
                "active": True,
                "weekCount": weeks_count,  # Store week count for efficient pagination
                "createdAt": now,
                "updatedAt": now,
            }

            # Use batch write for atomicity if we have initial data
            if initial_weeks or initial_skills:
                batch = self.db.batch()
                batch.set(doc_ref, data)

                # Add initial weeks
                if initial_weeks:
                    for week_data in initial_weeks:
                        week_ref = doc_ref.collection(WEEKS_SUBCOLLECTION).document(
                            f"week-{week_data.weekNumber}"
                        )
                        batch.set(week_ref, week_data.model_dump())

                # Add initial skills
                if initial_skills:
                    for skill_id, skill in initial_skills.items():
                        skill_ref = doc_ref.collection(LEGAL_SKILLS_SUBCOLLECTION).document(skill_id)
                        batch.set(skill_ref, skill.model_dump())

                batch.commit()
                logger.info("Created course %s with %d weeks and %d skills",
                           course_id, weeks_count, skills_count)
            else:
                doc_ref.set(data)
                logger.info("Created course: %s", course_id)

            return self.get_course(course_id, include_weeks=False)

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error creating course %s: %s", course_id, str(e))
            raise FirestoreOperationError("Failed to create course") from e

    @with_retry()
    def update_course(self, course_id: str, updates: CourseUpdate) -> Optional[Course]:
        """
        Update a course.

        Args:
            course_id: The course ID
            updates: Fields to update

        Returns:
            Updated course or None if not found

        Raises:
            ServiceValidationError: If course_id is invalid
            CourseNotFoundError: If course not found
            FirestoreOperationError: If Firestore operation fails
        """
        try:
            course_id = validate_course_id(course_id)
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e

        try:
            doc_ref = self.db.collection(COURSES_COLLECTION).document(course_id)

            # Only include non-None fields
            update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
            update_data["updatedAt"] = datetime.now(timezone.utc)

            # Use update() which will raise NotFound if document doesn't exist
            # This avoids race condition between exists check and update
            doc_ref.update(update_data)
            logger.info("Updated course: %s", course_id)

            return self.get_course(course_id, include_weeks=False)

        except google_exceptions.NotFound:
            logger.warning("Course not found for update: %s", course_id)
            raise CourseNotFoundError(f"Course not found: {course_id}")
        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error updating course %s: %s", course_id, str(e))
            raise FirestoreOperationError("Failed to update course") from e

    @with_retry()
    def deactivate_course(self, course_id: str) -> bool:
        """
        Deactivate a course (soft delete).

        Args:
            course_id: The course ID

        Returns:
            True if deactivated, False if not found

        Raises:
            ServiceValidationError: If course_id is invalid
            FirestoreOperationError: If Firestore operation fails
        """
        try:
            course_id = validate_course_id(course_id)
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e

        try:
            doc_ref = self.db.collection(COURSES_COLLECTION).document(course_id)

            if not doc_ref.get().exists:
                return False

            doc_ref.update({
                "active": False,
                "updatedAt": datetime.now(timezone.utc)
            })
            logger.info("Deactivated course: %s", course_id)
            return True

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error deactivating course %s: %s", course_id, str(e))
            raise FirestoreOperationError(f"Failed to deactivate course {course_id}: {str(e)}") from e

    # ========================================================================
    # Week Operations
    # ========================================================================

    @with_retry()
    def get_course_weeks(self, course_id: str) -> List[Week]:
        """
        Get all weeks for a course.

        Args:
            course_id: The course ID

        Returns:
            List of weeks sorted by week number

        Raises:
            FirestoreOperationError: If Firestore operation fails
        """
        try:
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

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error getting weeks for course %s: %s", course_id, str(e))
            raise FirestoreOperationError(f"Failed to get weeks for course {course_id}: {str(e)}") from e

    @with_retry()
    def get_week(self, course_id: str, week_number: int) -> Optional[Week]:
        """
        Get a specific week.

        Args:
            course_id: The course ID
            week_number: The week number

        Returns:
            Week object or None if not found

        Raises:
            ServiceValidationError: If course_id or week_number is invalid
            FirestoreOperationError: If Firestore operation fails
        """
        try:
            course_id = validate_course_id(course_id)
            week_number = validate_week_number(week_number)
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e

        try:
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

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error getting week %d for course %s: %s", week_number, course_id, str(e))
            raise FirestoreOperationError(f"Failed to get week {week_number} for course {course_id}: {str(e)}") from e

    @with_retry()
    def upsert_week(self, course_id: str, week_data: WeekCreate) -> Week:
        """
        Create or update a week using batch write for atomicity.

        Args:
            course_id: The course ID
            week_data: Week data

        Returns:
            Created/updated week

        Raises:
            ServiceValidationError: If course_id or week_number is invalid
            FirestoreOperationError: If Firestore operation fails
        """
        try:
            course_id = validate_course_id(course_id)
            validate_week_number(week_data.weekNumber)
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e

        try:
            course_ref = self.db.collection(COURSES_COLLECTION).document(course_id)
            week_ref = course_ref.collection(WEEKS_SUBCOLLECTION).document(f"week-{week_data.weekNumber}")

            # Check if this is a new week (for weekCount update)
            is_new_week = not week_ref.get().exists

            # Use batch for atomic update of week + course timestamp + weekCount
            batch = self.db.batch()
            batch.set(week_ref, week_data.model_dump())

            # Update course's updatedAt and increment weekCount if new week
            update_data = {"updatedAt": datetime.now(timezone.utc)}
            if is_new_week:
                # Get current weekCount and increment
                course_doc = course_ref.get()
                if course_doc.exists:
                    current_count = course_doc.to_dict().get("weekCount", 0)
                    update_data["weekCount"] = current_count + 1

            batch.update(course_ref, update_data)
            batch.commit()

            logger.info("Upserted week %d for course %s", week_data.weekNumber, course_id)
            return Week(**week_data.model_dump())

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error upserting week %d for course %s: %s", week_data.weekNumber, course_id, str(e))
            raise FirestoreOperationError("Failed to upsert week") from e

    @with_retry()
    def delete_week(self, course_id: str, week_number: int) -> bool:
        """
        Delete a week using batch write for atomicity.

        Args:
            course_id: The course ID
            week_number: The week number

        Returns:
            True if deleted, False if not found

        Raises:
            ServiceValidationError: If course_id or week_number is invalid
            FirestoreOperationError: If Firestore operation fails
        """
        try:
            course_id = validate_course_id(course_id)
            week_number = validate_week_number(week_number)
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e

        try:
            course_ref = self.db.collection(COURSES_COLLECTION).document(course_id)
            doc_ref = course_ref.collection(WEEKS_SUBCOLLECTION).document(f"week-{week_number}")

            if not doc_ref.get().exists:
                return False

            # Use batch for atomic delete + course timestamp + weekCount update
            batch = self.db.batch()
            batch.delete(doc_ref)

            # Update course's updatedAt and decrement weekCount
            course_doc = course_ref.get()
            if course_doc.exists:
                current_count = course_doc.to_dict().get("weekCount", 0)
                batch.update(course_ref, {
                    "updatedAt": datetime.now(timezone.utc),
                    "weekCount": max(0, current_count - 1)  # Ensure non-negative
                })
            else:
                batch.update(course_ref, {"updatedAt": datetime.now(timezone.utc)})

            batch.commit()

            logger.info("Deleted week %d from course %s", week_number, course_id)
            return True

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error deleting week %d from course %s: %s", week_number, course_id, str(e))
            raise FirestoreOperationError("Failed to delete week") from e

    # ========================================================================
    # Legal Skills Operations
    # ========================================================================

    @with_retry()
    def get_legal_skills(self, course_id: str) -> Dict[str, LegalSkill]:
        """
        Get all legal skills for a course.

        Args:
            course_id: The course ID

        Returns:
            Dictionary of skill_id -> LegalSkill

        Raises:
            FirestoreOperationError: If Firestore operation fails
        """
        try:
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

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error getting legal skills for course %s: %s", course_id, str(e))
            raise FirestoreOperationError(f"Failed to get legal skills for course {course_id}: {str(e)}") from e

    @with_retry()
    def upsert_legal_skill(
        self, course_id: str, skill_id: str, skill: LegalSkill
    ) -> LegalSkill:
        """
        Create or update a legal skill using batch write for atomicity.

        Args:
            course_id: The course ID
            skill_id: The skill identifier (e.g., "ecthrCaseAnalysis")
            skill: The legal skill data

        Returns:
            Created/updated legal skill

        Raises:
            ServiceValidationError: If course_id or skill_id is invalid
            FirestoreOperationError: If Firestore operation fails
        """
        try:
            course_id = validate_course_id(course_id)
            # Validate skill_id using same pattern as course_id
            if not COURSE_ID_PATTERN.match(skill_id):
                raise ServiceValidationError(
                    f"Invalid skill ID '{skill_id}'. "
                    "Must be 1-100 characters, alphanumeric with hyphens and underscores only."
                )
        except ValueError as e:
            raise ServiceValidationError(str(e)) from e

        try:
            # Use batch for atomic update of skill + course timestamp
            batch = self.db.batch()

            skill_ref = (
                self.db.collection(COURSES_COLLECTION)
                .document(course_id)
                .collection(LEGAL_SKILLS_SUBCOLLECTION)
                .document(skill_id)
            )
            batch.set(skill_ref, skill.model_dump())

            # Update course's updatedAt
            course_ref = self.db.collection(COURSES_COLLECTION).document(course_id)
            batch.update(course_ref, {"updatedAt": datetime.now(timezone.utc)})

            batch.commit()

            logger.info("Upserted legal skill '%s' for course %s", skill_id, course_id)
            return skill

        except google_exceptions.GoogleAPIError as e:
            logger.error("Firestore error upserting legal skill '%s' for course %s: %s", skill_id, course_id, str(e))
            raise FirestoreOperationError(f"Failed to upsert legal skill '{skill_id}' for course {course_id}: {str(e)}") from e


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

