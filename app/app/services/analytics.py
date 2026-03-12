"""
CallCoach CRM - Analytics Service
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import Call, CallScore, PipelineDeal, User, CoachingInsight


def get_dashboard_stats(db: Session, clinic_id: str) -> dict:
    """Compute dashboard statistics for a clinic."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Call stats
    total_calls = db.query(Call).filter(Call.clinic_id == clinic_id).count()

    calls_today = db.query(Call).filter(
        Call.clinic_id == clinic_id,
        Call.call_date >= today_start
    ).count()

    calls_this_week = db.query(Call).filter(
        Call.clinic_id == clinic_id,
        Call.call_date >= week_start
    ).count()

    # Average call score
    avg_score_result = db.query(func.avg(Call.overall_score)).filter(
        Call.clinic_id == clinic_id,
        Call.overall_score.isnot(None)
    ).scalar()
    avg_call_score = round(float(avg_score_result or 0), 1)

    # Deal stats
    deals = db.query(PipelineDeal).filter(PipelineDeal.clinic_id == clinic_id)
    total_deals = deals.count()
    open_deals = deals.filter(PipelineDeal.status == "open").count()
    won_deals = deals.filter(PipelineDeal.status == "won").count()
    lost_deals = deals.filter(PipelineDeal.status == "lost").count()

    pipeline_value = db.query(func.sum(PipelineDeal.deal_value)).filter(
        PipelineDeal.clinic_id == clinic_id,
        PipelineDeal.status == "open"
    ).scalar() or 0

    won_value = db.query(func.sum(PipelineDeal.deal_value)).filter(
        PipelineDeal.clinic_id == clinic_id,
        PipelineDeal.status == "won"
    ).scalar() or 0

    closed_deals = won_deals + lost_deals
    conversion_rate = round((won_deals / closed_deals * 100) if closed_deals > 0 else 0, 1)

    avg_deal_value = round(float(won_value / won_deals) if won_deals > 0 else 0, 0)

    # Top agent scores
    top_agents = db.query(
        User.full_name,
        func.avg(Call.overall_score).label("avg_score"),
        func.count(Call.id).label("call_count")
    ).join(Call, Call.agent_id == User.id).filter(
        Call.clinic_id == clinic_id,
        Call.overall_score.isnot(None)
    ).group_by(User.id).order_by(func.avg(Call.overall_score).desc()).limit(5).all()

    top_agent_scores = [
        {"name": a.full_name, "avg_score": round(float(a.avg_score), 1), "calls": a.call_count}
        for a in top_agents
    ]

    # Score trend (last 7 days)
    score_trend = []
    for i in range(6, -1, -1):
        day = today_start - timedelta(days=i)
        day_end = day + timedelta(days=1)
        day_avg = db.query(func.avg(Call.overall_score)).filter(
            Call.clinic_id == clinic_id,
            Call.call_date >= day,
            Call.call_date < day_end,
            Call.overall_score.isnot(None)
        ).scalar()
        score_trend.append({
            "date": day.strftime("%Y-%m-%d"),
            "avg_score": round(float(day_avg or 0), 1)
        })

    # Calls by type
    call_types = db.query(
        Call.call_type, func.count(Call.id)
    ).filter(Call.clinic_id == clinic_id).group_by(Call.call_type).all()
    calls_by_type = {ct: count for ct, count in call_types}

    # Deals by stage
    stage_counts = db.query(
        PipelineDeal.stage, func.count(PipelineDeal.id)
    ).filter(
        PipelineDeal.clinic_id == clinic_id,
        PipelineDeal.status == "open"
    ).group_by(PipelineDeal.stage).all()
    deals_by_stage = {stage: count for stage, count in stage_counts}

    # Calls per day (last 14 days)
    calls_per_day = []
    for i in range(13, -1, -1):
        day = today_start - timedelta(days=i)
        day_end = day + timedelta(days=1)
        day_count = db.query(Call).filter(
            Call.clinic_id == clinic_id,
            Call.call_date >= day,
            Call.call_date < day_end,
        ).count()
        calls_per_day.append({
            "date": day.strftime("%Y-%m-%d"),
            "day": day.strftime("%a"),
            "count": day_count
        })

    # Deals won per week (last 8 weeks)
    deals_per_week = []
    for i in range(7, -1, -1):
        wk_start = today_start - timedelta(weeks=i, days=today_start.weekday())
        wk_end = wk_start + timedelta(days=7)
        wk_won = db.query(func.count(PipelineDeal.id)).filter(
            PipelineDeal.clinic_id == clinic_id,
            PipelineDeal.status == "won",
            PipelineDeal.updated_at >= wk_start,
            PipelineDeal.updated_at < wk_end
        ).scalar() or 0
        wk_value = db.query(func.sum(PipelineDeal.deal_value)).filter(
            PipelineDeal.clinic_id == clinic_id,
            PipelineDeal.status == "won",
            PipelineDeal.updated_at >= wk_start,
            PipelineDeal.updated_at < wk_end
        ).scalar() or 0
        deals_per_week.append({
            "week": wk_start.strftime("%d %b"),
            "won": wk_won,
            "value": float(wk_value)
        })

    # Recent calls (last 5 for activity feed)
    recent_calls = db.query(Call).filter(
        Call.clinic_id == clinic_id
    ).order_by(Call.call_date.desc()).limit(5).all()
    recent_activity = []
    for c in recent_calls:
        agent = db.query(User).filter(User.id == c.agent_id).first() if c.agent_id else None
        recent_activity.append({
            "id": c.id,
            "type": "call",
            "agent": agent.full_name if agent else "Unknown",
            "contact": c.contact_name or "Unknown",
            "score": c.overall_score,
            "sentiment": c.sentiment,
            "intent": c.intent,
            "date": c.call_date.isoformat() if c.call_date else None,
        })

    # Recent deals (last 5)
    recent_deals = db.query(PipelineDeal).filter(
        PipelineDeal.clinic_id == clinic_id
    ).order_by(PipelineDeal.updated_at.desc()).limit(5).all()
    for d in recent_deals:
        recent_activity.append({
            "id": d.id,
            "type": "deal",
            "contact": d.contact_name or "Unknown",
            "stage": d.stage,
            "status": d.status,
            "value": float(d.deal_value or 0),
            "treatment": d.treatment_interest,
            "date": d.updated_at.isoformat() if d.updated_at else None,
        })

    # Sort activity by date
    recent_activity.sort(key=lambda x: x.get("date") or "", reverse=True)
    recent_activity = recent_activity[:8]

    # Sentiment distribution
    sentiments = db.query(
        Call.sentiment, func.count(Call.id)
    ).filter(
        Call.clinic_id == clinic_id,
        Call.sentiment.isnot(None)
    ).group_by(Call.sentiment).all()
    sentiment_dist = {s: count for s, count in sentiments if s}

    # Intent distribution
    intents = db.query(
        Call.intent, func.count(Call.id)
    ).filter(
        Call.clinic_id == clinic_id,
        Call.intent.isnot(None)
    ).group_by(Call.intent).all()
    intent_dist = {i: count for i, count in intents if i}

    # Team size
    team_count = db.query(User).filter(
        User.clinic_id == clinic_id,
        User.is_active == True
    ).count()

    return {
        "total_calls": total_calls,
        "calls_today": calls_today,
        "calls_this_week": calls_this_week,
        "avg_call_score": avg_call_score,
        "total_deals": total_deals,
        "open_deals": open_deals,
        "won_deals": won_deals,
        "lost_deals": lost_deals,
        "pipeline_value": float(pipeline_value),
        "won_value": float(won_value),
        "conversion_rate": conversion_rate,
        "avg_deal_value": avg_deal_value,
        "top_agent_scores": top_agent_scores,
        "score_trend": score_trend,
        "calls_by_type": calls_by_type,
        "deals_by_stage": deals_by_stage,
        "calls_per_day": calls_per_day,
        "deals_per_week": deals_per_week,
        "recent_activity": recent_activity,
        "sentiment_distribution": sentiment_dist,
        "intent_distribution": intent_dist,
        "team_count": team_count,
    }


