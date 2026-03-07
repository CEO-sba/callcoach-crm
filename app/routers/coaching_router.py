"""
CallCoach CRM - Coaching & Analytics Router
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, CoachingInsight, Call
from app.schemas import CoachingInsightOut, DashboardStats
from app.auth import get_current_user
from app.services.analytics import get_dashboard_stats, get_agent_performance
from app.services.ai_coach import analyze_agent_growth

router = APIRouter(prefix="/api", tags=["coaching"])


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get dashboard statistics."""
    return get_dashboard_stats(db, current_user.clinic_id)


@router.get("/coaching/insights", response_model=list[CoachingInsightOut])
def list_insights(
    limit: int = 20,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get coaching insights for the current user."""
    query = db.query(CoachingInsight).filter(CoachingInsight.user_id == current_user.id)
    if unread_only:
        query = query.filter(CoachingInsight.is_read == False)
    return query.order_by(CoachingInsight.created_at.desc()).limit(limit).all()


@router.post("/coaching/insights/{insight_id}/read")
def mark_insight_read(insight_id: str, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """Mark a coaching insight as read."""
    insight = db.query(CoachingInsight).filter(
        CoachingInsight.id == insight_id,
        CoachingInsight.user_id == current_user.id
    ).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    insight.is_read = True
    db.commit()
    return {"status": "ok"}


@router.get("/coaching/performance")
def my_performance(days: int = 30, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """Get performance metrics for the current user."""
    return get_agent_performance(db, current_user.id, days)


@router.get("/coaching/performance/{user_id}")
def agent_performance(user_id: str, days: int = 30, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """Get performance metrics for a specific agent (manager/admin only)."""
    if current_user.role not in ["admin", "manager"] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    target = db.query(User).filter(User.id == user_id, User.clinic_id == current_user.clinic_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return get_agent_performance(db, user_id, days)


@router.post("/coaching/growth-plan")
async def generate_growth_plan(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an AI growth plan for an agent."""
    target_id = user_id or current_user.id
    if current_user.role not in ["admin", "manager"] and current_user.id != target_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    perf = get_agent_performance(db, target_id, 30)
    if perf["total_calls"] == 0:
        return {"message": "No calls analyzed yet. Complete some calls first to generate a growth plan."}

    growth = await analyze_agent_growth(
        agent_name=target.full_name,
        recent_scores=perf["trend"],
        total_calls=perf["total_calls"],
        avg_score_30d=perf["avg_score"],
        avg_score_7d=perf["avg_score_7d"],
        weakest_areas=perf["weakest_areas"],
        strongest_areas=perf["strongest_areas"]
    )

    # Store insights
    for area in growth.get("focus_areas", []):
        insight = CoachingInsight(
            user_id=target_id,
            clinic_id=current_user.clinic_id,
            insight_type="tip",
            category=area.get("area"),
            title=f"Focus: {area.get('area', 'General')}",
            content=area.get("specific_drill", ""),
            priority="high"
        )
        db.add(insight)

    if growth.get("encouragement"):
        insight = CoachingInsight(
            user_id=target_id,
            clinic_id=current_user.clinic_id,
            insight_type="praise",
            title="Growth Update",
            content=growth["encouragement"],
            priority="medium"
        )
        db.add(insight)

    db.commit()
    return growth


@router.get("/coaching/leaderboard")
def leaderboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get team leaderboard."""
    from sqlalchemy import func
    results = db.query(
        User.id,
        User.full_name,
        func.avg(Call.overall_score).label("avg_score"),
        func.count(Call.id).label("total_calls"),
        func.max(Call.overall_score).label("best_score")
    ).join(Call, Call.agent_id == User.id).filter(
        User.clinic_id == current_user.clinic_id,
        Call.overall_score.isnot(None)
    ).group_by(User.id).order_by(func.avg(Call.overall_score).desc()).all()

    return [
        {
            "rank": i + 1,
            "user_id": r.id,
            "name": r.full_name,
            "avg_score": round(float(r.avg_score), 1),
            "total_calls": r.total_calls,
            "best_score": round(float(r.best_score), 1)
        }
        for i, r in enumerate(results)
    ]
