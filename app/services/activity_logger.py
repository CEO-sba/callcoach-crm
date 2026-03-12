"""
SBA CRM - Comprehensive Activity Logger

Logs every interaction across the entire platform:
- Script generation (Meta Ads, Google Ads, organic content)
- Report generation (72-hour, weekly, MIS)
- Coaching interactions (call analysis, recommendations)
- AI Employee conversations (messages, handoffs)
- Nurture sequence events (enrollments, sends, conversions)
- Lead lifecycle events (creation, scoring, status changes)
- HR actions (team changes, attendance, payroll)
- User actions (logins, settings changes, exports)
- Content generation (SEO, GMB, social posts)

All logs are stored in clinic settings JSON under "activity_logs" key,
with periodic rotation to prevent unbounded growth.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Maximum logs to keep per clinic (most recent)
MAX_LOGS = 5000


def log_activity(
    db: Session,
    clinic_id: str,
    category: str,
    action: str,
    details: Optional[dict] = None,
    user_email: Optional[str] = None,
    related_id: Optional[str] = None,
    related_type: Optional[str] = None,
):
    """
    Log an activity to the clinic's activity log.

    Categories:
    - script_generation: Any AI-generated script (ad scripts, video scripts, organic scripts)
    - report: Any report generated or viewed (72-hour, weekly, MIS, performance)
    - coaching: Call coaching analysis, recommendations, skill assessments
    - ai_employee: AI Employee conversations, config changes, handoffs
    - nurture: Sequence enrollments, message sends, completions, conversions
    - lead: Lead creation, scoring, status changes, assignments
    - hr: Team member changes, attendance, leave, payroll
    - content: SEO content, GMB posts, social media content generation
    - ads: Campaign changes, keyword research, landing page generation
    - user_action: Logins, settings changes, data exports, configuration
    - system: Automated events, scheduler runs, webhook receipts
    """
    from app.models import Clinic

    try:
        clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
        if not clinic:
            logger.warning(f"Activity log skipped: clinic {clinic_id} not found")
            return

        settings = dict(clinic.settings or {})
        logs = list(settings.get("activity_logs", []))

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category,
            "action": action,
            "user": user_email or "system",
            "details": details or {},
        }

        if related_id:
            entry["related_id"] = related_id
            entry["related_type"] = related_type or "unknown"

        logs.append(entry)

        # Keep only the most recent MAX_LOGS entries
        if len(logs) > MAX_LOGS:
            logs = logs[-MAX_LOGS:]

        settings["activity_logs"] = logs
        clinic.settings = settings
        db.commit()

    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        # Never let logging failures break the main flow
        try:
            db.rollback()
        except:
            pass


def get_activity_logs(
    db: Session,
    clinic_id: str,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list:
    """Retrieve activity logs for a clinic, optionally filtered by category."""
    from app.models import Clinic

    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        return []

    settings = clinic.settings or {}
    logs = list(settings.get("activity_logs", []))

    # Reverse to get newest first
    logs.reverse()

    if category:
        logs = [l for l in logs if l.get("category") == category]

    return logs[offset:offset + limit]


def get_activity_summary(db: Session, clinic_id: str, days: int = 7) -> dict:
    """Get a summary of activity over the past N days."""
    from app.models import Clinic
    from datetime import timedelta

    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        return {}

    settings = clinic.settings or {}
    logs = list(settings.get("activity_logs", []))

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    recent = [l for l in logs if l.get("timestamp", "") >= cutoff]

    # Count by category
    category_counts = {}
    for log in recent:
        cat = log.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Count by user
    user_counts = {}
    for log in recent:
        user = log.get("user", "system")
        user_counts[user] = user_counts.get(user, 0) + 1

    return {
        "period_days": days,
        "total_activities": len(recent),
        "by_category": category_counts,
        "by_user": user_counts,
        "most_recent": recent[:10] if recent else [],
    }
