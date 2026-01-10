"""Gamification API Routes.

Provides endpoints for gamification features including stats, activities,
sessions, and badges.
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.auth_models import User
from app.models.gamification_models import (
    ActivityLogRequest,
    ActivityLogResponse,
    SessionStartResponse,
    SessionHeartbeatRequest,
    UserStatsResponse,
    UserActivity,
    XPConfigResponse,
    XPConfigUpdateRequest,
    BadgeDefinition,
    UserBadge,
)
from app.services.gamification_service import get_gamification_service
from app.services.streak_maintenance import get_streak_maintenance_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


# =============================================================================
# User Stats Endpoints
# =============================================================================

@router.get("/stats", response_model=UserStatsResponse)
def get_user_stats(
    user: User = Depends(get_current_user)
):
    """Get current user's gamification stats.

    Returns:
        User's gamification statistics including XP, level, streak, and activities
    """
    try:
        service = get_gamification_service()
        stats = service.get_or_create_user_stats(
            user_id=user.user_id,
            user_email=user.email
        )

        if not stats:
            # FIX: Distinguish system error from user error
            raise HTTPException(
                500,
                detail="System error: Unable to retrieve user statistics. Please try again later or contact support if the issue persists."
            )

        return UserStatsResponse(
            total_xp=stats.total_xp,
            current_level=stats.current_level,
            level_title=stats.level_title,
            xp_to_next_level=stats.xp_to_next_level,
            streak={
                "current_count": stats.streak.current_count,
                "longest_streak": stats.streak.longest_streak,
                "freezes_available": stats.streak.freezes_available,
            },
            activities={
                "flashcards_reviewed": stats.activities.flashcards_reviewed,
                "quizzes_completed": stats.activities.quizzes_completed,
                "quizzes_passed": stats.activities.quizzes_passed,
                "evaluations_submitted": stats.activities.evaluations_submitted,
                "guides_completed": stats.activities.guides_completed,
                "total_study_time_minutes": stats.activities.total_study_time_minutes,
            },
            week7_quest={
                "active": stats.week7_quest.active,
                "exam_readiness_percent": stats.week7_quest.exam_readiness_percent,
                "boss_battle_completed": stats.week7_quest.boss_battle_completed,
                "double_xp_earned": stats.week7_quest.double_xp_earned,
            } if stats.week7_quest.active else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(500, detail=str(e)) from e


# =============================================================================
# Activity Endpoints
# =============================================================================

@router.post("/activity", response_model=ActivityLogResponse)
def log_activity(
    request: ActivityLogRequest,
    user: User = Depends(get_current_user)
):
    """Log a user activity and award XP.

    Args:
        request: Activity log request with type and data

    Returns:
        Activity log response with XP awarded and level info
    """
    try:
        service = get_gamification_service()
        response = service.log_activity(
            user_id=user.user_id,
            user_email=user.email,
            activity_type=request.activity_type,
            activity_data=request.activity_data,
            course_id=request.course_id
        )

        if not response:
            raise HTTPException(500, detail="Failed to log activity")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging activity: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.get("/activities")
def get_activities(
    limit: int = Query(50, ge=1, le=100, description="Number of activities to return"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    start_after: Optional[str] = Query(None, description="Activity ID to start after (pagination)"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    user: User = Depends(get_current_user)
):
    """Get user's recent activities with pagination support.

    CRITICAL: Added start_date/end_date support (BLOCKS MERGE - feature was broken)

    Args:
        limit: Maximum number of activities to return
        activity_type: Optional filter by activity type
        start_after: Optional activity ID for pagination
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)

    Returns:
        Dict with activities list and next_cursor for pagination
    """
    try:
        from datetime import datetime, timezone

        # Parse date strings to datetime objects
        start_datetime = None
        end_datetime = None

        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if start_datetime.tzinfo is None:
                    start_datetime = start_datetime.replace(tzinfo=timezone.utc)
            except ValueError as e:
                raise HTTPException(400, detail=f"Invalid start_date format: {e}")

        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if end_datetime.tzinfo is None:
                    end_datetime = end_datetime.replace(tzinfo=timezone.utc)
            except ValueError as e:
                raise HTTPException(400, detail=f"Invalid end_date format: {e}")

        service = get_gamification_service()
        activities, next_cursor = service.get_user_activities(
            user_id=user.user_id,
            limit=limit,
            activity_type=activity_type,
            start_after_id=start_after,
            start_date=start_datetime,
            end_date=end_datetime
        )

        return {
            "activities": [activity.model_dump(mode='json') for activity in activities],
            "next_cursor": next_cursor
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting activities: {e}")
        raise HTTPException(500, detail=str(e)) from e


# =============================================================================
# Session Endpoints
# =============================================================================

@router.post("/session/start", response_model=SessionStartResponse)
def start_session(
    course_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Start a new tracking session.

    Args:
        course_id: Optional course ID

    Returns:
        Session start response with session ID and start time
    """
    try:
        service = get_gamification_service()
        response = service.start_session(
            user_id=user.user_id,
            course_id=course_id
        )

        if not response:
            raise HTTPException(500, detail="Failed to start session")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.post("/session/heartbeat")
