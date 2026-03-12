"""
CallCoach CRM - Activity Log Router
Comprehensive activity logging and retrieval for all platform interactions.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import get_activity_logs, get_activity_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/activity", tags=["activity-logs"])


@router.get("/logs")
def list_activity_logs(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get activity logs for the current clinic."""
    logs = get_activity_logs(
        db=db,
        clinic_id=current_user.clinic_id,
        category=category,
        limit=limit,
        offset=offset,
    )
    return {"logs": logs, "count": len(logs), "offset": offset, "limit": limit}


@router.get("/summary")
def activity_summary(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get activity summary for the current clinic."""
    summary = get_activity_summary(
        db=db,
        clinic_id=current_user.clinic_id,
        days=days,
    )
    return summary


@router.get("/categories")
def list_categories(
    current_user: User = Depends(get_current_user),
):
    """List all available activity log categories."""
    return {
        "categories": [
            {"id": "script_generation", "label": "Script Generation", "description": "AI-generated scripts for ads, video, organic content"},
            {"id": "report", "label": "Reports", "description": "72-hour reports, weekly reviews, MIS reports, performance summaries"},
            {"id": "coaching", "label": "Call Coaching", "description": "Call analysis, coaching recommendations, skill assessments"},
            {"id": "ai_employee", "label": "AI Employee", "description": "WhatsApp conversations, config changes, handoffs"},
            {"id": "nurture", "label": "Nurture Sequences", "description": "Enrollments, message sends, completions, conversions"},
            {"id": "lead", "label": "Lead Management", "description": "Lead creation, scoring changes, status updates, assignments"},
            {"id": "hr", "label": "HR & Team", "description": "Team member changes, attendance, leave, payroll records"},
            {"id": "content", "label": "Content & SEO", "description": "SEO content, GMB posts, social media content generation"},
            {"id": "ads", "label": "Ads & Campaigns", "description": "Campaign changes, keyword research, ad copy, landing pages"},
            {"id": "user_action", "label": "User Actions", "description": "Logins, settings changes, exports, configuration updates"},
            {"id": "system", "label": "System Events", "description": "Automated events, scheduler runs, webhook receipts"},
        ]
    }
