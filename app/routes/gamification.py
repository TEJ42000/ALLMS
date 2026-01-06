"""Gamification API Routes.

Provides endpoints for gamification features including stats, activities,
sessions, and badges.
"""

import logging
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
)
from app.services.gamification_service import get_gamification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


# =============================================================================
# User Stats Endpoints
# =============================================================================

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user: User = Depends(get_current_user)
):
    """Get current user's gamification stats.
    
    Returns:
        User's gamification statistics including XP, level, streak, and activities
    """
    try:
        service = get_gamification_service()
        stats = await service.get_or_create_user_stats(
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
async def log_activity(
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
        response = await service.log_activity(
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


@router.get("/activities", response_model=list[UserActivity])
async def get_activities(
    limit: int = Query(50, ge=1, le=100, description="Number of activities to return"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    user: User = Depends(get_current_user)
):
    """Get user's recent activities.
    
    Args:
        limit: Maximum number of activities to return
        activity_type: Optional filter by activity type
        
    Returns:
        List of user activities
    """
    try:
        service = get_gamification_service()
        activities = await service.get_user_activities(
            user_id=user.user_id,
            limit=limit,
            activity_type=activity_type
        )
        
        return activities
        
    except Exception as e:
        logger.error(f"Error getting activities: {e}")
        raise HTTPException(500, detail=str(e)) from e


# =============================================================================
# Session Endpoints
# =============================================================================

@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(
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
        response = await service.start_session(
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
async def session_heartbeat(
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
        success = await service.update_session_heartbeat(
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
async def end_session(
    session_id: str,
    user: User = Depends(get_current_user)
):
    """End a tracking session.

    Args:
        session_id: Session ID to end

    Returns:
        Success status
    """
    try:
        service = get_gamification_service()
        success = await service.end_session(session_id)

        if not success:
            raise HTTPException(500, detail="Failed to end session")

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(500, detail=str(e)) from e