def session_heartbeat(
    request: SessionHeartbeatRequest,
    user: User = Depends(get_current_user)
):
    """Update session with heartbeat.

    Args:
        request: Heartbeat request with session ID, active seconds, and current page

    Returns:
        Success status
    """
    try:
        service = get_gamification_service()
        success = service.update_session_heartbeat(
            session_id=request.session_id,
            active_seconds=request.active_seconds,
            current_page=request.current_page
        )

        if not success:
            raise HTTPException(500, detail="Failed to update session")

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.post("/session/end")
def end_session(
    session_id: str = Query(..., description="Session ID to end"),
    user: User = Depends(get_current_user)
):
    """End a tracking session.

    Args:
        session_id: Session ID to end (query parameter for sendBeacon compatibility)

    Returns:
        Success status
    """
    try:
        service = get_gamification_service()
        success = service.end_session(session_id)

        if not success:
            raise HTTPException(500, detail="Failed to end session")

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(500, detail=str(e)) from e


# =============================================================================
# XP Configuration Endpoints (Admin)
# =============================================================================

@router.get("/config/xp", response_model=XPConfigResponse)
def get_xp_config(
    user: User = Depends(get_current_user)
):
    """Get current XP configuration.

    Returns:
        Current XP values for all activity types
    """
    try:
        service = get_gamification_service()
        config = service.get_xp_config()

        # Get metadata from Firestore
        if service.db:
            doc = service.db.collection("xp_config").document("default").get()
            if doc.exists:
                data = doc.to_dict()
                return XPConfigResponse(
                    **config,
                    updated_at=data.get("updated_at"),
                    updated_by=data.get("updated_by")
                )

        # Return config with defaults
        from datetime import datetime, timezone
        return XPConfigResponse(
            **config,
            updated_at=datetime.now(timezone.utc),
            updated_by="system"
        )

    except Exception as e:
        logger.error(f"Error getting XP config: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.patch("/config/xp")
def update_xp_config(
    request: XPConfigUpdateRequest,
    user: User = Depends(get_current_user)
):
    """Update XP configuration (admin only).

    Args:
        request: XP values to update

    Returns:
        Success status

    Raises:
        HTTPException 403: If user is not an admin
        HTTPException 400: If no updates provided or invalid values
    """
    # HIGH: Add admin config validation
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip() for email in admin_emails if email.strip()]

    # Explicit check: if ADMIN_EMAILS is not configured, deny all access
    if not admin_emails:
        logger.error("ADMIN_EMAILS environment variable not configured, denying XP config update")
        raise HTTPException(
            status_code=403,
            detail="Admin configuration required. ADMIN_EMAILS environment variable must be set."
        )

    if user.email not in admin_emails:
        logger.warning(f"Non-admin user {user.email} attempted to update XP config")
        raise HTTPException(
            status_code=403,
            detail="Admin access required. This endpoint is restricted to administrators."
        )

    try:
        service = get_gamification_service()

        # Build updates dict from request with validation
        updates = {}

        # Validate all XP values are positive
        if request.flashcard_set_completed is not None:
            if request.flashcard_set_completed < 0:
                raise HTTPException(400, detail="flashcard_set_completed must be non-negative")
            updates["flashcard_set_completed"] = request.flashcard_set_completed

        if request.study_guide_completed is not None:
            if request.study_guide_completed < 0:
                raise HTTPException(400, detail="study_guide_completed must be non-negative")
            updates["study_guide_completed"] = request.study_guide_completed

        if request.quiz_easy_passed is not None:
            if request.quiz_easy_passed < 0:
                raise HTTPException(400, detail="quiz_easy_passed must be non-negative")
            updates["quiz_easy_passed"] = request.quiz_easy_passed

        if request.quiz_hard_passed is not None:
            if request.quiz_hard_passed < 0:
                raise HTTPException(400, detail="quiz_hard_passed must be non-negative")
            updates["quiz_hard_passed"] = request.quiz_hard_passed

        if request.evaluation_low is not None:
            if request.evaluation_low < 0:
                raise HTTPException(400, detail="evaluation_low must be non-negative")
            updates["evaluation_low"] = request.evaluation_low

        if request.evaluation_high is not None:
            if request.evaluation_high < 0:
                raise HTTPException(400, detail="evaluation_high must be non-negative")
            updates["evaluation_high"] = request.evaluation_high

        if not updates:
            raise HTTPException(400, detail="No updates provided")

        success = service.update_xp_config(updates, user.email)

        if not success:
            raise HTTPException(500, detail="Failed to update XP config")

        logger.info(f"XP configuration updated successfully by admin {user.email}")
        return {"status": "ok", "message": "XP configuration updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating XP config: {e}")
        raise HTTPException(500, detail=str(e)) from e

