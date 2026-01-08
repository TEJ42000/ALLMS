"""Streak Maintenance Service.

Daily job to check and maintain user streaks, apply freezes, and send notifications.
Designed to run at 4:00 AM UTC via Cloud Scheduler.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# HIGH: Remove unused FieldFilter import

from app.models.gamification_models import UserStats, StreakInfo
from app.services.gcp_service import get_firestore_client
from app.services.gamification_service import GamificationService, STREAK_RESET_HOUR

logger = logging.getLogger(__name__)

# Batch size for processing users
BATCH_SIZE = 100

# Firestore collection names
USER_STATS_COLLECTION = "user_stats"
STREAK_HISTORY_COLLECTION = "streak_history"


class StreakMaintenanceService:
    """Service for daily streak maintenance."""

    def __init__(self):
        """Initialize the streak maintenance service."""
        self.db = get_firestore_client()
        self.gamification_service = GamificationService()

    def run_daily_maintenance(self) -> Dict[str, Any]:
        """Run daily streak maintenance for all users.

        Returns:
            Summary of maintenance run
        """
        if not self.db:
            logger.error("Firestore unavailable for streak maintenance")
            return {
                "status": "error",
                "message": "Firestore unavailable"
            }

        logger.info("Starting daily streak maintenance")
        start_time = datetime.now(timezone.utc)

        try:
            # Get all users with stats
            users_processed = 0
            streaks_broken = 0
            freezes_applied = 0
            notifications_sent = 0
            errors = 0

            # Process users in batches
            last_doc = None
            while True:
                # Query batch of users
                query = self.db.collection(USER_STATS_COLLECTION).limit(BATCH_SIZE)
                if last_doc:
                    query = query.start_after(last_doc)

                docs = list(query.stream())
                if not docs:
                    break

                batch_size = len(docs)

                # Process each user
                for doc in docs:
                    try:
                        user_stats = UserStats(**doc.to_dict())
                        result = self._check_user_streak(user_stats)

                        users_processed += 1
                        if result.get("streak_broken"):
                            streaks_broken += 1
                        if result.get("freeze_applied"):
                            freezes_applied += 1
                        if result.get("notification_sent"):
                            notifications_sent += 1

                    except Exception as e:
                        logger.error(f"Error processing user {doc.id}: {e}", exc_info=True)
                        errors += 1

                # Store only the last doc for pagination
                last_doc = docs[-1]

                # Clear docs list to free memory (CRITICAL: prevents memory leak)
                del docs

                # Break if we got fewer docs than batch size (last batch)
                if batch_size < BATCH_SIZE:
                    break

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            summary = {
                "status": "success",
                "users_processed": users_processed,
                "streaks_broken": streaks_broken,
                "freezes_applied": freezes_applied,
                "notifications_sent": notifications_sent,
                "errors": errors,
                "duration_seconds": duration,
                "timestamp": end_time.isoformat()
            }

            logger.info(f"Daily streak maintenance completed: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Error in daily streak maintenance: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _check_user_streak(self, user_stats: UserStats) -> Dict[str, Any]:
        """Check and update a single user's streak.

        Args:
            user_stats: User's stats

        Returns:
            Result of streak check
        """
        result = {
            "streak_broken": False,
            "freeze_applied": False,
            "notification_sent": False
        }

        try:
            current_time = datetime.now(timezone.utc)
            
            # Get last activity day
            last_activity_date = user_stats.streak.last_activity_date
            if not last_activity_date:
                # No activity yet, nothing to check
                return result

            # Calculate streak days
            current_day = self.gamification_service._get_streak_day(current_time)
            last_day = self.gamification_service._get_streak_day(last_activity_date)
            
            days_diff = (current_day - last_day).days

            # If days_diff == 0, user has activity today - no action needed
            # If days_diff == 1, user has activity yesterday - streak is current
            if days_diff <= 1:
                return result

            # User missed at least one day
            if days_diff == 2 and user_stats.streak.freezes_available > 0:
                # Missed exactly 1 day, can apply freeze
                freeze_applied = self._apply_freeze(user_stats.user_id)

                if freeze_applied:
                    result["freeze_applied"] = True
                    result["notification_sent"] = self._send_freeze_notification(user_stats)

                    # Get updated freeze count AFTER application for accurate logging
                    # CRITICAL: Prevents logging inaccuracy that confuses users
                    updated_stats = self._get_user_stats(user_stats.user_id)
                    actual_freezes_remaining = updated_stats.streak.freezes_available if updated_stats else 0

                    # Log freeze application with ACCURATE freeze count
                    self._log_streak_event(
                        user_stats.user_id,
                        "freeze_applied",
                        user_stats.streak.current_count,
                        {
                            "freezes_remaining": actual_freezes_remaining,
                            "days_missed": 1,
                            "freeze_applied_at": datetime.now(timezone.utc).isoformat()
                        }
                    )

                    logger.info(f"Freeze applied for {user_stats.user_id}. Freezes remaining: {actual_freezes_remaining}")
                else:
                    # Freeze application failed (race condition or no freezes left)
                    # Break the streak instead
                    self._break_streak(user_stats.user_id, user_stats.streak.current_count)
                    result["streak_broken"] = True
                    result["notification_sent"] = self._send_streak_broken_notification(user_stats)

            else:
                # Streak broken (missed >1 day or no freeze available)
                self._break_streak(user_stats.user_id, user_stats.streak.current_count)
                result["streak_broken"] = True
                result["notification_sent"] = self._send_streak_broken_notification(user_stats)
                
                # Log streak break
                self._log_streak_event(
                    user_stats.user_id,
                    "streak_broken",
                    user_stats.streak.current_count,
                    {
                        "days_missed": days_diff - 1,
                        "had_freeze": user_stats.streak.freezes_available > 0
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error checking streak for user {user_stats.user_id}: {e}", exc_info=True)
            return result

    def _get_user_stats(self, user_id: str) -> Optional[UserStats]:
        """Get current user stats from Firestore.

        Args:
            user_id: User's IAP user ID

        Returns:
            UserStats or None if not found
        """
        if not self.db:
            return None

        try:
            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return None

            return UserStats(**doc.to_dict())

        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}", exc_info=True)
            return None

    def _apply_freeze(self, user_id: str) -> bool:
        """Apply a streak freeze for a user.

        Uses a transaction to prevent race conditions and ensure
        freezes don't go negative.

        Args:
            user_id: User's IAP user ID

        Returns:
            True if successful, False if no freezes available or error
        """
        if not self.db:
            return False

        try:
            from google.cloud import firestore

            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)

            @firestore.transactional
            def apply_freeze_transaction(transaction):
                """Transaction to safely apply freeze."""
                snapshot = doc_ref.get(transaction=transaction)

                if not snapshot.exists:
                    return False

                data = snapshot.to_dict()
                freezes_available = data.get("streak", {}).get("freezes_available", 0)

                # Check if freeze is available
                if freezes_available <= 0:
                    logger.warning(f"No freezes available for user {user_id}")
                    return False

                # Apply freeze atomically
                transaction.update(doc_ref, {
                    "streak.freezes_available": freezes_available - 1,
                    "updated_at": datetime.now(timezone.utc)
                })

                return True

            # Execute transaction
            transaction = self.db.transaction()
            success = apply_freeze_transaction(transaction)

            if success:
                logger.info(f"Applied streak freeze for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error applying freeze for {user_id}: {e}", exc_info=True)
            return False

    def _break_streak(self, user_id: str, old_streak: int) -> bool:
        """Break a user's streak.

        Args:
            user_id: User's IAP user ID
            old_streak: Previous streak count

        Returns:
            True if successful
        """
        if not self.db:
            return False

        try:
            doc_ref = self.db.collection(USER_STATS_COLLECTION).document(user_id)
            doc_ref.update({
                "streak.current_count": 0,
                "updated_at": datetime.now(timezone.utc)
            })
            logger.info(f"Broke streak for user {user_id} (was {old_streak} days)")
            return True

        except Exception as e:
            logger.error(f"Error breaking streak for {user_id}: {e}", exc_info=True)
            return False

    def _log_streak_event(
        self,
        user_id: str,
        event_type: str,
        streak_count: int,
        details: Dict[str, Any]
    ) -> bool:
        """Log a streak event to history.

        Args:
            user_id: User's IAP user ID
            event_type: Type of event
            streak_count: Current streak count
            details: Event details

        Returns:
            True if successful
        """
        if not self.db:
            return False

        try:
            event_id = f"{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
            event_ref = self.db.collection(STREAK_HISTORY_COLLECTION).document(user_id).collection("events").document(event_id)
            
            event_ref.set({
                "event_id": event_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc),
                "event_type": event_type,
                "streak_count": streak_count,
                "details": details
            })
            
            return True

        except Exception as e:
            logger.error(f"Error logging streak event for {user_id}: {e}", exc_info=True)
            return False

    def _send_freeze_notification(self, user_stats: UserStats) -> bool:
        """Send notification that freeze was applied.

        Args:
            user_stats: User's stats

        Returns:
            True if notification sent
        """
        # TODO: Implement notification service integration
        logger.info(f"Would send freeze notification to {user_stats.user_email}")
        return True

    def _send_streak_broken_notification(self, user_stats: UserStats) -> bool:
        """Send notification that streak was broken.

        Args:
            user_stats: User's stats

        Returns:
            True if notification sent
        """
        # TODO: Implement notification service integration
        logger.info(f"Would send streak broken notification to {user_stats.user_email}")
        return True


# Singleton instance
_streak_maintenance_service = None


def get_streak_maintenance_service() -> StreakMaintenanceService:
    """Get the streak maintenance service singleton.

    Returns:
        StreakMaintenanceService instance
    """
    global _streak_maintenance_service
    if _streak_maintenance_service is None:
        _streak_maintenance_service = StreakMaintenanceService()
    return _streak_maintenance_service

