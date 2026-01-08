"""Week 7 Boss Quest Service.

Manages the Week 7 "Boss Prep" quest system with double XP rewards and exam readiness tracking.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from app.models.gamification_models import UserStats, Week7Quest
from app.services.gcp_service import get_firestore_client
from app.services.course_service import get_course_service

logger = logging.getLogger(__name__)

# Firestore collection names
USER_STATS_COLLECTION = "user_stats"

# Quest configuration
WEEK7_QUEST_DURATION_DAYS = 7  # Quest lasts for 7 days
DOUBLE_XP_MULTIPLIER = 2.0
EXAM_READINESS_THRESHOLDS = {
    "flashcards": 50,  # Complete 50 flashcards
    "quizzes": 5,      # Pass 5 quizzes
    "evaluations": 3,  # Complete 3 evaluations
    "guides": 2        # Complete 2 study guides
}


class Week7QuestService:
    """Service for managing Week 7 Boss Quest."""

    def __init__(self):
        """Initialize the Week 7 quest service."""
        self.db = get_firestore_client()
        self.course_service = get_course_service()

    def check_and_activate_quest(
        self,
        user_id: str,
        course_id: str,
        current_week: int
    ) -> tuple[bool, Optional[str]]:
        """Check if Week 7 quest should be activated.

        Args:
            user_id: User's IAP user ID
            course_id: Course ID
            current_week: Current week number

        Returns:
            Tuple of (activated, message)
        """
        if not self.db:
            return False, "Firestore unavailable"

        try:
            # Check if it's Week 7
            if current_week != 7:
                return False, None

            # Get user stats
            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return False, "User stats not found"

            stats = UserStats(**doc.to_dict())

            # HIGH: Validate course_id matches current course
            if stats.course_id and stats.course_id != course_id:
                return False, f"Quest must be activated for current course (expected: {course_id}, got: {stats.course_id})"

            # Check if quest is already active
            if stats.week7_quest.active:
                return False, "Quest already active"

            # Check if quest was already completed
            if stats.week7_quest.boss_battle_completed:
                return False, "Quest already completed"

            # Activate quest
            doc_ref.update({
                "week7_quest.active": True,
                "week7_quest.exam_readiness_percent": 0,
                "week7_quest.boss_battle_completed": False,
                "week7_quest.double_xp_earned": 0,
                "week7_quest.course_id": course_id,  # HIGH: Store course_id with quest
                "updated_at": datetime.now(timezone.utc)
            })

            logger.info(f"Week 7 quest activated for user {user_id}")
            return True, "Week 7 Boss Quest activated! Double XP for all activities!"

        except Exception as e:
            logger.error(f"Error activating Week 7 quest for {user_id}: {e}", exc_info=True)
            return False, str(e)

    def calculate_exam_readiness(
        self,
        stats: UserStats
    ) -> int:
        """Calculate exam readiness percentage based on activities.

        Args:
            stats: User stats

        Returns:
            Exam readiness percentage (0-100)
        """
        try:
            # CRITICAL: Use correct field names from ActivityCounters model
            # CRITICAL: Ensure non-negative values
            flashcard_count = max(0, stats.activities.flashcards_reviewed)
            quiz_count = max(0, stats.activities.quizzes_passed)
            evaluation_count = max(0, stats.activities.evaluations_submitted)
            guide_count = max(0, stats.activities.guides_completed)

            # Calculate progress for each category
            flashcard_progress = min(
                (flashcard_count / EXAM_READINESS_THRESHOLDS["flashcards"]) * 100,
                100
            )
            quiz_progress = min(
                (quiz_count / EXAM_READINESS_THRESHOLDS["quizzes"]) * 100,
                100
            )
            evaluation_progress = min(
                (evaluation_count / EXAM_READINESS_THRESHOLDS["evaluations"]) * 100,
                100
            )
            guide_progress = min(
                (guide_count / EXAM_READINESS_THRESHOLDS["guides"]) * 100,
                100
            )

            # Average all categories
            total_progress = (flashcard_progress + quiz_progress + evaluation_progress + guide_progress) / 4

            return int(total_progress)

        except Exception as e:
            logger.error(f"Error calculating exam readiness: {e}", exc_info=True)
            return 0

    def calculate_quest_updates(
        self,
        user_id: str,
        xp_bonus: int,
        stats: UserStats,
        activity_type: str
    ) -> Dict[str, Any]:
        """Calculate Week 7 quest updates without applying them.

        HIGH: This method calculates updates that will be included in the atomic
        update in gamification_service to prevent race conditions.

        Args:
            user_id: User's IAP user ID
            xp_bonus: XP bonus earned (before doubling)
            stats: Current user stats (BEFORE activity increment)
            activity_type: Type of activity being logged

        Returns:
            Dictionary of Firestore update fields
        """
        if not stats.week7_quest.active:
            return {}

        try:
            # Calculate exam readiness with PREDICTED activity counts
            # We need to predict what the counts will be after the increment
            predicted_stats = self._predict_stats_after_activity(stats, activity_type)
            exam_readiness = self.calculate_exam_readiness(predicted_stats)

            # Calculate double XP earned
            double_xp_bonus = xp_bonus
            total_double_xp = stats.week7_quest.double_xp_earned + double_xp_bonus

            # Check if boss battle should be completed (100% readiness)
            boss_completed = exam_readiness >= 100

            # Build update dictionary
            updates = {
                "week7_quest.exam_readiness_percent": exam_readiness,
                "week7_quest.double_xp_earned": total_double_xp
            }

            if boss_completed and not stats.week7_quest.boss_battle_completed:
                updates["week7_quest.boss_battle_completed"] = True
                logger.info(f"Boss battle completed for user {user_id[:8]}...!")

            return updates

        except Exception as e:
            logger.error(f"Error calculating quest updates: {e}", exc_info=True)
            return {}

    def _predict_stats_after_activity(self, stats: UserStats, activity_type: str) -> UserStats:
        """Predict what stats will look like after activity increment.

        Args:
            stats: Current stats
            activity_type: Type of activity being logged

        Returns:
            Copy of stats with predicted increments
        """
        # Create a copy to avoid modifying original
        import copy
        predicted = copy.deepcopy(stats)

        # Increment the appropriate counter
        if activity_type == "quiz_completed":
            predicted.activities.quizzes_completed += 1
            # Assume it passed (conservative estimate)
            predicted.activities.quizzes_passed += 1
        elif activity_type == "flashcard_set_completed":
            predicted.activities.flashcards_reviewed += 1
        elif activity_type == "study_guide_completed":
            predicted.activities.guides_completed += 1
        elif activity_type == "evaluation_completed":
            predicted.activities.evaluations_submitted += 1

        return predicted

    def update_quest_progress(
        self,
        user_id: str,
        xp_earned: int,
        stats: UserStats
    ) -> Dict[str, Any]:
        """Update Week 7 quest progress.

        DEPRECATED: This method is deprecated in favor of calculate_quest_updates()
        which is called from gamification_service to prevent race conditions.

        Args:
            user_id: User's IAP user ID
            xp_earned: XP earned from activity (before doubling)
            stats: Current user stats

        Returns:
            Quest update info
        """
        if not self.db:
            return {"updated": False}

        try:
            # Check if quest is active
            if not stats.week7_quest.active:
                return {"updated": False}

            # Calculate exam readiness
            exam_readiness = self.calculate_exam_readiness(stats)

            # Calculate double XP earned
            double_xp_bonus = xp_earned  # The bonus amount (original XP is already added)
            total_double_xp = stats.week7_quest.double_xp_earned + double_xp_bonus

            # Check if boss battle should be completed (100% readiness)
            boss_completed = exam_readiness >= 100

            # Update quest progress
            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            updates = {
                "week7_quest.exam_readiness_percent": exam_readiness,
                "week7_quest.double_xp_earned": total_double_xp,
                "updated_at": datetime.now(timezone.utc)
            }

            if boss_completed and not stats.week7_quest.boss_battle_completed:
                updates["week7_quest.boss_battle_completed"] = True
                logger.info(f"Boss battle completed for user {user_id}!")

            doc_ref.update(updates)

            return {
                "updated": True,
                "exam_readiness": exam_readiness,
                "double_xp_earned": total_double_xp,
                "boss_completed": boss_completed,
                "double_xp_bonus": double_xp_bonus
            }

        except Exception as e:
            logger.error(f"Error updating Week 7 quest progress for {user_id}: {e}", exc_info=True)
            return {"updated": False, "error": str(e)}

    def deactivate_quest(
        self,
        user_id: str
    ) -> bool:
        """Deactivate Week 7 quest (e.g., when week ends).

        Args:
            user_id: User's IAP user ID

        Returns:
            True if successful
        """
        if not self.db:
            return False

        try:
            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            doc_ref.update({
                "week7_quest.active": False,
                "updated_at": datetime.now(timezone.utc)
            })

            logger.info(f"Week 7 quest deactivated for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deactivating Week 7 quest for {user_id}: {e}", exc_info=True)
            return False

    def get_quest_requirements(self) -> Dict[str, Any]:
        """Get quest requirements and thresholds.

        Returns:
            Quest requirements
        """
        return {
            "duration_days": WEEK7_QUEST_DURATION_DAYS,
            "double_xp_multiplier": DOUBLE_XP_MULTIPLIER,
            "requirements": {
                "flashcards": {
                    "required": EXAM_READINESS_THRESHOLDS["flashcards"],
                    "description": f"Complete {EXAM_READINESS_THRESHOLDS['flashcards']} flashcards"
                },
                "quizzes": {
                    "required": EXAM_READINESS_THRESHOLDS["quizzes"],
                    "description": f"Pass {EXAM_READINESS_THRESHOLDS['quizzes']} quizzes"
                },
                "evaluations": {
                    "required": EXAM_READINESS_THRESHOLDS["evaluations"],
                    "description": f"Complete {EXAM_READINESS_THRESHOLDS['evaluations']} evaluations"
                },
                "guides": {
                    "required": EXAM_READINESS_THRESHOLDS["guides"],
                    "description": f"Complete {EXAM_READINESS_THRESHOLDS['guides']} study guides"
                }
            },
            "boss_battle": {
                "unlock_at": 100,
                "description": "Reach 100% exam readiness to complete the Boss Battle"
            }
        }

    def get_quest_progress_details(
        self,
        stats: UserStats
    ) -> Dict[str, Any]:
        """Get detailed quest progress breakdown.

        Args:
            stats: User stats

        Returns:
            Detailed progress information
        """
        try:
            # CRITICAL: Use correct field names from ActivityCounters model
            # Calculate progress for each category
            flashcard_count = stats.activities.flashcards_reviewed
            quiz_count = stats.activities.quizzes_passed
            evaluation_count = stats.activities.evaluations_submitted
            guide_count = stats.activities.guides_completed

            return {
                "active": stats.week7_quest.active,
                "exam_readiness_percent": stats.week7_quest.exam_readiness_percent,
                "boss_battle_completed": stats.week7_quest.boss_battle_completed,
                "double_xp_earned": stats.week7_quest.double_xp_earned,
                "progress": {
                    "flashcards": {
                        "current": flashcard_count,
                        "required": EXAM_READINESS_THRESHOLDS["flashcards"],
                        "percentage": min((flashcard_count / EXAM_READINESS_THRESHOLDS["flashcards"]) * 100, 100)
                    },
                    "quizzes": {
                        "current": quiz_count,
                        "required": EXAM_READINESS_THRESHOLDS["quizzes"],
                        "percentage": min((quiz_count / EXAM_READINESS_THRESHOLDS["quizzes"]) * 100, 100)
                    },
                    "evaluations": {
                        "current": evaluation_count,
                        "required": EXAM_READINESS_THRESHOLDS["evaluations"],
                        "percentage": min((evaluation_count / EXAM_READINESS_THRESHOLDS["evaluations"]) * 100, 100)
                    },
                    "guides": {
                        "current": guide_count,
                        "required": EXAM_READINESS_THRESHOLDS["guides"],
                        "percentage": min((guide_count / EXAM_READINESS_THRESHOLDS["guides"]) * 100, 100)
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error getting quest progress details: {e}", exc_info=True)
            return {
                "active": False,
                "error": str(e)
            }


# Singleton instance
_week7_quest_service = None


def get_week7_quest_service() -> Week7QuestService:
    """Get the Week 7 quest service singleton.

    Returns:
        Week7QuestService instance
    """
    global _week7_quest_service
    if _week7_quest_service is None:
        _week7_quest_service = Week7QuestService()
    return _week7_quest_service