# =============================================================================
# Badge Endpoints - REMOVED (Duplicate)
# =============================================================================
# CRITICAL: Old badge endpoints removed to prevent duplicate route errors
# Phase 4 badge endpoints are defined below (lines 700+)
# The following routes were removed:
# - GET /badges (duplicate of line 706)
# - GET /badges/definitions (replaced by GET /badges at line 706)
# - POST /badges/seed (duplicate of line 838)


# =============================================================================
# Streak Endpoints
# =============================================================================

@router.get("/streak/calendar")
def get_streak_calendar(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to retrieve"),
    user: User = Depends(get_current_user)
):
    """Get calendar data for streak visualization.

    Args:
        days: Number of days to retrieve (1-90)

    Returns:
        Calendar data with activity days, freezes, and streak info
    """
    try:
        service = get_gamification_service()
        stats = service.get_or_create_user_stats(user.user_id, user.email)

        if not stats:
            raise HTTPException(500, detail="Failed to get user stats")

        # Get activities for the specified period
        from datetime import datetime, timezone, timedelta
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        activities, _ = service.get_user_activities(
            user_id=user.user_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000  # Get all activities in period
        )

        # Build calendar data
        calendar_days = []
        activity_by_day = {}

        # Group activities by day
        for activity in activities:
            day = service._get_streak_day(activity.timestamp).date().isoformat()
            if day not in activity_by_day:
                activity_by_day[day] = {
                    "date": day,
                    "has_activity": True,
                    "freeze_used": False,
                    "activity_count": 0
                }
            activity_by_day[day]["activity_count"] += 1
            if activity.metadata.get("freeze_used"):
                activity_by_day[day]["freeze_used"] = True

        # Fill in all days in range
        current_date = start_date.date()
        end = end_date.date()
        while current_date <= end:
            day_str = current_date.isoformat()
            if day_str in activity_by_day:
                calendar_days.append(activity_by_day[day_str])
            else:
                calendar_days.append({
                    "date": day_str,
                    "has_activity": False,
                    "freeze_used": False,
                    "activity_count": 0
                })
            current_date += timedelta(days=1)

        return {
            "days": calendar_days,
            "current_streak": stats.streak.current_count,
            "longest_streak": stats.streak.longest_streak,
            "freezes_available": stats.streak.freezes_available
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting streak calendar: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.get("/streak/consistency")
def get_weekly_consistency(
    user: User = Depends(get_current_user)
):
    """Get weekly consistency status.

    Returns:
        Weekly consistency progress and bonus status
    """
    try:
        service = get_gamification_service()
        stats = service.get_or_create_user_stats(user.user_id, user.email)

        if not stats:
            raise HTTPException(500, detail="Failed to get user stats")

        # Calculate week boundaries
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc)
        week_start = service._get_week_start(current_time)
        week_end = week_start + timedelta(days=7)

        # Calculate progress percentage
        completed = sum(1 for v in stats.streak.weekly_consistency.values() if v)
        progress = (completed / 4) * 100

        return {
            "week_start": week_start.date().isoformat(),
            "week_end": week_end.date().isoformat(),
            "categories": stats.streak.weekly_consistency,
            "bonus_active": getattr(stats.streak, 'bonus_active', False),
            "bonus_multiplier": getattr(stats.streak, 'bonus_multiplier', 1.0),
            "progress": progress,
            "completed_count": completed,
            "total_count": 4
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weekly consistency: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.post("/streak/maintenance")
def run_streak_maintenance(
    user: User = Depends(get_current_user)
):
    """Run daily streak maintenance (admin only).

    This endpoint is called by Cloud Scheduler at 4:00 AM UTC daily.
    Can also be manually triggered by admins for testing.

    Returns:
        Maintenance run summary

    Raises:
        HTTPException 403: If user is not an admin or ADMIN_EMAILS not configured
    """
    # HIGH: Add ADMIN_EMAILS configuration check to maintenance endpoint
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip() for email in admin_emails if email.strip()]

    # Explicit check: if ADMIN_EMAILS is not configured, deny all access
    if not admin_emails:
        logger.error("ADMIN_EMAILS environment variable not configured, denying streak maintenance request")
        raise HTTPException(
            status_code=403,
            detail="Admin configuration required. ADMIN_EMAILS environment variable must be set."
        )

    if user.email not in admin_emails:
        logger.warning(f"Non-admin user {user.email} attempted to run streak maintenance")
        raise HTTPException(
            status_code=403,
            detail="Admin access required. This endpoint is restricted to administrators."
        )

    try:
        maintenance_service = get_streak_maintenance_service()
        result = maintenance_service.run_daily_maintenance()

        # SECURITY: Don't expose internal error messages from maintenance service (CWE-209)
        if result.get("status") == "error":
            # Log detailed error server-side
            logger.error(f"Maintenance service error for {user.email}: {result.get('message', 'Unknown')}")
            # Return sanitized result without internal error message
            return {
                "status": "error",
                "message": "Maintenance job failed. Check server logs for details.",
                "timestamp": result.get("timestamp")
            }

        # Log success only after confirming no error
        logger.info(f"Streak maintenance succeeded for {user.email}: {result}")
        return result

    except Exception as e:
        # CRITICAL SECURITY: Don't expose internal error details to client
        # Log the full error server-side for debugging
        logger.error(f"Error running streak maintenance: {e}", exc_info=True)
        # Return generic error message to client
        raise HTTPException(500, detail="Failed to run streak maintenance. Please try again later.") from e


