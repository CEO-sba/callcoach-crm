"""
CallCoach CRM - Comparison Service
Agent comparison and dimension-level leaderboard analytics.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import User, Call, CallScore


DIMENSIONS = [
    "greeting_score", "discovery_score", "presentation_score",
    "objection_handling_score", "closing_score", "rapport_score",
    "active_listening_score", "urgency_creation_score", "follow_up_setup_score"
]

DIMENSION_LABELS = {
    "greeting_score": "Greeting",
    "discovery_score": "Discovery",
    "presentation_score": "Presentation",
    "objection_handling_score": "Objection Handling",
    "closing_score": "Closing",
    "rapport_score": "Rapport",
    "active_listening_score": "Active Listening",
    "urgency_creation_score": "Urgency Creation",
    "follow_up_setup_score": "Follow-up Setup",
}


def compare_agents(db: Session, agent_ids: list, clinic_id: str) -> list:
    """Compare multiple agents across all 9 dimensions. All must be in the same clinic."""
    # Validate all agents belong to the same clinic
    agents = db.query(User).filter(
        User.id.in_(agent_ids),
        User.clinic_id == clinic_id,
        User.is_super_admin == False
    ).all()

    if len(agents) != len(agent_ids):
        return {"error": "One or more agents not found in this clinic"}

    results = []
    for agent in agents:
        # Overall stats from Call table
        call_stats = db.query(
            func.count(Call.id).label("total_calls"),
            func.avg(Call.overall_score).label("avg_score"),
            func.max(Call.overall_score).label("best_score"),
            func.min(Call.overall_score).label("worst_score"),
        ).filter(
            Call.agent_id == agent.id,
            Call.overall_score.isnot(None)
        ).first()

        # Dimension averages from CallScore via Call
        dim_query = db.query(
            *[func.avg(getattr(CallScore, dim)).label(dim) for dim in DIMENSIONS]
        ).join(Call, Call.id == CallScore.call_id).filter(
            Call.agent_id == agent.id
        ).first()

        dimensions = {}
        if dim_query:
            for dim in DIMENSIONS:
                val = getattr(dim_query, dim)
                dimensions[DIMENSION_LABELS[dim]] = round(float(val), 1) if val else 0.0

        # Recent trend (last 10 calls)
        recent_calls = db.query(
            Call.overall_score, Call.call_date
        ).filter(
            Call.agent_id == agent.id,
            Call.overall_score.isnot(None)
        ).order_by(Call.call_date.desc()).limit(10).all()

        trend = [
            {"score": round(float(c.overall_score), 1), "date": c.call_date.isoformat()}
            for c in reversed(recent_calls)
        ]

        results.append({
            "user_id": agent.id,
            "name": agent.full_name,
            "role": agent.role,
            "total_calls": call_stats.total_calls if call_stats else 0,
            "avg_score": round(float(call_stats.avg_score), 1) if call_stats and call_stats.avg_score else 0,
            "best_score": round(float(call_stats.best_score), 1) if call_stats and call_stats.best_score else 0,
            "dimensions": dimensions,
            "trend": trend,
        })

    return results


def get_dimension_leaderboard(db: Session, clinic_id: str) -> list:
    """Full leaderboard with per-dimension scores for all team members in a clinic."""
    agents = db.query(User).filter(
        User.clinic_id == clinic_id,
        User.is_super_admin == False,
        User.is_active == True
    ).all()

    results = []
    for agent in agents:
        call_stats = db.query(
            func.count(Call.id).label("total_calls"),
            func.avg(Call.overall_score).label("avg_score"),
            func.max(Call.overall_score).label("best_score"),
        ).filter(
            Call.agent_id == agent.id,
            Call.overall_score.isnot(None)
        ).first()

        if not call_stats or call_stats.total_calls == 0:
            continue

        # Dimension averages
        dim_query = db.query(
            *[func.avg(getattr(CallScore, dim)).label(dim) for dim in DIMENSIONS]
        ).join(Call, Call.id == CallScore.call_id).filter(
            Call.agent_id == agent.id
        ).first()

        dimensions = {}
        if dim_query:
            for dim in DIMENSIONS:
                val = getattr(dim_query, dim)
                dimensions[DIMENSION_LABELS[dim]] = round(float(val), 1) if val else 0.0

        results.append({
            "user_id": agent.id,
            "name": agent.full_name,
            "role": agent.role,
            "total_calls": call_stats.total_calls,
            "avg_score": round(float(call_stats.avg_score), 1) if call_stats.avg_score else 0,
            "best_score": round(float(call_stats.best_score), 1) if call_stats.best_score else 0,
            "dimensions": dimensions,
        })

    # Sort by avg_score descending
    results.sort(key=lambda x: x["avg_score"], reverse=True)

    # Add rank
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results


def get_platform_benchmarks(db: Session) -> dict:
    """Get platform-wide averages per dimension for benchmarking. Anonymized."""
    result = db.query(
        func.avg(CallScore.overall_score).label("overall"),
        *[func.avg(getattr(CallScore, dim)).label(dim) for dim in DIMENSIONS],
        func.count(CallScore.id).label("total"),
    ).first()

    if not result or result.total == 0:
        return {
            "overall": None,
            "dimensions": {DIMENSION_LABELS[d]: None for d in DIMENSIONS},
            "total_calls_analyzed": 0,
        }

    dimensions = {}
    for dim in DIMENSIONS:
        val = getattr(result, dim)
        dimensions[DIMENSION_LABELS[dim]] = round(float(val), 1) if val else None

    return {
        "overall": round(float(result.overall), 1) if result.overall else None,
        "dimensions": dimensions,
        "total_calls_analyzed": result.total,
    }
