"""Gamification Service.

Provides functionality for tracking user activities, awarding XP, managing streaks,
and handling gamification features.

Firestore structure:
- user_stats/{user_id}
- user_activities/{activity_id}
- user_sessions/{session_id}
- badge_definitions/{badge_id}
- user_achievements/{user_id}/badges/{badge_id}
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from google.cloud.firestore_v1 import FieldFilter, Increment

from app.models.gamification_models import (
    UserStats,
    UserActivity,
    UserSession,
    BadgeDefinition,
    UserBadge,
    ActivityLogResponse,
    SessionStartResponse,
    UserStatsResponse,
    StreakInfo,
    ActivityCounters,
    Week7Quest,
    PageView,
    XPConfig,
)
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Firestore collection names
USER_STATS_COLLECTION = "user_stats"
USER_ACTIVITIES_COLLECTION = "user_activities"
USER_SESSIONS_COLLECTION = "user_sessions"
BADGE_DEFINITIONS_COLLECTION = "badge_definitions"
USER_ACHIEVEMENTS_COLLECTION = "user_achievements"
XP_CONFIG_COLLECTION = "xp_config"
XP_CONFIG_DOC_ID = "default"

# Query limits
DEFAULT_QUERY_LIMIT = 50
MAX_QUERY_LIMIT = 100

# XP values for activities
XP_VALUES = {
    "flashcard_set_completed": 5,  # Per 10 cards reviewed correctly
    "study_guide_completed": 15,
    "quiz_easy_passed": 10,
    "quiz_hard_passed": 25,
    "evaluation_low": 20,  # Grade 1-6
    "evaluation_high": 50,  # Grade 7-10
}

# Level thresholds and titles
LEVEL_THRESHOLDS = [
    (0, "Junior Clerk"),  # Levels 1-10
    (1000, "Summer Associate"),  # Levels 11-25
    (5000, "Junior Partner"),  # Levels 26-50
    (15000, "Senior Partner"),  # Level 50+
    (50000, "Juris Doctor"),  # Level 100+
]

# Streak freeze XP requirement
STREAK_FREEZE_XP_REQUIREMENT = 500

# 4AM reset hour
STREAK_RESET_HOUR = 4


class GamificationService:
    """Service for managing gamification features."""

    def __init__(self):
        """Initialize the gamification service."""
        self._db = None
        self._xp_config_cache = None
        self._xp_config_cache_time = None
        self._xp_config_cache_ttl = 300  # 5 minutes

    @property
    def db(self):
        """Lazy-load Firestore client."""
        if self._db is None:
            self._db = get_firestore_client()
        return self._db

    def get_xp_config(self) -> Dict[str, int]:
        """Get XP configuration from Firestore with caching.

        Returns:
            Dictionary of XP values for each activity type
        """
        # Check cache
        if self._xp_config_cache and self._xp_config_cache_time:
            age = (datetime.now(timezone.utc) - self._xp_config_cache_time).total_seconds()
            if age < self._xp_config_cache_ttl:
                return self._xp_config_cache

        # Load from Firestore
        if not self.db:
            logger.warning("Firestore unavailable, using default XP values")
            return XP_VALUES

        try:
            doc_ref = self.db.collection(XP_CONFIG_COLLECTION).document(XP_CONFIG_DOC_ID)
            doc = doc_ref.get()

            if doc.exists:
                config = doc.to_dict()
                # Cache the config
                self._xp_config_cache = {
                    "flashcard_set_completed": config.get("flashcard_set_completed", XP_VALUES["flashcard_set_completed"]),
                    "study_guide_completed": config.get("study_guide_completed", XP_VALUES["study_guide_completed"]),
                    "quiz_easy_passed": config.get("quiz_easy_passed", XP_VALUES["quiz_easy_passed"]),
                    "quiz_hard_passed": config.get("quiz_hard_passed", XP_VALUES["quiz_hard_passed"]),
                    "evaluation_low": config.get("evaluation_low", XP_VALUES["evaluation_low"]),
                    "evaluation_high": config.get("evaluation_high", XP_VALUES["evaluation_high"]),
                }
                self._xp_config_cache_time = datetime.now(timezone.utc)
                return self._xp_config_cache
            else:
                # Create default config
                logger.info("Creating default XP config")
                doc_ref.set({
                    **XP_VALUES,
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": "system"
                })
                self._xp_config_cache = XP_VALUES.copy()
                self._xp_config_cache_time = datetime.now(timezone.utc)
                return self._xp_config_cache

        except Exception as e:
            logger.error(f"Error loading XP config: {e}")
            return XP_VALUES

    def update_xp_config(self, updates: Dict[str, int], updated_by: str) -> bool:
        """Update XP configuration.

        Args:
            updates: Dictionary of XP values to update
            updated_by: User who is updating the config

        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return False

        try:
            doc_ref = self.db.collection(XP_CONFIG_COLLECTION).document(XP_CONFIG_DOC_ID)
            updates["updated_at"] = datetime.now(timezone.utc)
            updates["updated_by"] = updated_by
            doc_ref.update(updates)

            # Clear cache
            self._xp_config_cache = None
            self._xp_config_cache_time = None

            logger.info(f"XP config updated by {updated_by}: {updates}")
            return True

        except Exception as e:
            logger.error(f"Error updating XP config: {e}")
            return False

    # =========================================================================
    # User Stats Methods
    # =========================================================================

    def get_user_stats(self, user_id: str) -> Optional[UserStats]:
        """Get user gamification stats.

        Args:
            user_id: User's IAP user ID

        Returns:
            UserStats object or None if not found
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return None

        try:
            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return None

            data = doc.to_dict()
            return UserStats(**data)

        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return None

    def create_user_stats(
        self,
        user_id: str,
        user_email: str,
        course_id: Optional[str] = None
    ) -> Optional[UserStats]:
        """Create initial user stats.

        Args:
            user_id: User's IAP user ID
            user_email: User's email address
            course_id: Course ID if applicable

        Returns:
            Created UserStats object or None on error
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return None

        try:
            stats = UserStats(
                user_id=user_id,
                user_email=user_email,
                course_id=course_id
            )

            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            doc_ref.set(stats.model_dump(mode='json'))

            logger.info(f"Created user stats for {user_id}")
            return stats

        except Exception as e:
            logger.error(f"Error creating user stats for {user_id}: {e}")
            return None

    def get_or_create_user_stats(
        self,
        user_id: str,
        user_email: str,
        course_id: Optional[str] = None
    ) -> Optional[UserStats]:
        """Get user stats or create if doesn't exist.

        Args:
            user_id: User's IAP user ID
            user_email: User's email address
            course_id: Course ID if applicable

        Returns:
            UserStats object or None on error
        """
        stats = self.get_user_stats(user_id)
        if stats is None:
            stats = self.create_user_stats(user_id, user_email, course_id)
        return stats

    def update_user_stats(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user stats.

        Args:
            user_id: User's IAP user ID
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return False

        try:
            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            updates["updated_at"] = datetime.now(timezone.utc)
            doc_ref.update(updates)
            return True

        except Exception as e:
            logger.error(f"Error updating user stats for {user_id}: {e}")
            return False

    # =========================================================================
    # XP and Level Methods
    # =========================================================================

    def calculate_xp_for_activity(
        self,
        activity_type: str,
        activity_data: Dict[str, Any]
    ) -> int:
        """Calculate XP for an activity using configurable XP values.

        Args:
            activity_type: Type of activity
            activity_data: Activity-specific data

        Returns:
            XP amount to award
        """
        # Get current XP configuration
        xp_config = self.get_xp_config()

        # Quiz completion
        if activity_type == "quiz_completed":
            difficulty = activity_data.get("difficulty", "easy")
            score = activity_data.get("score", 0)
            total = activity_data.get("total_questions", 1)
            percentage = (score / total) * 100 if total > 0 else 0

            # Only award XP if passed (>= 60%)
            if percentage >= 60:
                if difficulty == "hard":
                    return xp_config["quiz_hard_passed"]
                else:
                    return xp_config["quiz_easy_passed"]
            return 0

        # Flashcard review
        elif activity_type == "flashcard_set_completed":
            correct = activity_data.get("correct_count", 0)
            # Award XP per 10 cards reviewed correctly
            return (correct // 10) * xp_config["flashcard_set_completed"]

        # Study guide completion
        elif activity_type == "study_guide_completed":
            return xp_config["study_guide_completed"]

        # AI Evaluation
        elif activity_type == "evaluation_completed":
            grade = activity_data.get("grade", 0)
            if grade >= 7:
                return xp_config["evaluation_high"]
            elif grade >= 1:
                return xp_config["evaluation_low"]
            return 0

        # Default: no XP
        return 0

    def calculate_level_from_xp(self, total_xp: int) -> tuple[int, str, int]:
        """Calculate level, title, and XP to next level from total XP.

        Args:
            total_xp: Total XP earned

        Returns:
            Tuple of (level, level_title, xp_to_next_level)
        """
        # Find current level tier
        current_tier_index = 0
        for i, (threshold, _) in enumerate(LEVEL_THRESHOLDS):
            if total_xp >= threshold:
                current_tier_index = i
            else:
                break

        current_threshold, level_title = LEVEL_THRESHOLDS[current_tier_index]

        # Calculate level within tier
        if current_tier_index < len(LEVEL_THRESHOLDS) - 1:
            next_threshold, _ = LEVEL_THRESHOLDS[current_tier_index + 1]
            xp_in_tier = total_xp - current_threshold
            xp_per_level = (next_threshold - current_threshold) // 10
            level_in_tier = min(xp_in_tier // xp_per_level, 9) if xp_per_level > 0 else 0
            level = (current_tier_index * 10) + level_in_tier + 1
            xp_to_next = xp_per_level - (xp_in_tier % xp_per_level) if xp_per_level > 0 else 0
        else:
            # Max tier
            level = 100
            xp_to_next = 0

        return level, level_title, xp_to_next

    # =========================================================================
    # Activity Logging Methods
    # =========================================================================

    def log_activity(
        self,
        user_id: str,
        user_email: str,
        activity_type: str,
        activity_data: Dict[str, Any],
        course_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[ActivityLogResponse]:
        """Log a user activity and award XP.

        Uses Firestore atomic operations to prevent race conditions.

        Args:
            user_id: User's IAP user ID
            user_email: User's email address
            activity_type: Type of activity
            activity_data: Activity-specific data
            course_id: Course ID if applicable
            session_id: Session ID if applicable

        Returns:
            ActivityLogResponse or None on error
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return None

        try:
            # Get or create user stats (for reading current values)
            stats = self.get_or_create_user_stats(user_id, user_email, course_id)
            if not stats:
                return None

            # Calculate XP
            xp_awarded = self.calculate_xp_for_activity(activity_type, activity_data)

            if xp_awarded == 0:
                logger.info(f"No XP awarded for {activity_type} (did not meet criteria)")
                # Still log the activity but don't update stats
                activity_id = str(uuid.uuid4())
                activity = UserActivity(
                    id=activity_id,
                    user_id=user_id,
                    user_email=user_email,
                    course_id=course_id,
                    activity_type=activity_type,
                    activity_data=activity_data,
                    session_id=session_id,
                    xp_awarded=0,
                    streak_maintained=True,
                    badges_earned=[],
                    metadata={"time_of_day": self._get_time_of_day()}
                )
                activity_ref = self.db.collection(USER_ACTIVITIES_COLLECTION).document(activity_id)
                activity_ref.set(activity.model_dump(mode='json'))

                return ActivityLogResponse(
                    activity_id=activity_id,
                    xp_awarded=0,
                    new_total_xp=stats.total_xp,
                    level_up=False,
                    new_level=None,
                    new_level_title=None,
                    streak_maintained=True,
                    badges_earned=[]
                )

            # Calculate new totals (for response)
            new_total_xp = stats.total_xp + xp_awarded
            old_level = stats.current_level
            new_level, new_level_title, xp_to_next = self.calculate_level_from_xp(new_total_xp)
            level_up = new_level > old_level

            # Check for streak freeze award (every 500 XP)
            old_freeze_count = stats.streak.freezes_available
            freezes_to_add = (new_total_xp // STREAK_FREEZE_XP_REQUIREMENT) - (stats.total_xp // STREAK_FREEZE_XP_REQUIREMENT)

            # Create activity record
            activity_id = str(uuid.uuid4())
            activity = UserActivity(
                id=activity_id,
                user_id=user_id,
                user_email=user_email,
                course_id=course_id,
                activity_type=activity_type,
                activity_data=activity_data,
                session_id=session_id,
                xp_awarded=xp_awarded,
                streak_maintained=True,  # TODO: Implement streak logic
                badges_earned=[],  # TODO: Implement badge logic
                metadata={
                    "time_of_day": self._get_time_of_day(),
                }
            )

            # Save activity
            activity_ref = self.db.collection(USER_ACTIVITIES_COLLECTION).document(activity_id)
            activity_ref.set(activity.model_dump(mode='json'))

            # Use atomic increments to prevent race conditions
            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            updates = {
                "total_xp": Increment(xp_awarded),
                "current_level": new_level,
                "level_title": new_level_title,
                "xp_to_next_level": xp_to_next,
                "last_active": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            # Add freeze increment if earned
            if freezes_to_add > 0:
                updates["streak.freezes_available"] = Increment(freezes_to_add)

            # Update activity counters with atomic increments
            if activity_type == "quiz_completed":
                updates["activities.quizzes_completed"] = Increment(1)
                if activity_data.get("score", 0) / activity_data.get("total_questions", 1) >= 0.6:
                    updates["activities.quizzes_passed"] = Increment(1)
            elif activity_type == "flashcard_set_completed":
                total_count = activity_data.get("total_count", 0)
                if total_count > 0:
                    updates["activities.flashcards_reviewed"] = Increment(total_count)
            elif activity_type == "study_guide_completed":
                updates["activities.guides_completed"] = Increment(1)
            elif activity_type == "evaluation_completed":
                updates["activities.evaluations_submitted"] = Increment(1)

            doc_ref.update(updates)

            logger.info(f"Logged activity {activity_type} for {user_id}, awarded {xp_awarded} XP")

            return ActivityLogResponse(
                activity_id=activity_id,
                xp_awarded=xp_awarded,
                new_total_xp=new_total_xp,
                level_up=level_up,
                new_level=new_level if level_up else None,
                new_level_title=new_level_title if level_up else None,
                streak_maintained=True,
                badges_earned=[]
            )

        except Exception as e:
            logger.error(f"Error logging activity for {user_id}: {e}")
            return None

    def _get_time_of_day(self) -> str:
        """Get time of day category."""
        hour = datetime.now(timezone.utc).hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def get_user_activities(
        self,
        user_id: str,
        limit: int = DEFAULT_QUERY_LIMIT,
        activity_type: Optional[str] = None,
        start_after_id: Optional[str] = None
    ) -> tuple[List[UserActivity], Optional[str]]:
        """Get user's recent activities with pagination support.

        Args:
            user_id: User's IAP user ID
            limit: Maximum number of activities to return
            activity_type: Optional filter by activity type
            start_after_id: Optional activity ID to start after (for pagination)

        Returns:
            Tuple of (List of UserActivity objects, next_cursor for pagination)
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return [], None

        try:
            query = self.db.collection(USER_ACTIVITIES_COLLECTION).where(
                filter=FieldFilter("user_id", "==", user_id)
            ).order_by("timestamp", direction="DESCENDING").limit(min(limit, MAX_QUERY_LIMIT))

            if activity_type:
                query = query.where(filter=FieldFilter("activity_type", "==", activity_type))

            # Add pagination support
            if start_after_id:
                start_doc = self.db.collection(USER_ACTIVITIES_COLLECTION).document(start_after_id).get()
                if start_doc.exists:
                    query = query.start_after(start_doc)

            docs = list(query.stream())
            activities = []
            for doc in docs:
                try:
                    activities.append(UserActivity(**doc.to_dict()))
                except Exception as e:
                    logger.warning(f"Error parsing activity {doc.id}: {e}")

            # Return next cursor for pagination
            next_cursor = docs[-1].id if docs and len(docs) == limit else None
            return activities, next_cursor

        except Exception as e:
            logger.error(f"Error getting activities for {user_id}: {e}")
            return [], None

    # =========================================================================
    # Session Management Methods
    # =========================================================================

    def start_session(
        self,
        user_id: str,
        course_id: Optional[str] = None
    ) -> Optional[SessionStartResponse]:
        """Start a new tracking session.

        Args:
            user_id: User's IAP user ID
            course_id: Course ID if applicable

        Returns:
            SessionStartResponse or None on error
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return None

        try:
            session_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)

            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                course_id=course_id,
                start_time=start_time
            )

            session_ref = self.db.collection(USER_SESSIONS_COLLECTION).document(session_id)
            session_ref.set(session.model_dump(mode='json'))

            logger.info(f"Started session {session_id} for {user_id}")

            return SessionStartResponse(
                session_id=session_id,
                start_time=start_time
            )

        except Exception as e:
            logger.error(f"Error starting session for {user_id}: {e}")
            return None

    def update_session_heartbeat(
        self,
        session_id: str,
        active_seconds: int,
        current_page: str
    ) -> bool:
        """Update session with heartbeat using atomic increment.

        Args:
            session_id: Session ID
            active_seconds: Active seconds since last heartbeat
            current_page: Current page name

        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return False

        try:
            session_ref = self.db.collection(USER_SESSIONS_COLLECTION).document(session_id)
            session_doc = session_ref.get()

            if not session_doc.exists:
                logger.warning(f"Session {session_id} not found")
                return False

            session_data = session_doc.to_dict()
            page_views = session_data.get("page_views", [])

            # Add page view
            page_view = PageView(
                page=current_page,
                active_seconds=active_seconds,
                timestamp=datetime.now(timezone.utc)
            )
            page_views.append(page_view.model_dump(mode='json'))

            # Update session with atomic increment for active_time_seconds
            updates = {
                "active_time_seconds": Increment(active_seconds),
                "page_views": page_views
            }
            session_ref.update(updates)

            return True

        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False

    def end_session(self, session_id: str) -> bool:
        """End a tracking session.

        Args:
            session_id: Session ID

        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return False

        try:
            session_ref = self.db.collection(USER_SESSIONS_COLLECTION).document(session_id)
            end_time = datetime.now(timezone.utc)

            updates = {
                "end_time": end_time
            }
            session_ref.update(updates)

            logger.info(f"Ended session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")
            return False


# =============================================================================
# Service Instance
# =============================================================================

_service_instance = None
_service_lock = None


def get_gamification_service() -> GamificationService:
    """Get singleton instance of GamificationService."""
    global _service_instance
    if _service_instance is None:
        _service_instance = GamificationService()
    return _service_instance

