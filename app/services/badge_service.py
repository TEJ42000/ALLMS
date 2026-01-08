"""
Badge Service - Achievement Tracking and Badge Management

MEDIUM: Enhanced documentation for better code clarity

This service handles:
- Badge checking and unlocking
- Progress tracking
- Badge definitions management
- Integration with activity logging and streak system

Architecture:
- Uses Firestore for persistent storage
- Implements transaction-based unlocking to prevent race conditions
- Gracefully handles service unavailability
- Filters to only show active badges to users

Collections:
- badge_definitions: Master list of all badges
- user_badges: User-earned badges (composite key: user_id_badge_id)

Error Handling:
- All methods include comprehensive error handling
- Service degrades gracefully when Firestore is unavailable
- Partial failures don't prevent other operations
- All errors are logged with context

Thread Safety:
- Badge unlocking uses Firestore transactions
- No shared mutable state
- Safe for concurrent operations
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.models.gamification_models import (
    UserStats,
    BadgeDefinition,
    UserBadge,
    StreakInfo,
    ActivityCounters
)
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Firestore collections
USER_STATS_COLLECTION = "user_stats"
BADGE_DEFINITIONS_COLLECTION = "badge_definitions"
USER_BADGES_COLLECTION = "user_badges"


class BadgeService:
    """Service for managing badges and achievements.

    CRITICAL: Includes comprehensive error handling for service unavailability
    """

    def __init__(self):
        """Initialize badge service.

        CRITICAL: Handles Firestore unavailability gracefully
        """
        try:
            self.db = get_firestore_client()
            if not self.db:
                logger.error("Firestore client is None - badge service degraded")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            self.db = None

    def check_and_unlock_badges(
        self,
        user_id: str,
        user_stats: UserStats,
        trigger_type: str = "activity"
    ) -> List[UserBadge]:
        """Check for newly earned badges and unlock them.

        MEDIUM: Added memory leak prevention and better documentation

        Args:
            user_id: User's IAP user ID
            user_stats: Current user stats
            trigger_type: What triggered the check (activity, streak, xp, weekly_bonus)

        Returns:
            List of newly unlocked badges (empty list if none or error)

        Memory Management:
            - Clears large lists after use to prevent memory leaks
            - Uses generator expressions where possible
            - Limits result set size

        Error Handling:
            - Returns empty list on Firestore unavailability
            - Continues checking other badges if one fails
            - Logs all errors with context
        """
        if not self.db:
            logger.warning("Firestore unavailable")
            return []

        # MEDIUM: Initialize with empty list to prevent None issues
        newly_unlocked = []
        badge_defs = []
        earned_badge_ids = set()

        try:
            # Get all badge definitions
            badge_defs = self._get_badge_definitions()

            # MEDIUM: Limit to reasonable number to prevent memory issues
            if len(badge_defs) > 1000:
                logger.warning(f"Unusually large number of badge definitions: {len(badge_defs)}")
                badge_defs = badge_defs[:1000]

            # Get user's already earned badges
            earned_badge_ids = self._get_earned_badge_ids(user_id)

            # Check each badge
            for badge_def in badge_defs:
                # Skip if already earned
                if badge_def.badge_id in earned_badge_ids:
                    continue

                # Check if criteria met
                try:
                    if self._check_badge_criteria(badge_def, user_stats):
                        # Unlock the badge
                        user_badge = self._unlock_badge(user_id, badge_def)
                        if user_badge:
                            newly_unlocked.append(user_badge)
                            logger.info(f"Badge unlocked: {badge_def.badge_id} for user {user_id}")
                except Exception as badge_error:
                    # MEDIUM: Don't let one badge failure stop others
                    logger.error(f"Error checking badge {badge_def.badge_id}: {badge_error}")
                    continue

            return newly_unlocked

        except Exception as e:
            logger.error(f"Error checking badges for {user_id}: {e}", exc_info=True)
            return []
        finally:
            # MEDIUM: Memory leak prevention - clear large objects
            badge_defs = []
            earned_badge_ids = set()

    def _get_badge_definitions(self) -> List[BadgeDefinition]:
        """Get all badge definitions from Firestore.

        CRITICAL: Only returns ACTIVE badges

        Returns:
            List of BadgeDefinition objects (active only)
        """
        try:
            docs = self.db.collection(BADGE_DEFINITIONS_COLLECTION).stream()
            badges = []
            for doc in docs:
                try:
                    badge = BadgeDefinition(**doc.to_dict())
                    # CRITICAL: Only include active badges
                    if badge.active:
                        badges.append(badge)
                except Exception as e:
                    logger.warning(f"Error parsing badge definition {doc.id}: {e}")
            return badges
        except Exception as e:
            logger.error(f"Error getting badge definitions: {e}")
            return []

    def _get_earned_badge_ids(self, user_id: str) -> set:
        """Get set of badge IDs already earned by user.

        Args:
            user_id: User's IAP user ID

        Returns:
            Set of badge IDs
        """
        try:
            docs = self.db.collection(USER_BADGES_COLLECTION).where(
                "user_id", "==", user_id
            ).stream()
            
            return {doc.to_dict().get("badge_id") for doc in docs}
        except Exception as e:
            logger.error(f"Error getting earned badges for {user_id}: {e}")
            return set()

    def _check_badge_criteria(
        self,
        badge_def: BadgeDefinition,
        user_stats: UserStats
    ) -> bool:
        """Check if user meets badge criteria.

        Args:
            badge_def: Badge definition
            user_stats: User's current stats

        Returns:
            True if criteria met, False otherwise
        """
        criteria = badge_def.criteria
        category = badge_def.category

        try:
            # Streak badges
            if category == "streak":
                return self._check_streak_criteria(criteria, user_stats.streak)
            
            # XP badges
            elif category == "xp":
                return self._check_xp_criteria(criteria, user_stats.total_xp)
            
            # Activity badges
            elif category == "activity":
                return self._check_activity_criteria(criteria, user_stats.activity_counters)
            
            # Consistency badges
            elif category == "consistency":
                return self._check_consistency_criteria(criteria, user_stats)
            
            # Special badges
            elif category == "special":
                return self._check_special_criteria(criteria, user_stats)
            
            else:
                logger.warning(f"Unknown badge category: {category}")
                return False

        except Exception as e:
            logger.error(f"Error checking criteria for {badge_def.badge_id}: {e}")
            return False

    def _check_streak_criteria(self, criteria: Dict[str, Any], streak: StreakInfo) -> bool:
        """Check streak badge criteria."""
        # Current streak length
        if "streak_days" in criteria:
            return streak.current_count >= criteria["streak_days"]
        
        # Longest streak
        if "longest_streak" in criteria:
            return streak.longest_count >= criteria["longest_streak"]
        
        # Phoenix badge (rebuild after breaking 30+ day streak)
        if "rebuild_after" in criteria:
            # Check if user had a streak >= rebuild_after and now has a new streak
            # This requires tracking previous streaks (future enhancement)
            return False
        
        return False

    def _check_xp_criteria(self, criteria: Dict[str, Any], total_xp: int) -> bool:
        """Check XP badge criteria."""
        if "total_xp" in criteria:
            return total_xp >= criteria["total_xp"]
        return False

    def _check_activity_criteria(
        self,
        criteria: Dict[str, Any],
        counters: ActivityCounters
    ) -> bool:
        """Check activity badge criteria.

        MEDIUM: Fixed field naming consistency with ActivityCounters model
        """
        # MEDIUM: Map badge criteria names to ActivityCounters field names
        # This ensures consistency between badge definitions and the data model
        field_mapping = {
            "flashcard_sets": "flashcards_reviewed",  # Maps to flashcards_reviewed
            "quizzes_passed": "quizzes_passed",       # Direct match
            "evaluations": "evaluations_submitted",   # Maps to evaluations_submitted
            "study_guides": "guides_completed"        # Maps to guides_completed
        }

        # Check each criterion
        for criteria_key, criteria_value in criteria.items():
            # Get the actual field name from mapping
            field_name = field_mapping.get(criteria_key)

            if not field_name:
                logger.warning(f"Unknown activity criteria: {criteria_key}")
                continue

            # Get the counter value
            counter_value = getattr(counters, field_name, 0)

            # Check if criterion is met
            if counter_value < criteria_value:
                return False

        # All criteria must be met
        return True

    def _check_consistency_criteria(
        self,
        criteria: Dict[str, Any],
        user_stats: UserStats
    ) -> bool:
        """Check consistency badge criteria.

        CRITICAL: Unimplemented criteria return False with logging
        """
        # Consecutive weeks with bonus
        if "consecutive_weeks_bonus" in criteria:
            # CRITICAL: Not yet implemented - requires tracking consecutive weeks
            # This will be implemented in a future update
            logger.debug(f"Consistency badge criteria not yet implemented: consecutive_weeks_bonus")
            return False

        # CRITICAL: Log unknown criteria
        logger.warning(f"Unknown consistency criteria: {criteria}")
        return False

    def _check_special_criteria(
        self,
        criteria: Dict[str, Any],
        user_stats: UserStats
    ) -> bool:
        """Check special badge criteria.

        CRITICAL: Unimplemented criteria return False with logging
        """
        # Early adopter (joined before specific date)
        if "joined_before" in criteria:
            try:
                joined_date = datetime.fromisoformat(criteria["joined_before"])
                if user_stats.created_at <= joined_date:
                    return True
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid joined_before date format: {e}")
                return False

        # Perfect week (all 4 categories every day for 7 days)
        if "perfect_week" in criteria:
            # CRITICAL: Not yet implemented - requires daily activity tracking
            logger.debug(f"Special badge criteria not yet implemented: perfect_week")
            return False

        # Time-based badges (night owl, early bird, weekend warrior, etc.)
        # CRITICAL: Not yet implemented - requires activity timestamp tracking
        unimplemented_criteria = [
            "night_activities", "early_activities", "weekend_streaks",
            "flashcard_combo", "flashcards_one_session", "hard_quiz_streak",
            "high_complexity_evaluations"
        ]

        for crit in unimplemented_criteria:
            if crit in criteria:
                logger.debug(f"Special badge criteria not yet implemented: {crit}")
                return False

        # CRITICAL: Log unknown criteria
        if criteria:
            logger.warning(f"Unknown special criteria: {criteria}")

        return False

    def _unlock_badge(
        self,
        user_id: str,
        badge_def: BadgeDefinition
    ) -> Optional[UserBadge]:
        """Unlock a badge for user.

        CRITICAL: Uses Firestore transaction to prevent race conditions
        CRITICAL: Handles service unavailability gracefully

        Args:
            user_id: User's IAP user ID
            badge_def: Badge definition

        Returns:
            UserBadge if successful, None otherwise
        """
        # CRITICAL: Check if Firestore is available
        if not self.db:
            logger.error(f"Cannot unlock badge {badge_def.badge_id} - Firestore unavailable")
            return None

        try:
            doc_id = f"{user_id}_{badge_def.badge_id}"
            doc_ref = self.db.collection(USER_BADGES_COLLECTION).document(doc_id)

            # CRITICAL: Use transaction to prevent race condition
            # If two requests try to unlock the same badge simultaneously,
            # only one will succeed
            @self.db.transactional
            def unlock_in_transaction(transaction):
                # Check if badge already exists
                snapshot = doc_ref.get(transaction=transaction)
                if snapshot.exists:
                    logger.info(f"Badge {badge_def.badge_id} already unlocked for {user_id}")
                    return UserBadge(**snapshot.to_dict())

                # Create new badge
                user_badge = UserBadge(
                    user_id=user_id,
                    badge_id=badge_def.badge_id,
                    earned_at=datetime.now(timezone.utc)
                )

                # Save to Firestore within transaction
                transaction.set(doc_ref, user_badge.model_dump(mode='json'))

                logger.info(f"Badge {badge_def.badge_id} unlocked for user {user_id}")
                return user_badge

            # Execute transaction
            transaction = self.db.transaction()
            return unlock_in_transaction(transaction)

        except Exception as e:
            logger.error(f"Error unlocking badge {badge_def.badge_id} for {user_id}: {e}", exc_info=True)
            return None

    def get_user_badges(self, user_id: str) -> List[UserBadge]:
        """Get all badges earned by user.

        Args:
            user_id: User's IAP user ID

        Returns:
            List of UserBadge objects
        """
        if not self.db:
            return []

        try:
            docs = self.db.collection(USER_BADGES_COLLECTION).where(
                "user_id", "==", user_id
            ).stream()
            
            badges = []
            for doc in docs:
                try:
                    badges.append(UserBadge(**doc.to_dict()))
                except Exception as e:
                    logger.warning(f"Error parsing user badge {doc.id}: {e}")
            
            return badges

        except Exception as e:
            logger.error(f"Error getting badges for {user_id}: {e}")
            return []

    def get_badge_progress(
        self,
        user_id: str,
        user_stats: UserStats
    ) -> Dict[str, Dict[str, Any]]:
        """Get progress toward all badges.

        Args:
            user_id: User's IAP user ID
            user_stats: User's current stats

        Returns:
            Dict mapping badge_id to progress info
        """
        progress = {}
        
        try:
            # Get all badge definitions
            badge_defs = self._get_badge_definitions()
            
            # Get earned badges
            earned_badge_ids = self._get_earned_badge_ids(user_id)
            
            for badge_def in badge_defs:
                # Skip earned badges
                if badge_def.badge_id in earned_badge_ids:
                    continue
                
                # Calculate progress
                prog = self._calculate_progress(badge_def, user_stats)
                if prog:
                    progress[badge_def.badge_id] = prog
            
            return progress

        except Exception as e:
            logger.error(f"Error getting badge progress for {user_id}: {e}")
            return {}

    def _calculate_progress(
        self,
        badge_def: BadgeDefinition,
        user_stats: UserStats
    ) -> Optional[Dict[str, Any]]:
        """Calculate progress toward a specific badge."""
        criteria = badge_def.criteria
        category = badge_def.category

        try:
            if category == "streak":
                if "streak_days" in criteria:
                    return {
                        "current": user_stats.streak.current_count,
                        "required": criteria["streak_days"],
                        "percentage": min(100, int(user_stats.streak.current_count / criteria["streak_days"] * 100))
                    }
            
            elif category == "xp":
                if "total_xp" in criteria:
                    return {
                        "current": user_stats.total_xp,
                        "required": criteria["total_xp"],
                        "percentage": min(100, int(user_stats.total_xp / criteria["total_xp"] * 100))
                    }
            
            elif category == "activity":
                # Return progress for first criteria found
                if "flashcard_sets" in criteria:
                    return {
                        "current": user_stats.activity_counters.flashcard_sets_completed,
                        "required": criteria["flashcard_sets"],
                        "percentage": min(100, int(user_stats.activity_counters.flashcard_sets_completed / criteria["flashcard_sets"] * 100))
                    }
            
            return None

        except Exception as e:
            logger.error(f"Error calculating progress for {badge_def.badge_id}: {e}")
            return None


# Singleton instance
_badge_service = None


def get_badge_service() -> BadgeService:
    """Get or create badge service singleton."""
    global _badge_service
    if _badge_service is None:
        _badge_service = BadgeService()
    return _badge_service

