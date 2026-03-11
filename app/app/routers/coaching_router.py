"""
CallCoach CRM - Coaching & Analytics Router
"""
from typing import Optional, List
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Clinic, CoachingInsight, Call
from app.schemas import CoachingInsightOut, DashboardStats
from app.auth import get_current_user
from app.services.analytics import get_dashboard_stats, get_agent_performance
from app.services.ai_coach import analyze_agent_growth
from app.services.comparison_service import (
    compare_agents, get_dimension_leaderboard, get_platform_benchmarks
)
from app.services.activity_logger import log_activity

router = APIRouter(prefix="/api", tags=["coaching"])


# ---------------------------------------------------------------------------
# Generation History
# ---------------------------------------------------------------------------

@router.get("/coaching/history")
def get_coaching_generation_history(
    action_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get coaching generation history."""
    from app.services.activity_logger import get_activity_logs
    logs = get_activity_logs(db=db, clinic_id=current_user.clinic_id, category="coaching", limit=limit)
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    if action_filter:
        logs = [l for l in logs if action_filter in l.get("action", "")]
    return {"history": logs[:limit], "count": len(logs[:limit])}


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get dashboard statistics."""
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Super admins should use the admin dashboard")
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
    data: dict = Body(default={}),
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
        strongest_areas=perf["strongest_areas"],
        regenerate_changes=data.get("regenerate_changes", "")
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
    log_activity(db, current_user.clinic_id, "coaching", "growth_plan_generated",
                 {"target_user": target.full_name, "total_calls": perf["total_calls"], "avg_score": perf["avg_score"]},
                 current_user.email)
    return growth


@router.get("/coaching/leaderboard")
def leaderboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get team leaderboard. Respects clinic leaderboard_visible setting for agents."""
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Super admins should use admin portal")

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Agents can only see leaderboard if the clinic has it enabled
    if current_user.role not in ["admin", "manager"] and not clinic.leaderboard_visible:
        return {"visible": False, "message": "Leaderboard is currently hidden by your clinic admin.", "leaderboard": []}

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

    return {
        "visible": True,
        "leaderboard_enabled": clinic.leaderboard_visible,
        "leaderboard": [
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
    }


@router.get("/coaching/leaderboard/dimensions")
def leaderboard_dimensions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed leaderboard with per-dimension scores for all team members."""
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Super admins should use admin portal")

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Agents can only see if enabled
    if current_user.role not in ["admin", "manager"] and not clinic.leaderboard_visible:
        return {"visible": False, "message": "Leaderboard is currently hidden.", "leaderboard": []}

    return {
        "visible": True,
        "leaderboard": get_dimension_leaderboard(db, current_user.clinic_id)
    }


@router.get("/coaching/compare")
def compare_team_members(
    user_ids: str = Query(..., description="Comma-separated user IDs to compare"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare agents side-by-side across all 9 dimensions. Same clinic only."""
    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Super admins should use admin portal")

    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only admin or manager can compare agents")

    ids = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 user IDs to compare")
    if len(ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 agents can be compared at once")

    result = compare_agents(db, ids, current_user.clinic_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return {"comparison": result}


@router.get("/coaching/platform-benchmark")
def platform_benchmark(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get platform-wide averages for benchmarking (admin/manager only). No clinic-specific data exposed."""
    if current_user.role not in ["admin", "manager"] and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only admin or manager can view platform benchmarks")

    return get_platform_benchmarks(db)


@router.patch("/coaching/leaderboard/visibility")
def toggle_leaderboard_visibility(
    visible: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle leaderboard visibility for the clinic (admin only)."""
    if current_user.role != "admin" and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only clinic admin can toggle leaderboard visibility")

    if not current_user.clinic_id:
        raise HTTPException(status_code=400, detail="Super admins must use /api/admin/clinics/{id} to toggle")

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    clinic.leaderboard_visible = visible
    db.commit()
    return {
        "status": "ok",
        "leaderboard_visible": clinic.leaderboard_visible,
    }