def get_agent_performance(db: Session, user_id: str, days: int = 30) -> dict:
    """Get detailed performance metrics for a specific agent."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    calls = db.query(Call).filter(
        Call.agent_id == user_id,
        Call.call_date >= cutoff,
        Call.overall_score.isnot(None)
    ).order_by(Call.call_date.desc()).all()

    if not calls:
        return {"total_calls": 0, "avg_score": 0, "scores_by_dimension": {}, "trend": []}

    # Aggregate scores
    dimensions = [
        "greeting_score", "discovery_score", "presentation_score",
        "objection_handling_score", "closing_score", "rapport_score",
        "active_listening_score", "urgency_creation_score", "follow_up_setup_score"
    ]

    scores_by_dim = {}
    for dim in dimensions:
        scores = []
        for call in calls:
            if call.scores:
                for score in call.scores:
                    val = getattr(score, dim, None)
                    if val is not None:
                        scores.append(val)
            scores_by_dim[dim] = round(sum(scores) / len(scores), 1) if scores else 0

    # Find weakest and strongest
    sorted_dims = sorted(scores_by_dim.items(), key=lambda x: x[1])
    weakest = [{"area": d[0].replace("_score", ""), "score": d[1]} for d in sorted_dims[:3]]
    strongest = [{"area": d[0].replace("_score", ""), "score": d[1]} for d in sorted_dims[-3:]]

    # Score trend
    trend = [
        {
            "date": c.call_date.strftime("%Y-%m-%d"),
            "score": c.overall_score,
            "call_id": c.id
        }
        for c in calls[:20]
    ]

    overall_scores = [c.overall_score for c in calls if c.overall_score]
    avg_score = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0

    # 7-day vs 30-day comparison
    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    recent_scores = [c.overall_score for c in calls if c.call_date >= cutoff_7d and c.overall_score]
    avg_7d = round(sum(recent_scores) / len(recent_scores), 1) if recent_scores else avg_score

    return {
        "total_calls": len(calls),
        "avg_score": avg_score,
        "avg_score_7d": avg_7d,
        "score_change": round(avg_7d - avg_score, 1),
        "scores_by_dimension": scores_by_dim,
        "weakest_areas": weakest,
        "strongest_areas": strongest,
        "trend": trend
    }
