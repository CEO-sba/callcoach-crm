"""
CallCoach CRM - Admin Service
Platform-level admin operations for managing clinics and aggregating analytics.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Clinic, User, Call, CallScore, PipelineDeal


def get_platform_stats(db: Session) -> dict:
    """Get platform-wide statistics for the admin dashboard."""
    total_clinics = db.query(func.count(Clinic.id)).scalar() or 0
    active_clinics = db.query(func.count(Clinic.id)).filter(Clinic.is_active == True).scalar() or 0
    total_users = db.query(func.count(User.id)).filter(User.is_super_admin == False).scalar() or 0
    total_calls = db.query(func.count(Call.id)).scalar() or 0

    avg_score = db.query(func.avg(Call.overall_score)).filter(
        Call.overall_score.isnot(None)
    ).scalar()

    total_pipeline = db.query(func.sum(PipelineDeal.deal_value)).filter(
        PipelineDeal.status == "open"
    ).scalar() or 0

    total_won = db.query(func.sum(PipelineDeal.deal_value)).filter(
        PipelineDeal.status == "won"
    ).scalar() or 0

    return {
        "total_clinics": total_clinics,
        "active_clinics": active_clinics,
        "total_users": total_users,
        "total_calls": total_calls,
        "platform_avg_score": round(float(avg_score), 1) if avg_score else None,
        "total_pipeline_value": float(total_pipeline),
        "total_won_value": float(total_won),
    }


def get_platform_averages(db: Session) -> dict:
    """Get platform-wide average scores across all dimensions. Anonymized."""
    result = db.query(
        func.avg(CallScore.overall_score).label("overall"),
        func.avg(CallScore.greeting_score).label("greeting"),
        func.avg(CallScore.discovery_score).label("discovery"),
        func.avg(CallScore.presentation_score).label("presentation"),
        func.avg(CallScore.objection_handling_score).label("objection_handling"),
        func.avg(CallScore.closing_score).label("closing"),
        func.avg(CallScore.rapport_score).label("rapport"),
        func.avg(CallScore.active_listening_score).label("active_listening"),
        func.avg(CallScore.urgency_creation_score).label("urgency_creation"),
        func.avg(CallScore.follow_up_setup_score).label("follow_up_setup"),
        func.count(CallScore.id).label("total_calls_analyzed"),
    ).first()

    if not result or result.total_calls_analyzed == 0:
        return {
            "overall": None, "greeting": None, "discovery": None,
            "presentation": None, "objection_handling": None, "closing": None,
            "rapport": None, "active_listening": None, "urgency_creation": None,
            "follow_up_setup": None, "total_calls_analyzed": 0,
        }

    def r(val):
        return round(float(val), 1) if val else None

    return {
        "overall": r(result.overall),
        "greeting": r(result.greeting),
        "discovery": r(result.discovery),
        "presentation": r(result.presentation),
        "objection_handling": r(result.objection_handling),
        "closing": r(result.closing),
        "rapport": r(result.rapport),
        "active_listening": r(result.active_listening),
        "urgency_creation": r(result.urgency_creation),
        "follow_up_setup": r(result.follow_up_setup),
        "total_calls_analyzed": result.total_calls_analyzed,
    }


def get_clinic_detail_stats(db: Session, clinic_id: str) -> dict:
    """Get detailed stats for a single clinic."""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        return None

    staff_count = db.query(func.count(User.id)).filter(
        User.clinic_id == clinic_id, User.is_super_admin == False
    ).scalar() or 0

    total_calls = db.query(func.count(Call.id)).filter(
        Call.clinic_id == clinic_id
    ).scalar() or 0

    avg_score = db.query(func.avg(Call.overall_score)).filter(
        Call.clinic_id == clinic_id,
        Call.overall_score.isnot(None)
    ).scalar()

    total_deals = db.query(func.count(PipelineDeal.id)).filter(
        PipelineDeal.clinic_id == clinic_id
    ).scalar() or 0

    pipeline_value = db.query(func.sum(PipelineDeal.deal_value)).filter(
        PipelineDeal.clinic_id == clinic_id,
        PipelineDeal.status == "open"
    ).scalar() or 0

    won_value = db.query(func.sum(PipelineDeal.deal_value)).filter(
        PipelineDeal.clinic_id == clinic_id,
        PipelineDeal.status == "won"
    ).scalar() or 0

    # Staff list
    staff = db.query(User).filter(
        User.clinic_id == clinic_id, User.is_super_admin == False
    ).all()

    staff_list = []
    for s in staff:
        agent_calls = db.query(func.count(Call.id)).filter(Call.agent_id == s.id).scalar() or 0
        agent_avg = db.query(func.avg(Call.overall_score)).filter(
            Call.agent_id == s.id, Call.overall_score.isnot(None)
        ).scalar()
        staff_list.append({
            "id": s.id,
            "email": s.email,
            "full_name": s.full_name,
            "role": s.role,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "total_calls": agent_calls,
            "avg_score": round(float(agent_avg), 1) if agent_avg else None,
        })

    return {
        "id": clinic.id,
        "name": clinic.name,
        "phone": clinic.phone,
        "email": clinic.email,
        "city": clinic.city,
        "specialty": clinic.specialty,
        "is_active": clinic.is_active,
        "leaderboard_visible": clinic.leaderboard_visible,
        "created_at": clinic.created_at.isoformat() if clinic.created_at else None,
        "staff_count": staff_count,
        "total_calls": total_calls,
        "avg_score": round(float(avg_score), 1) if avg_score else None,
        "total_deals": total_deals,
        "pipeline_value": float(pipeline_value),
        "won_value": float(won_value),
        "staff": staff_list,
    }


def list_all_clinics(db: Session, active_only: bool = False) -> list:
    """List all clinics with basic stats."""
    query = db.query(Clinic)
    if active_only:
        query = query.filter(Clinic.is_active == True)
    clinics = query.order_by(Clinic.created_at.desc()).all()

    result = []
    for clinic in clinics:
        staff_count = db.query(func.count(User.id)).filter(
            User.clinic_id == clinic.id, User.is_super_admin == False
        ).scalar() or 0

        total_calls = db.query(func.count(Call.id)).filter(
            Call.clinic_id == clinic.id
        ).scalar() or 0

        avg_score = db.query(func.avg(Call.overall_score)).filter(
            Call.clinic_id == clinic.id,
            Call.overall_score.isnot(None)
        ).scalar()

        result.append({
            "id": clinic.id,
            "name": clinic.name,
            "phone": clinic.phone,
            "email": clinic.email,
            "city": clinic.city,
            "specialty": clinic.specialty,
            "is_active": clinic.is_active,
            "leaderboard_visible": clinic.leaderboard_visible,
            "created_at": clinic.created_at.isoformat() if clinic.created_at else None,
            "staff_count": staff_count,
            "total_calls": total_calls,
            "avg_score": round(float(avg_score), 1) if avg_score else None,
        })

    return result
