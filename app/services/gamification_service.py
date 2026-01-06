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

from google.cloud.firestore_v1 import FieldFilter

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

    @property
    def db(self):
        """Lazy-load Firestore client."""
        if self._db is None:
            self._db = get_firestore_client()
        return self._db

    # =========================================================================
    # User Stats Methods
    # =========================================================================

    async def get_user_stats(self, user_id: str) -> Optional[UserStats]:
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

    async def create_user_stats(
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

    async def get_or_create_user_stats(
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
        stats = await self.get_user_stats(user_id)
        if stats is None:
            stats = await self.create_user_stats(user_id, user_email, course_id)
        return stats

    async def update_user_stats(self, user_id: str, updates: Dict[str, Any]) -> bool:
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
        """Calculate XP for an activity.

        Args:
            activity_type: Type of activity
            activity_data: Activity-specific data

        Returns:
            XP amount to award
        """
        # Quiz completion
        if activity_type == "quiz_completed":
            difficulty = activity_data.get("difficulty", "easy")
            score = activity_data.get("score", 0)
            total = activity_data.get("total_questions", 1)
            percentage = (score / total) * 100 if total > 0 else 0

            # Only award XP if passed (>= 60%)
            if percentage >= 60:
                if difficulty == "hard":
                    return XP_VALUES["quiz_hard_passed"]
                else:
                    return XP_VALUES["quiz_easy_passed"]
            return 0

        # Flashcard review
        elif activity_type == "flashcard_set_completed":
            correct = activity_data.get("correct_count", 0)
            # Award 5 XP per 10 cards reviewed correctly
            return (correct // 10) * XP_VALUES["flashcard_set_completed"]

        # Study guide completion
        elif activity_type == "study_guide_completed":
            return XP_VALUES["study_guide_completed"]

        # AI Evaluation
        elif activity_type == "evaluation_completed":
            grade = activity_data.get("grade", 0)
            if grade >= 7:
                return XP_VALUES["evaluation_high"]
            elif grade >= 1:
                return XP_VALUES["evaluation_low"]
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

    async def log_activity(
        self,
        user_id: str,
        user_email: str,
        activity_type: str,
        activity_data: Dict[str, Any],
        course_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[ActivityLogResponse]:
        """Log a user activity and award XP.

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
            # Get or create user stats
            stats = await self.get_or_create_user_stats(user_id, user_email, course_id)
            if not stats:
                return None

            # Calculate XP
            xp_awarded = self.calculate_xp_for_activity(activity_type, activity_data)

            # Calculate new totals
            new_total_xp = stats.total_xp + xp_awarded
            old_level = stats.current_level
            new_level, new_level_title, xp_to_next = self.calculate_level_from_xp(new_total_xp)
            level_up = new_level > old_level

            # Check for streak freeze award (every 500 XP)
            old_freeze_count = stats.streak.freezes_available
            new_freeze_count = old_freeze_count + (new_total_xp // STREAK_FREEZE_XP_REQUIREMENT) - (stats.total_xp // STREAK_FREEZE_XP_REQUIREMENT)

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

            # Update user stats
            updates = {
                "total_xp": new_total_xp,
                "current_level": new_level,
                "level_title": new_level_title,
                "xp_to_next_level": xp_to_next,
                "last_active": datetime.now(timezone.utc),
                f"streak.freezes_available": new_freeze_count,
            }

            # Update activity counters
            if activity_type == "quiz_completed":
                updates["activities.quizzes_completed"] = stats.activities.quizzes_completed + 1
                if activity_data.get("score", 0) / activity_data.get("total_questions", 1) >= 0.6:
                    updates["activities.quizzes_passed"] = stats.activities.quizzes_passed + 1
            elif activity_type == "flashcard_set_completed":
                updates["activities.flashcards_reviewed"] = stats.activities.flashcards_reviewed + activity_data.get("total_count", 0)
            elif activity_type == "study_guide_completed":
                updates["activities.guides_completed"] = stats.activities.guides_completed + 1
            elif activity_type == "evaluation_completed":
                updates["activities.evaluations_submitted"] = stats.activities.evaluations_submitted + 1

            await self.update_user_stats(user_id, updates)

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

    async def get_user_activities(
        self,
        user_id: str,
        limit: int = DEFAULT_QUERY_LIMIT,
        activity_type: Optional[str] = None
    ) -> List[UserActivity]:
        """Get user's recent activities.

        Args:
            user_id: User's IAP user ID
            limit: Maximum number of activities to return
            activity_type: Optional filter by activity type

        Returns:
            List of UserActivity objects
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return []

        try:
            query = self.db.collection(USER_ACTIVITIES_COLLECTION).where(
                filter=FieldFilter("user_id", "==", user_id)
            ).order_by("timestamp", direction="DESCENDING").limit(min(limit, MAX_QUERY_LIMIT))

            if activity_type:
                query = query.where(filter=FieldFilter("activity_type", "==", activity_type))

            docs = query.stream()
            activities = []
            for doc in docs:
                try:
                    activities.append(UserActivity(**doc.to_dict()))
                except Exception as e:
                    logger.warning(f"Error parsing activity {doc.id}: {e}")

            return activities

        except Exception as e:
            logger.error(f"Error getting activities for {user_id}: {e}")
            return []

    # =========================================================================
    # Session Management Methods
    # =========================================================================

    async def start_session(
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

    async def update_session_heartbeat(
        self,
        session_id: str,
        active_seconds: int,
        current_page: str
    ) -> bool:
        """Update session with heartbeat.

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
            current_active = session_data.get("active_time_seconds", 0)
            page_views = session_data.get("page_views", [])

            # Add page view
            page_view = PageView(
                page=current_page,
                active_seconds=active_seconds,
                timestamp=datetime.now(timezone.utc)
            )
            page_views.append(page_view.model_dump(mode='json'))

            # Update session
            updates = {
                "active_time_seconds": current_active + active_seconds,
                "page_views": page_views
            }
            session_ref.update(updates)

            return True

        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False

    async def end_session(self, session_id: str) -> bool:
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

