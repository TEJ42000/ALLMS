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

from fastapi import HTTPException
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
)
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Import Week 7 quest service (avoid circular import)
def get_week7_quest_service():
    """Lazy import to avoid circular dependency."""
    from app.services.week7_quest_service import get_week7_quest_service as _get_service
    return _get_service()

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

# Bonus multiplier validation (HIGH: Validate bonus_multiplier range)
BONUS_MULTIPLIER_MIN = 1.0
BONUS_MULTIPLIER_MAX = 2.0
WEEKLY_CONSISTENCY_BONUS_MULTIPLIER = 1.5  # 50% XP bonus

# XP validation (CRITICAL: Prevent negative or excessive XP)
MIN_XP_PER_ACTIVITY = 0
MAX_XP_PER_ACTIVITY = 1000  # Maximum XP for a single activity
MAX_TOTAL_XP = 1000000  # Maximum total XP (prevents overflow)


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
                xp_awarded = xp_config["evaluation_high"]
            elif grade >= 1:
                xp_awarded = xp_config["evaluation_low"]
            else:
                xp_awarded = 0
        else:
            # Default: no XP
            xp_awarded = 0

        # CRITICAL: Validate XP is within acceptable range
        if xp_awarded < MIN_XP_PER_ACTIVITY:
            logger.warning(f"Negative XP calculated ({xp_awarded}) for {activity_type}, clamping to 0")
            xp_awarded = MIN_XP_PER_ACTIVITY
        elif xp_awarded > MAX_XP_PER_ACTIVITY:
            logger.warning(f"Excessive XP calculated ({xp_awarded}) for {activity_type}, clamping to {MAX_XP_PER_ACTIVITY}")
            xp_awarded = MAX_XP_PER_ACTIVITY

        return xp_awarded

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

            # Apply weekly consistency bonus if active
            consistency_bonus = 0
            if xp_awarded > 0 and getattr(stats.streak, 'bonus_active', False):
                bonus_multiplier = getattr(stats.streak, 'bonus_multiplier', 1.0)

                # HIGH: Validate bonus_multiplier range
                if not (BONUS_MULTIPLIER_MIN <= bonus_multiplier <= BONUS_MULTIPLIER_MAX):
                    logger.warning(f"Invalid bonus multiplier {bonus_multiplier} for user {user_id}, clamping to valid range")
                    bonus_multiplier = max(BONUS_MULTIPLIER_MIN, min(bonus_multiplier, BONUS_MULTIPLIER_MAX))

                if bonus_multiplier > 1.0:
                    original_xp = xp_awarded
                    xp_awarded = int(xp_awarded * bonus_multiplier)
                    consistency_bonus = xp_awarded - original_xp
                    logger.info(f"Weekly consistency bonus applied: {original_xp} XP -> {xp_awarded} XP (multiplier: {bonus_multiplier})")

            # Apply Week 7 double XP if quest is active
            week7_bonus = 0
            week7_quest_updates = {}
            if stats.week7_quest.active and xp_awarded > 0:
                # MEDIUM: week7_bonus represents the XP value that gets doubled
                # This includes any bonuses applied before Week 7 (e.g., consistency bonus)
                # Example: 100 base XP + 50 consistency = 150, then doubled to 300
                # week7_bonus = 150 (the value that was doubled, not the base XP)
                week7_bonus = xp_awarded  # XP value before doubling (includes consistency)
                xp_awarded = xp_awarded * 2  # Double the current XP
                logger.info(f"Week 7 quest active - doubled XP from {xp_awarded//2} to {xp_awarded}")

                # HIGH: Calculate quest updates NOW to avoid race condition
                # This will be included in the atomic update below
                quest_service = get_week7_quest_service()
                week7_quest_updates = quest_service.calculate_quest_updates(
                    user_id=user_id,
                    xp_bonus=week7_bonus,
                    stats=stats,
                    activity_type=activity_type,
                    course_id=course_id  # MEDIUM: Add course validation
                )

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

            # Check streak status
            current_time = datetime.now(timezone.utc)
            streak_maintained, new_streak_count, freeze_used = self.check_streak_status(
                user_id, current_time
            )

            # Update weekly consistency tracking
            consistency_updated, bonus_earned = self.update_weekly_consistency(
                user_id, activity_type, stats
            )

            # Check for badge earning
            badges_earned = self.check_and_award_badges(
                user_id, user_email, activity_type, activity_data, course_id
            )

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
                streak_maintained=streak_maintained,
                badges_earned=badges_earned,
                metadata={
                    "time_of_day": self._get_time_of_day(),
                    "freeze_used": freeze_used,
                    "consistency_bonus": consistency_bonus if consistency_bonus > 0 else None,
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

            # Update streak
            updates["streak.current_count"] = new_streak_count
            updates["streak.last_activity_date"] = current_time
            if new_streak_count > stats.streak.longest_streak:
                updates["streak.longest_streak"] = new_streak_count

            # Calculate net freeze change (earned - used)
            # This prevents race condition when both earning and using a freeze in same activity
            freeze_delta = freezes_to_add
            if freeze_used:
                freeze_delta -= 1

            # Apply freeze change if non-zero
            if freeze_delta != 0:
                updates["streak.freezes_available"] = Increment(freeze_delta)

            # Update weekly consistency if changed
            if consistency_updated:
                category_map = {
                    "flashcard_set_completed": "flashcards",
                    "quiz_completed": "quiz",
                    "evaluation_completed": "evaluation",
                    "study_guide_completed": "guide"
                }
                category = category_map.get(activity_type)
                if category:
                    updates[f"streak.weekly_consistency.{category}"] = True

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

            # HIGH: Include Week 7 quest updates in atomic update to prevent race condition
            if week7_quest_updates:
                updates.update(week7_quest_updates)
                logger.info(f"Including Week 7 quest updates in atomic update: {week7_quest_updates}")

            doc_ref.update(updates)

            logger.info(f"Logged activity {activity_type} for {user_id}, awarded {xp_awarded} XP, streak: {new_streak_count}")

            # Phase 4: Check for newly earned badges
            try:
                from app.services.badge_service import get_badge_service

                # Get updated user stats for badge checking
                updated_stats = self.get_user_stats(user_id)
                if updated_stats:
                    badge_service = get_badge_service()
                    newly_unlocked = badge_service.check_and_unlock_badges(
                        user_id=user_id,
                        user_stats=updated_stats,
                        trigger_type="activity"
                    )

                    if newly_unlocked:
                        badges_earned = [badge.badge_id for badge in newly_unlocked]
                        logger.info(f"Badges unlocked for {user_id}: {badges_earned}")
            except Exception as e:
                logger.error(f"Error checking badges for {user_id}: {e}")
                # Don't fail the activity logging if badge checking fails

            return ActivityLogResponse(
                activity_id=activity_id,
                xp_awarded=xp_awarded,
                new_total_xp=new_total_xp,
                level_up=level_up,
                new_level=new_level if level_up else None,
                new_level_title=new_level_title if level_up else None,
                streak_maintained=streak_maintained,
                new_streak_count=new_streak_count,
                freeze_used=freeze_used,
                badges_earned=badges_earned
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

    # =========================================================================
    # Streak Methods
    # =========================================================================

    def _get_streak_day(self, dt: datetime) -> datetime:
        """Get the streak day for a given datetime.

        A streak day starts at 4:00 AM and ends at 3:59:59 AM the next day.

        Args:
            dt: Datetime to get streak day for (should be in UTC)

        Returns:
            Date representing the streak day (normalized to midnight UTC)
        """
        # If before 4 AM, it's still the previous day's streak
        if dt.hour < STREAK_RESET_HOUR:
            streak_date = (dt - timedelta(days=1)).date()
        else:
            streak_date = dt.date()

        # Return as datetime at midnight UTC for consistency
        return datetime.combine(streak_date, datetime.min.time()).replace(tzinfo=timezone.utc)

    def check_streak_status(
        self,
        user_id: str,
        current_activity_time: datetime
    ) -> tuple[bool, int, bool]:
        """Check if activity maintains streak and calculate new streak count.

        Args:
            user_id: User's IAP user ID
            current_activity_time: Time of current activity (UTC)

        Returns:
            Tuple of (streak_maintained, new_streak_count, freeze_used)

        Raises:
            ValueError: If activity time is in the future
            HTTPException: If Firestore is unavailable
        """
        # Validate timestamp is not in future (allow 5 min clock skew)
        if current_activity_time > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Activity time cannot be in the future")

        if not self.db:
            logger.error("Firestore unavailable - cannot check streak")
            raise HTTPException(status_code=503, detail="Database unavailable")

        try:
            # Get user stats
            stats = self.get_user_stats(user_id)
            if not stats:
                # First activity ever
                return True, 1, False

            # Get current streak day
            current_day = self._get_streak_day(current_activity_time)

            # Get last activity day
            if not stats.last_active:
                # No previous activity
                return True, 1, False

            last_day = self._get_streak_day(stats.last_active)

            # Calculate days difference between streak days
            # Note: days_diff represents the number of streak days between activities
            # Example: Last activity Monday, current activity Wednesday = days_diff of 2
            # This means the user missed exactly 1 day (Tuesday)
            days_diff = (current_day - last_day).days

            if days_diff == 0:
                # Same streak day - maintain current streak
                # Example: Multiple activities on same calendar day (after 4 AM)
                return True, stats.streak.current_count, False

            elif days_diff == 1:
                # Consecutive streak days - increment streak
                # Example: Activity Monday, then activity Tuesday (both after 4 AM)
                return True, stats.streak.current_count + 1, False

            elif days_diff == 2 and stats.streak.freezes_available > 0:
                # Missed exactly 1 day but have freeze available - use it
                # Example: Activity Monday, skip Tuesday, activity Wednesday
                # days_diff = 2 means we missed exactly 1 day (Tuesday)
                # Use freeze to maintain streak without incrementing
                return True, stats.streak.current_count, True

            else:
                # Streak broken - either missed >1 day or no freeze available
                # Reset streak to 1 for this new activity
                return False, 1, False

        except ValueError as e:
            # Re-raise validation errors (e.g., future timestamp)
            logger.error(f"Invalid data for streak check: {e}")
            raise
        except Exception as e:
            # Log unexpected errors and re-raise as HTTPException
            logger.error(f"Unexpected error checking streak status for {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error checking streak status")

    def update_weekly_consistency(
        self,
        user_id: str,
        activity_type: str,
        stats: UserStats
    ) -> tuple[bool, bool]:
        """Update weekly consistency tracking and check for bonus.

        Args:
            user_id: User's IAP user ID
            activity_type: Type of activity completed
            stats: Current user stats

        Returns:
            Tuple of (consistency_updated, bonus_earned)
        """
        try:
            # Map activity types to consistency categories
            category_map = {
                "flashcard_set_completed": "flashcards",
                "quiz_completed": "quiz",
                "evaluation_completed": "evaluation",
                "study_guide_completed": "guide"
            }

            category = category_map.get(activity_type)
            if not category:
                # Activity doesn't count toward consistency
                return False, False

            # Check if we need to reset weekly consistency (new week)
            current_time = datetime.now(timezone.utc)
            week_start = self._get_week_start(current_time)

            # Get stored week start from stats
            stored_week_start = getattr(stats.streak, 'week_start', None)
            if stored_week_start:
                if isinstance(stored_week_start, str):
                    stored_week_start = datetime.fromisoformat(stored_week_start)
                elif not isinstance(stored_week_start, datetime):
                    stored_week_start = None

            # Reset if new week - use transaction to prevent data loss
            if not stored_week_start or week_start > stored_week_start:
                # New week - reset all categories atomically
                if not self.db:
                    return False, False

                from google.cloud import firestore

                doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)

                @firestore.transactional
                def reset_week_transaction(transaction):
                    """Transaction to safely reset weekly consistency.

                    CRITICAL: Prevents data loss from concurrent resets.
                    """
                    snapshot = doc_ref.get(transaction=transaction)

                    if not snapshot.exists:
                        return False

                    data = snapshot.to_dict()
                    current_week_start = data.get("streak", {}).get("week_start")

                    # Parse stored week start
                    if current_week_start:
                        if isinstance(current_week_start, str):
                            current_week_start = datetime.fromisoformat(current_week_start)

                    # Double-check we still need to reset (race condition check)
                    if current_week_start and week_start <= current_week_start:
                        # Another thread already reset, skip
                        return False

                    # Perform atomic reset
                    transaction.update(doc_ref, {
                        "streak.weekly_consistency.flashcards": False,
                        "streak.weekly_consistency.quiz": False,
                        "streak.weekly_consistency.evaluation": False,
                        "streak.weekly_consistency.guide": False,
                        "streak.week_start": week_start.isoformat(),
                        "streak.bonus_active": False,
                        "updated_at": datetime.now(timezone.utc)
                    })

                    logger.info(f"Weekly consistency reset for {user_id} (new week: {week_start.isoformat()})")
                    return True

                # Execute transaction
                transaction = self.db.transaction()
                reset_performed = reset_week_transaction(transaction)

                if not reset_performed:
                    # Another thread already reset, continue with current stats
                    logger.debug(f"Weekly reset skipped for {user_id} (already reset by another thread)")

                # Refresh stats after reset
                stats = self.get_or_create_user_stats(user_id, stats.user_email)
                if not stats:
                    return False, False

            # Check if category already completed this week
            if stats.streak.weekly_consistency.get(category, False):
                # Already completed this category this week
                return False, False

            # Use transaction to prevent race conditions when updating consistency
            # CRITICAL: Prevents duplicate bonus activation
            if self.db:
                from google.cloud import firestore

                doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)

                @firestore.transactional
                def update_consistency_transaction(transaction):
                    """Transaction to safely update weekly consistency."""
                    snapshot = doc_ref.get(transaction=transaction)

                    if not snapshot.exists:
                        return False, False

                    data = snapshot.to_dict()
                    current_consistency = data.get("streak", {}).get("weekly_consistency", {})

                    # Double-check category not already completed (race condition check)
                    if current_consistency.get(category, False):
                        return False, False

                    # Update category
                    updated_consistency = current_consistency.copy()
                    updated_consistency[category] = True

                    # Check if all 4 categories complete
                    all_complete = all(updated_consistency.values())
                    bonus_active = data.get("streak", {}).get("bonus_active", False)
                    bonus_earned = all_complete and not bonus_active

                    # Build update dict
                    updates = {
                        f"streak.weekly_consistency.{category}": True
                    }

                    if bonus_earned:
                        # HIGH: Validate bonus_multiplier range
                        multiplier = WEEKLY_CONSISTENCY_BONUS_MULTIPLIER
                        if not (BONUS_MULTIPLIER_MIN <= multiplier <= BONUS_MULTIPLIER_MAX):
                            logger.error(f"Invalid bonus multiplier {multiplier}, using default 1.5")
                            multiplier = 1.5

                        updates["streak.bonus_active"] = True
                        updates["streak.bonus_multiplier"] = multiplier

                    transaction.update(doc_ref, updates)

                    return True, bonus_earned

                # Execute transaction
                transaction = self.db.transaction()
                consistency_updated, bonus_earned = update_consistency_transaction(transaction)

                if bonus_earned:
                    logger.info(f"Weekly consistency bonus earned for {user_id}")

                return consistency_updated, bonus_earned

            return False, False

        except Exception as e:
            logger.error(f"Error updating weekly consistency for {user_id}: {e}", exc_info=True)
            return False, False

    def _get_week_start(self, dt: datetime) -> datetime:
        """Get the start of the week (Monday at 4:00 AM) for a given datetime.

        Args:
            dt: Datetime to get week start for

        Returns:
            Datetime representing Monday at 4:00 AM of the week
        """
        # Get the Monday of the current week
        days_since_monday = dt.weekday()  # 0 = Monday, 6 = Sunday
        monday = dt - timedelta(days=days_since_monday)

        # Set to 4:00 AM (streak reset time)
        week_start = monday.replace(hour=STREAK_RESET_HOUR, minute=0, second=0, microsecond=0)

        # If current time is before Monday 4 AM, use previous week's Monday
        if dt < week_start:
            week_start = week_start - timedelta(days=7)

        return week_start

    def update_streak(
        self,
        user_id: str,
        streak_maintained: bool,
        new_streak_count: int,
        freeze_used: bool
    ) -> bool:
        """Update user's streak information.

        Args:
            user_id: User's IAP user ID
            streak_maintained: Whether streak was maintained
            new_streak_count: New streak count
            freeze_used: Whether a freeze was used

        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return False

        try:
            stats = self.get_user_stats(user_id)
            if not stats:
                return False

            updates = {
                "streak.current_count": new_streak_count,
                "streak.last_activity_date": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # Update longest streak if current is higher
            if new_streak_count > stats.streak.longest_streak:
                updates["streak.longest_streak"] = new_streak_count

            # Decrement freeze if used
            if freeze_used:
                updates["streak.freezes_available"] = Increment(-1)
                logger.info(f"Streak freeze used for {user_id}, new count: {stats.streak.freezes_available - 1}")

            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            doc_ref.update(updates)

            return True

        except Exception as e:
            logger.error(f"Error updating streak for {user_id}: {e}")
            return False

    def get_user_activities(
        self,
        user_id: str,
        limit: int = DEFAULT_QUERY_LIMIT,
        activity_type: Optional[str] = None,
        start_after_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[List[UserActivity], Optional[str]]:
        """Get user's recent activities with pagination support.

        CRITICAL: Added start_date/end_date support (BLOCKS MERGE - feature was broken)

        Args:
            user_id: User's IAP user ID
            limit: Maximum number of activities to return
            activity_type: Optional filter by activity type
            start_after_id: Optional activity ID to start after (for pagination)
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)

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

            # CRITICAL: Add date range filtering
            if start_date:
                query = query.where(filter=FieldFilter("timestamp", ">=", start_date))

            if end_date:
                query = query.where(filter=FieldFilter("timestamp", "<=", end_date))

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

    # =========================================================================
    # Badge Management Methods
    # =========================================================================

    def seed_badge_definitions(self) -> bool:
        """Seed initial badge definitions to Firestore.

        Creates the 6 core badge types with their tier requirements.
        Safe to call multiple times - will not overwrite existing badges.

        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return False

        try:
            badges = [
                BadgeDefinition(
                    badge_id="night_owl",
                    name="Night Owl",
                    description="Complete a Hard Quiz or AI Evaluation between 11:00 PM and 3:00 AM",
                    icon="🦉",
                    category="behavioral",
                    tiers=["bronze", "silver", "gold"],
                    tier_requirements={"bronze": 1, "silver": 5, "gold": 10}
                ),
                BadgeDefinition(
                    badge_id="early_riser",
                    name="Early Riser",
                    description="Complete a Study Guide before 8:00 AM",
                    icon="☀️",
                    category="behavioral",
                    tiers=["bronze", "silver", "gold"],
                    tier_requirements={"bronze": 1, "silver": 5, "gold": 10}
                ),
                BadgeDefinition(
                    badge_id="hat_trick",
                    name="Hat Trick",
                    description="Pass 3 separate Hard Quizzes in a row with 100% accuracy",
                    icon="🎩",
                    category="achievement",
                    tiers=["bronze", "silver", "gold"],
                    tier_requirements={"bronze": 1, "silver": 3, "gold": 5}
                ),
                BadgeDefinition(
                    badge_id="combo_king",
                    name="Combo King",
                    description="Flip 20 Flashcards in a row without marking one as incorrect",
                    icon="🔥",
                    category="achievement",
                    tiers=["bronze", "silver", "gold"],
                    tier_requirements={"bronze": 1, "silver": 5, "gold": 10}
                ),
                BadgeDefinition(
                    badge_id="legal_scholar",
                    name="Legal Scholar",
                    description="Achieve an AI Grade of 9 or 10 on three consecutive Evaluations",
                    icon="⚖️",
                    category="achievement",
                    tiers=["bronze", "silver", "gold"],
                    tier_requirements={"bronze": 1, "silver": 3, "gold": 5}
                ),
                BadgeDefinition(
                    badge_id="deep_diver",
                    name="Deep Diver",
                    description="Spend 45+ minutes interacting with a single Study Guide without navigating away",
                    icon="📖",
                    category="behavioral",
                    tiers=["bronze", "silver", "gold"],
                    tier_requirements={"bronze": 1, "silver": 5, "gold": 10}
                )
            ]

            for badge in badges:
                badge_ref = self.db.collection(BADGE_DEFINITIONS_COLLECTION).document(badge.badge_id)
                # Only create if doesn't exist
                if not badge_ref.get().exists:
                    badge_ref.set(badge.model_dump(mode='json'))
                    logger.info(f"Created badge definition: {badge.badge_id}")
                else:
                    logger.debug(f"Badge definition already exists: {badge.badge_id}")

            logger.info("Badge definitions seeded successfully")
            return True

        except Exception as e:
            logger.error(f"Error seeding badge definitions: {e}")
            return False

    def get_badge_definitions(self) -> List[BadgeDefinition]:
        """Get all badge definitions.

        Returns:
            List of BadgeDefinition objects
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return []

        try:
            # Get all badge definitions (no filter - all badges are active)
            docs = self.db.collection(BADGE_DEFINITIONS_COLLECTION).stream()

            badges = []
            for doc in docs:
                try:
                    badge_data = doc.to_dict()
                    badges.append(BadgeDefinition(**badge_data))
                except Exception as e:
                    logger.warning(f"Error parsing badge {doc.id}: {e}")
                    continue

            return badges

        except Exception as e:
            logger.error(f"Error getting badge definitions: {e}")
            return []

    def get_user_badges(self, user_id: str) -> List[UserBadge]:
        """Get all badges earned by a user.

        Args:
            user_id: User's IAP user ID

        Returns:
            List of UserBadge objects
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return []

        try:
            docs = self.db.collection(USER_ACHIEVEMENTS_COLLECTION).document(user_id).collection("badges").stream()

            badges = []
            for doc in docs:
                try:
                    badge_data = doc.to_dict()
                    badges.append(UserBadge(**badge_data))
                except Exception as e:
                    logger.warning(f"Error parsing user badge {doc.id}: {e}")
                    continue

            return badges

        except Exception as e:
            logger.error(f"Error getting user badges for {user_id}: {e}")
            return []

    def check_and_award_badges(
        self,
        user_id: str,
        user_email: str,
        activity_type: str,
        activity_data: Dict[str, Any],
        course_id: Optional[str] = None
    ) -> List[str]:
        """Check if activity earns any badges and award them.

        Args:
            user_id: User's IAP user ID
            user_email: User's email address
            activity_type: Type of activity
            activity_data: Activity-specific data
            course_id: Course ID if applicable

        Returns:
            List of badge IDs earned
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return []

        earned_badge_ids = []

        try:
            # Validate activity data inputs
            consecutive_correct = activity_data.get("consecutive_correct", 0)
            if not isinstance(consecutive_correct, int) or consecutive_correct < 0:
                logger.warning(f"Invalid consecutive_correct value: {consecutive_correct}, defaulting to 0")
                consecutive_correct = 0
                activity_data["consecutive_correct"] = consecutive_correct

            time_spent_minutes = activity_data.get("time_spent_minutes", 0)
            if not isinstance(time_spent_minutes, (int, float)) or time_spent_minutes < 0:
                logger.warning(f"Invalid time_spent_minutes value: {time_spent_minutes}, defaulting to 0")
                time_spent_minutes = 0
                activity_data["time_spent_minutes"] = time_spent_minutes

            difficulty = activity_data.get("difficulty")
            if difficulty and not isinstance(difficulty, str):
                logger.warning(f"Invalid difficulty value: {difficulty}, setting to None")
                activity_data["difficulty"] = None

            # Get current time for time-based badges
            current_time = datetime.now(timezone.utc)
            hour = current_time.hour

            # Check Night Owl badge (11 PM - 3 AM)
            if activity_type in ["quiz_completed", "evaluation_completed"]:
                if activity_type == "quiz_completed" and activity_data.get("difficulty") == "hard":
                    if hour >= 23 or hour < 3:
                        badge_id = self._award_badge(user_id, user_email, "night_owl", course_id)
                        if badge_id:
                            earned_badge_ids.append(badge_id)
                elif activity_type == "evaluation_completed":
                    if hour >= 23 or hour < 3:
                        badge_id = self._award_badge(user_id, user_email, "night_owl", course_id)
                        if badge_id:
                            earned_badge_ids.append(badge_id)

            # Check Early Riser badge (before 8 AM)
            if activity_type == "study_guide_completed":
                if hour < 8:
                    badge_id = self._award_badge(user_id, user_email, "early_riser", course_id)
                    if badge_id:
                        earned_badge_ids.append(badge_id)

            # Check Deep Diver badge (45+ minutes on study guide)
            if activity_type == "study_guide_completed":
                time_spent_minutes = activity_data.get("time_spent_minutes", 0)
                if time_spent_minutes >= 45:
                    badge_id = self._award_badge(user_id, user_email, "deep_diver", course_id)
                    if badge_id:
                        earned_badge_ids.append(badge_id)

            # Check Combo King badge (20 flashcards in a row correct)
            if activity_type == "flashcard_set_completed":
                consecutive_correct = activity_data.get("consecutive_correct", 0)
                if consecutive_correct >= 20:
                    badge_id = self._award_badge(user_id, user_email, "combo_king", course_id)
                    if badge_id:
                        earned_badge_ids.append(badge_id)

            # Check sequence badges (Hat Trick, Legal Scholar)
            # These require checking recent activity history
            if activity_type == "quiz_completed":
                if self._check_hat_trick(user_id, activity_data):
                    badge_id = self._award_badge(user_id, user_email, "hat_trick", course_id)
                    if badge_id:
                        earned_badge_ids.append(badge_id)

            if activity_type == "evaluation_completed":
                if self._check_legal_scholar(user_id, activity_data):
                    badge_id = self._award_badge(user_id, user_email, "legal_scholar", course_id)
                    if badge_id:
                        earned_badge_ids.append(badge_id)

            return earned_badge_ids

        except Exception as e:
            logger.error(f"Error checking badges for {user_id}: {e}")
            return []

    def _award_badge(
        self,
        user_id: str,
        user_email: str,
        badge_id: str,
        course_id: Optional[str] = None
    ) -> Optional[str]:
        """Award a badge to a user or increment times_earned.

        Args:
            user_id: User's IAP user ID
            user_email: User's email address
            badge_id: Badge ID to award
            course_id: Course ID if applicable

        Returns:
            Badge ID if awarded/upgraded, None otherwise
        """
        try:
            # Get badge definition
            badge_def_ref = self.db.collection(BADGE_DEFINITIONS_COLLECTION).document(badge_id)
            badge_def_doc = badge_def_ref.get()

            if not badge_def_doc.exists:
                logger.error(f"Badge definition not found: {badge_id} - possible configuration error. Badge may not be seeded or badge_id is misspelled.")
                return None

            badge_def_data = badge_def_doc.to_dict()
            badge_def = BadgeDefinition(**badge_def_data)

            # Check if user already has this badge
            user_badge_ref = self.db.collection(USER_ACHIEVEMENTS_COLLECTION).document(user_id).collection("badges").document(badge_id)
            user_badge_doc = user_badge_ref.get()

            if user_badge_doc.exists:
                # Use atomic increment to prevent race conditions
                user_badge_data = user_badge_doc.to_dict()
                current_tier = user_badge_data.get("tier", "bronze")

                # Atomically increment times_earned
                user_badge_ref.update({
                    "times_earned": Increment(1),
                    "last_earned_at": datetime.now(timezone.utc)
                })

                # Re-read document to get accurate times_earned after atomic increment
                # This prevents race conditions where concurrent requests could cause incorrect tier calculations
                refreshed_doc = user_badge_ref.get()
                if refreshed_doc.exists:
                    refreshed_data = refreshed_doc.to_dict()
                    new_times_earned = refreshed_data.get("times_earned", 0)
                else:
                    logger.error(f"Badge document disappeared after update: {badge_id} for {user_id}")
                    return None

                # Check for tier upgrade based on accurate times_earned
                new_tier = current_tier
                for tier in ["gold", "silver", "bronze"]:  # Check from highest to lowest
                    if new_times_earned >= badge_def.tier_requirements.get(tier, 999):
                        new_tier = tier
                        break

                # Update tier if upgraded
                if new_tier != current_tier:
                    user_badge_ref.update({"tier": new_tier})
                    logger.info(f"Badge {badge_id} upgraded to {new_tier} for {user_id} (earned {new_times_earned} times)")
                    return badge_id
                else:
                    logger.debug(f"Badge {badge_id} times_earned incremented to {new_times_earned} for {user_id}")
                    return None
            else:
                # Create new badge
                user_badge = UserBadge(
                    user_id=user_id,
                    badge_id=badge_id,
                    badge_name=badge_def.name,
                    badge_description=badge_def.description,
                    badge_icon=badge_def.icon,
                    tier="bronze",
                    earned_at=datetime.now(timezone.utc),
                    times_earned=1,
                    course_id=course_id
                )

                user_badge_ref.set(user_badge.model_dump(mode='json'))
                logger.info(f"Badge {badge_id} awarded to {user_id}")
                return badge_id

        except Exception as e:
            logger.error(f"Error awarding badge {badge_id} to {user_id}: {e}")
            return None

    def _check_hat_trick(self, user_id: str, current_activity_data: Dict[str, Any]) -> bool:
        """Check if user has passed 3 hard quizzes in a row with 100% accuracy.

        Args:
            user_id: User's IAP user ID
            current_activity_data: Current quiz activity data

        Returns:
            True if Hat Trick achieved, False otherwise
        """
        try:
            # Check if current quiz qualifies
            if current_activity_data.get("difficulty") != "hard":
                return False

            score = current_activity_data.get("score", 0)
            total = current_activity_data.get("total_questions", 1)
            if score != total or total == 0:
                return False

            # Get last 3 quiz activities (need to check the 2 immediately preceding quizzes)
            activities, _ = self.get_user_activities(user_id, limit=3, activity_type="quiz_completed")

            # Check that the 2 most recent quizzes (before current) are CONSECUTIVE perfect hard quizzes
            # This ensures we have 3 in a row: [previous-2, previous-1, current]
            perfect_hard_count = 0
            for activity in activities[:2]:  # Only check the 2 most recent (before current)
                if activity.activity_data.get("difficulty") == "hard":
                    act_score = activity.activity_data.get("score", 0)
                    act_total = activity.activity_data.get("total_questions", 1)
                    if act_score == act_total and act_total > 0:
                        perfect_hard_count += 1
                    else:
                        # Not perfect - sequence broken
                        break
                else:
                    # Not hard quiz - sequence broken
                    break

            # Need 2 consecutive previous perfect hard quizzes + current one = 3 in a row
            return perfect_hard_count >= 2

        except Exception as e:
            logger.error(f"Error checking Hat Trick for {user_id}: {e}")
            return False

    def _check_legal_scholar(self, user_id: str, current_activity_data: Dict[str, Any]) -> bool:
        """Check if user has achieved grade 9-10 on 3 consecutive evaluations.

        Args:
            user_id: User's IAP user ID
            current_activity_data: Current evaluation activity data

        Returns:
            True if Legal Scholar achieved, False otherwise
        """
        try:
            # Check if current evaluation qualifies
            current_grade = current_activity_data.get("grade", 0)
            if current_grade < 9:
                return False

            # Get last 3 evaluation activities (need to check the 2 immediately preceding evaluations)
            activities, _ = self.get_user_activities(user_id, limit=3, activity_type="evaluation_completed")

            # Check that the 2 most recent evaluations (before current) are CONSECUTIVE high grades
            # This ensures we have 3 in a row: [previous-2, previous-1, current]
            high_grade_count = 0
            for activity in activities[:2]:  # Only check the 2 most recent (before current)
                grade = activity.activity_data.get("grade", 0)
                if grade >= 9:
                    high_grade_count += 1
                else:
                    # Grade below 9 - sequence broken
                    break

            # Need 2 consecutive previous high grades + current one = 3 in a row
            return high_grade_count >= 2

        except Exception as e:
            logger.error(f"Error checking Legal Scholar for {user_id}: {e}")
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

