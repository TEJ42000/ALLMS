"""Gamification API Routes.

Provides endpoints for gamification features including stats, activities,
sessions, and badges.
"""

import logging
import os
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
            raise HTTPException(500, detail="Failed to get user stats")

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
    user: User = Depends(get_current_user)
):
    """Get user's recent activities with pagination support.

    Args:
        limit: Maximum number of activities to return
        activity_type: Optional filter by activity type
        start_after: Optional activity ID for pagination

    Returns:
        Dict with activities list and next_cursor for pagination
    """
    try:
        service = get_gamification_service()
        activities, next_cursor = service.get_user_activities(
            user_id=user.user_id,
            limit=limit,
            activity_type=activity_type,
            start_after_id=start_after
        )

        return {
            "activities": [activity.model_dump(mode='json') for activity in activities],
            "next_cursor": next_cursor
        }

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
    """
    # TODO: Add admin role check
    # For now, any authenticated user can update (will add proper admin check in Phase 7)

    try:
        service = get_gamification_service()

        # Build updates dict from request
        updates = {}
        if request.flashcard_set_completed is not None:
            updates["flashcard_set_completed"] = request.flashcard_set_completed
        if request.study_guide_completed is not None:
            updates["study_guide_completed"] = request.study_guide_completed
        if request.quiz_easy_passed is not None:
            updates["quiz_easy_passed"] = request.quiz_easy_passed
        if request.quiz_hard_passed is not None:
            updates["quiz_hard_passed"] = request.quiz_hard_passed
        if request.evaluation_low is not None:
            updates["evaluation_low"] = request.evaluation_low
        if request.evaluation_high is not None:
            updates["evaluation_high"] = request.evaluation_high

        if not updates:
            raise HTTPException(400, detail="No updates provided")

        success = service.update_xp_config(updates, user.email)

        if not success:
            raise HTTPException(500, detail="Failed to update XP config")

        return {"status": "ok", "message": "XP configuration updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating XP config: {e}")
        raise HTTPException(500, detail=str(e)) from e

# =============================================================================
# Badge Endpoints
# =============================================================================

@router.get("/badges")
def get_user_badges(
    user: User = Depends(get_current_user)
):
    """Get all badges earned by the current user.

    Returns:
        List of user's earned badges with tier and times_earned info
    """
    try:
        service = get_gamification_service()
        badges = service.get_user_badges(user.user_id)

        return {
            "badges": [badge.model_dump(mode='json') for badge in badges]
        }

    except Exception as e:
        logger.error(f"Error getting user badges: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.get("/badges/definitions")
def get_badge_definitions(
    user: User = Depends(get_current_user)
):
    """Get all available badge definitions.

    Returns:
        List of all badge definitions with requirements and tiers
    """
    try:
        service = get_gamification_service()
        definitions = service.get_badge_definitions()

        return {
            "badge_definitions": [badge.model_dump(mode='json') for badge in definitions]
        }

    except Exception as e:
        logger.error(f"Error getting badge definitions: {e}")
        raise HTTPException(500, detail=str(e)) from e


@router.post("/badges/seed")
def seed_badges(
    user: User = Depends(get_current_user)
):
    """Seed initial badge definitions (admin only).

    Safe to call multiple times - will not overwrite existing badges.

    Returns:
        Success status

    Raises:
        HTTPException 403: If user is not an admin
    """
    # Check if user is admin
    # Admin users are defined in ADMIN_EMAILS environment variable (comma-separated)
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip() for email in admin_emails if email.strip()]

    # Explicit check: if ADMIN_EMAILS is not configured, deny all access
    if not admin_emails:
        logger.error("ADMIN_EMAILS environment variable not configured, denying badge seed request")
        raise HTTPException(
            status_code=403,
            detail="Admin configuration required. ADMIN_EMAILS environment variable must be set."
        )

    if user.email not in admin_emails:
        logger.warning(f"Non-admin user {user.email} attempted to seed badges")
        raise HTTPException(
            status_code=403,
            detail="Admin access required. This endpoint is restricted to administrators."
        )

    try:
        service = get_gamification_service()
        success = service.seed_badge_definitions()

        if not success:
            raise HTTPException(500, detail="Failed to seed badge definitions")

        logger.info(f"Badge definitions seeded successfully by admin {user.email}")
        return {"status": "ok", "message": "Badge definitions seeded successfully"}

    except HTTPException:
        raise
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
        logger.error(f"Error activating Week 7 quest: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e)) from e


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
        logger.error(f"Error getting Week 7 quest progress: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e)) from e


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
        logger.error(f"Error getting Week 7 quest requirements: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e)) from e