# =============================================================================
# Badge Endpoints (Phase 4)
# =============================================================================

@router.get("/badges")
def get_all_badges(
    user: User = Depends(get_current_user),
    include_inactive: bool = False
):
    """Get all badge definitions.

    MEDIUM: Added input validation and clarity
    MEDIUM: Only returns active badges by default

    Args:
        include_inactive: Include inactive badges (admin only, default: False)

    Returns:
        {
            "badges": List of badge definitions,
            "total": Total count,
            "active_count": Count of active badges,
            "inactive_count": Count of inactive badges
        }
    """
    try:
        from app.services.badge_definitions import get_all_badge_definitions

        # Get all badge definitions
        all_badges = get_all_badge_definitions()

        # MEDIUM: Filter to only active badges unless admin requests inactive
        if not include_inactive:
            badges = [b for b in all_badges if b.active]
        else:
            # Check if user is admin for inactive badges
            admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
            admin_emails = [email.strip() for email in admin_emails if email.strip()]

            if user.email not in admin_emails:
                # Non-admin users only see active badges
                badges = [b for b in all_badges if b.active]
            else:
                badges = all_badges

        # Calculate counts
        active_count = sum(1 for b in all_badges if b.active)
        inactive_count = len(all_badges) - active_count

        return {
            "badges": [badge.model_dump(mode='json') for badge in badges],
            "total": len(badges),
            "active_count": active_count,
            "inactive_count": inactive_count
        }

    except Exception as e:
        logger.error(f"Error getting badges: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.get("/badges/earned")
def get_earned_badges(
    user: User = Depends(get_current_user)
):
    """Get user's earned badges.

    Returns:
        List of badges earned by the user
    """
    try:
        from app.services.badge_service import get_badge_service

        badge_service = get_badge_service()
        earned_badges = badge_service.get_user_badges(user.user_id)

        return {
            "badges": [badge.model_dump(mode='json') for badge in earned_badges],
            "total": len(earned_badges)
        }

    except Exception as e:
        logger.error(f"Error getting earned badges: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.get("/badges/{badge_id}")
def get_badge_details(
    badge_id: str,
    user: User = Depends(get_current_user)
):
    """Get details for a specific badge.

    MEDIUM: Added input validation

    Args:
        badge_id: Badge identifier (alphanumeric and underscores only)

    Returns:
        {
            "badge": Badge definition,
            "earned": Whether user has earned this badge,
            "earned_at": When badge was earned (if earned),
            "progress": Progress toward badge (if not earned)
        }

    Raises:
        400: Invalid badge_id format
        404: Badge not found
    """
    try:
        from app.services.badge_definitions import get_all_badge_definitions
        from app.services.badge_service import get_badge_service

        # MEDIUM: Input validation - badge_id should be alphanumeric with underscores
        import re
        if not re.match(r'^[a-z0-9_]+$', badge_id):
            raise HTTPException(
                400,
                detail="Invalid badge_id format. Must be lowercase alphanumeric with underscores."
            )

        # MEDIUM: Limit badge_id length to prevent abuse
        if len(badge_id) > 50:
            raise HTTPException(400, detail="badge_id too long (max 50 characters)")

        # Find badge definition
        all_badges = get_all_badge_definitions()
        badge_def = next((b for b in all_badges if b.badge_id == badge_id), None)

        if not badge_def:
            # FIX: Improved error message with helpful hint
            raise HTTPException(
                404,
                detail=f"Badge '{badge_id}' not found. Check the badge ID and try again. Use GET /api/gamification/badges to see all available badges."
            )

        # MEDIUM: Don't show inactive badges to non-admin users
        if not badge_def.active:
            admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
            admin_emails = [email.strip() for email in admin_emails if email.strip()]

            if user.email not in admin_emails:
                # FIX: Improved error message with helpful hint
                raise HTTPException(
                    404,
                    detail=f"Badge '{badge_id}' not found. This badge may not be available yet. Use GET /api/gamification/badges to see all available badges."
                )

        # Check if user has earned it
        badge_service = get_badge_service()
        earned_badges = badge_service.get_user_badges(user.user_id)

        # MEDIUM: Find the specific earned badge to get earned_at timestamp
        earned_badge = next((b for b in earned_badges if b.badge_id == badge_id), None)
        earned = earned_badge is not None
        earned_at = earned_badge.earned_at.isoformat() if earned_badge else None

        # Get progress if not earned
        progress = None
        if not earned:
            service = get_gamification_service()
            user_stats = service.get_user_stats(user.user_id)
            if user_stats:
                all_progress = badge_service.get_badge_progress(user.user_id, user_stats)
                progress = all_progress.get(badge_id)

        return {
            "badge": badge_def.model_dump(mode='json'),
            "earned": earned,
            "earned_at": earned_at,  # MEDIUM: Added earned_at timestamp
            "progress": progress
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting badge details: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.get("/badges/progress")
def get_badge_progress(
    user: User = Depends(get_current_user)
):
    """Get user's progress toward all badges.

    Returns:
        Progress information for all unearned badges
    """
    try:
        from app.services.badge_service import get_badge_service

        service = get_gamification_service()
        user_stats = service.get_user_stats(user.user_id)

        if not user_stats:
            # FIX: User-friendly error message
            raise HTTPException(
                404,
                detail="User statistics not found. Please complete an activity first to initialize your stats."
            )

        badge_service = get_badge_service()
        progress = badge_service.get_badge_progress(user.user_id, user_stats)

        return {
            "progress": progress,
            "total_badges_in_progress": len(progress)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting badge progress: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.post("/badges/seed")
def seed_all_badges(
    user: User = Depends(get_current_user)
):
    """Seed all badge definitions (admin only).

    CRITICAL: Function renamed from seed_badges to seed_all_badges to avoid duplicate

    Returns:
        Number of badges seeded
    """
    # Admin check
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip() for email in admin_emails if email.strip()]

    if not admin_emails:
        logger.error("ADMIN_EMAILS not configured")
        raise HTTPException(403, detail="Admin configuration required")

    if user.email not in admin_emails:
        logger.warning(f"Non-admin {user.email} attempted to seed badges")
        raise HTTPException(403, detail="Admin access required")

    try:
        from app.services.badge_definitions import seed_badge_definitions
        from app.services.gcp_service import get_firestore_client

        db = get_firestore_client()
        count = seed_badge_definitions(db)

        logger.info(f"Badges seeded by {user.email}: {count} badges")
        return {
            "status": "ok",
            "badges_seeded": count,
            "message": f"Successfully seeded {count} badge definitions"
        }

    except Exception as e:
        logger.error(f"Error seeding badges: {e}")
        raise HTTPException(500, detail=str(e)) from e


# =============================================================================
# Week 7 Quest Endpoints
# =============================================================================

@router.post("/quest/week7/activate")
def activate_week7_quest(
    current_week: int = Query(..., ge=1, le=13, description="Current week number"),
    course_id: str = Query(..., description="Course ID"),
    user: User = Depends(get_current_user)
):
    """Activate Week 7 Boss Quest for current user.

    HIGH: Added API endpoint to activate quest

    Args:
        current_week: Current week number (1-13)
        course_id: Course ID
        user: Current authenticated user

    Returns:
        Activation status and message

    Raises:
        HTTPException: If activation fails
    """
    try:
        from app.services.week7_quest_service import get_week7_quest_service

        quest_service = get_week7_quest_service()
        activated, message = quest_service.check_and_activate_quest(
            user_id=user.user_id,
            course_id=course_id,
            current_week=current_week
        )

        if not activated and message:
            raise HTTPException(400, detail=message)

        logger.info(f"Week 7 quest activation attempt for user {user.user_id[:8]}... - Result: {activated}")
        return {"status": "activated" if activated else "not_activated", "message": message}

    except HTTPException:
        raise
    except Exception as e:
        # CRITICAL: Don't expose internal error details to client
        logger.error(f"Error activating Week 7 quest for user {user.user_id[:8]}...: {e}", exc_info=True)
        raise HTTPException(500, detail="Failed to activate quest. Please try again later.") from e


@router.get("/quest/week7/progress")
def get_week7_quest_progress(
    user: User = Depends(get_current_user)
):
    """Get detailed Week 7 quest progress for current user.

    HIGH: Added API endpoint to get quest progress

    Args:
        user: Current authenticated user

    Returns:
        Quest progress including exam readiness, double XP earned, etc.

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        from app.services.gamification_service import get_gamification_service

        service = get_gamification_service()
        stats = service.get_or_create_user_stats(
            user_id=user.user_id,
            user_email=user.email,
            course_id=None  # Will use existing course_id from stats
        )

        if not stats:
            raise HTTPException(404, detail="User stats not found")

        return {
            "active": stats.week7_quest.active,
            "course_id": stats.week7_quest.course_id,
            "exam_readiness_percent": stats.week7_quest.exam_readiness_percent,
            "boss_battle_completed": stats.week7_quest.boss_battle_completed,
            "double_xp_earned": stats.week7_quest.double_xp_earned
        }

    except HTTPException:
        raise
    except Exception as e:
        # CRITICAL: Don't expose internal error details to client
        logger.error(f"Error getting Week 7 quest progress: {e}", exc_info=True)
        raise HTTPException(500, detail="Failed to retrieve quest progress. Please try again later.") from e


@router.get("/quest/week7/requirements")
def get_week7_quest_requirements():
    """Get Week 7 quest requirements and thresholds.

    HIGH: Added API endpoint to get quest requirements

    Returns:
        Quest requirements including exam readiness thresholds
    """
    try:
        from app.services.week7_quest_service import get_week7_quest_service

        quest_service = get_week7_quest_service()
        return quest_service.get_quest_requirements()

    except Exception as e:
        # CRITICAL: Don't expose internal error details to client
        logger.error(f"Error getting Week 7 quest requirements: {e}", exc_info=True)
        raise HTTPException(500, detail="Failed to retrieve quest requirements. Please try again later.") from e
