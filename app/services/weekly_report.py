"""
CallCoach CRM - Weekly Reporting Service

Generates comprehensive weekly reports with AI-powered insights, including:
- Call metrics and trends
- Agent performance analysis
- Conversion rate analysis
- Revenue impact assessment
- Actionable recommendations
"""
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models import Call, User, CallScore, PipelineDeal
from app.services.ai_coach import get_client
from app.config import ANTHROPIC_MODEL

logger = logging.getLogger(__name__)


WEEKLY_REPORT_SYSTEM = """You are CallCoach AI generating a comprehensive executive weekly report for a medical/aesthetic clinic.

Your report is for clinic managers/owners to understand team performance, identify conversion leaks, and prioritize coaching areas.

REPORTING FOCUS:
1. TEAM PERFORMANCE TREND: Is the team improving, stable, or declining? What's the overall sentiment?
2. CONVERSION LEAKING: Where exactly are deals dying? Opening phase? Discovery? Closing? Which agents struggle most?
3. ACTIONABLE RECOMMENDATIONS: Top 3 specific, implementable actions with expected impact
4. INDIVIDUAL AGENT HIGHLIGHTS: Who improved the most? Who needs coaching? Specific patterns per agent.
5. REVENUE IMPACT: What's the estimated revenue impact of performance changes? Use INR.

SCORING CONTEXT:
- Opening/Greeting: Building trust, using names, professional introduction
- Discovery: Problem identification, patient-centric questions, active listening
- Presentation: Solution clarity, value building, matching solutions to needs
- Objection Handling: AAA framework (Agree-Associate-Ask), not arguing with patients
- Closing: Soft closing technique, appointment booking, follow-up clarity
- Overall: Weighted average of all dimensions

REVENUE IMPACT CALCULATION (INR):
- Average treatment value: Consider clinic specialty (hair transplant: 80k-3L, botox: 5k-15k, laser: 3k-10k, dental: 2k-10k)
- Conversion rate improvement: Each 1% improvement in conversion = X additional deals per week
- Formula: (Current Conversion % - Baseline %) × Deal Volume × Avg Treatment Value
- Example: If conversion improved 2% on 50 calls, with 40k avg treatment = 50 × 2% × 40k = 40k/week revenue impact

Be specific with numbers. Reference actual data from the report."""


WEEKLY_REPORT_PROMPT = """Generate an executive weekly report for this clinic.

CLINIC INFO:
- Name: {clinic_name}
- Specialty: {specialty}

WEEK: {week_start} to {week_end}

CALL METRICS:
- Total calls: {total_calls}
- Avg call duration: {avg_duration_seconds}s
- Calls per agent: {calls_per_agent_json}

PERFORMANCE SCORES (0-100):
- Team avg overall score: {avg_overall_score}
- Team avg greeting: {avg_greeting_score}
- Team avg discovery: {avg_discovery_score}
- Team avg presentation: {avg_presentation_score}
- Team avg objection_handling: {avg_objection_handling_score}
- Team avg closing: {avg_closing_score}

SENTIMENT ANALYSIS:
{sentiment_distribution_json}

CONVERSION METRICS:
- Meetings booked: {meetings_booked}
- Deals won: {deals_won}
- Estimated conversion rate: {conversion_rate}%
- Previous week conversion: {prev_week_conversion}%

TOP PERFORMERS:
- Best overall score agent: {best_agent_name} ({best_agent_score})
- Most improved agent: {most_improved_agent_name} (from {most_improved_before} to {most_improved_after})

AREAS OF CONCERN:
- Lowest scoring dimension: {lowest_dimension} ({lowest_dimension_score})
- Agent needing coaching: {struggling_agent_name} ({struggling_agent_score})

TREATMENTS DISCUSSED:
{treatments_discussed_json}

PREVIOUS WEEK COMPARISON:
{previous_week_comparison_json}

Return a JSON response:
{{
    "executive_summary": "2-3 sentence overall assessment of the week",
    "overall_trend": "improving|stable|declining with specific percentage or point change",
    "team_highlights": [
        "Specific positive observation with data",
        "Another strength noticed"
    ],
    "conversion_leak_analysis": {{
        "primary_leak_stage": "opening|discovery|presentation|objection|closing",
        "evidence": "Why we believe this is where deals are leaking",
        "affected_agents": ["agent1", "agent2"],
        "estimated_opportunity": "If fixed, X% improvement expected, worth INRxxx/week"
    }},
    "individual_agent_insights": [
        {{
            "agent_name": "Name",
            "performance_level": "excellent|good|needs_coaching|concerning",
            "key_strength": "What they do well",
            "key_weakness": "Area needing development",
            "specific_action": "One concrete action for this agent",
            "improvement_trajectory": "improving|stable|declining"
        }}
    ],
    "top_3_recommendations": [
        {{
            "rank": 1,
            "recommendation": "Specific, actionable recommendation",
            "rationale": "Why this matters based on data",
            "expected_impact": "Expected outcome + INR value if applicable",
            "implementation": "How to do it",
            "timeline": "Week/Days"
        }}
    ],
    "revenue_impact": {{
        "estimated_weekly_impact": "₹X current performance",
        "improvement_opportunity": "If all agents score +10, estimated ₹X/week additional revenue",
        "high_value_treatments": "treatments with highest discussion frequency",
        "conversion_rate_change": "% change vs previous week"
    }},
    "metrics_snapshot": {{
        "total_calls": {total_calls},
        "avg_score": round({avg_overall_score}),
        "best_agent_score": {best_agent_score},
        "conversion_rate": {conversion_rate}%
    }}
}}"""


def generate_weekly_report(
    db: Session,
    clinic_id: str,
    week_start: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive weekly report for a clinic.

    Args:
        db: Database session
        clinic_id: Clinic ID to generate report for
        week_start: Start of the week (defaults to last Monday)

    Returns:
        Dict with all metrics and AI-generated narrative
    """
    # Calculate week boundaries
    if week_start is None:
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=7)

    logger.info(f"Generating weekly report for clinic {clinic_id} from {week_start} to {week_end}")

    # Query all calls for the week
    calls = db.query(Call).filter(
        Call.clinic_id == clinic_id,
        Call.call_date >= week_start,
        Call.call_date < week_end,
        Call.overall_score.isnot(None)
    ).all()

    # Query clinic info
    clinic = db.query(User).filter(User.clinic_id == clinic_id).first()
    clinic_obj = clinic.clinic if clinic else None

    # ---- BASIC METRICS ----
    total_calls = len(calls)

    if total_calls == 0:
        return {
            "clinic_id": clinic_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_calls": 0,
            "avg_score": 0,
            "conversion_rate": 0,
            "ai_summary": "No calls recorded this week.",
            "ai_recommendations": [],
            "revenue_impact": {},
            "calls_by_day": {},
            "sentiment_distribution": {}
        }

    # Average score and metrics
    avg_overall_score = sum(c.overall_score for c in calls if c.overall_score) / total_calls if calls else 0

    # Call scores breakdown
    call_scores = db.query(CallScore).filter(
        CallScore.call_id.in_([c.id for c in calls])
    ).all()

    avg_greeting = sum(s.greeting_score for s in call_scores if s.greeting_score) / len(call_scores) if call_scores else 0
    avg_discovery = sum(s.discovery_score for s in call_scores if s.discovery_score) / len(call_scores) if call_scores else 0
    avg_presentation = sum(s.presentation_score for s in call_scores if s.presentation_score) / len(call_scores) if call_scores else 0
    avg_objection = sum(s.objection_handling_score for s in call_scores if s.objection_handling_score) / len(call_scores) if call_scores else 0
    avg_closing = sum(s.closing_score for s in call_scores if s.closing_score) / len(call_scores) if call_scores else 0

    # ---- SENTIMENT DISTRIBUTION ----
    sentiment_counts = {}
    for call in calls:
        sentiment = call.ai_sentiment or "neutral"
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

    sentiment_distribution = {
        sent: {
            "count": count,
            "percentage": round(count / total_calls * 100, 1)
        }
        for sent, count in sentiment_counts.items()
    }

    # ---- CALLS PER DAY ----
    calls_by_day = {}
    for call in calls:
        day_key = call.call_date.date().isoformat()
        calls_by_day[day_key] = calls_by_day.get(day_key, 0) + 1

    # ---- AGENT PERFORMANCE ----
    agents_data = {}
    for call in calls:
        if call.agent_id not in agents_data:
            agents_data[call.agent_id] = {
                "name": call.agent.full_name,
                "calls": [],
                "total_calls": 0,
                "avg_score": 0
            }
        agents_data[call.agent_id]["calls"].append(call.overall_score)
        agents_data[call.agent_id]["total_calls"] += 1

    for agent_id, data in agents_data.items():
        data["avg_score"] = sum(data["calls"]) / len(data["calls"]) if data["calls"] else 0

    # Best and worst agents
    sorted_agents = sorted(agents_data.items(), key=lambda x: x[1]["avg_score"], reverse=True)
    best_agent = sorted_agents[0] if sorted_agents else None
    worst_agent = sorted_agents[-1] if sorted_agents else None

    best_agent_name = best_agent[1]["name"] if best_agent else "N/A"
    best_agent_score = round(best_agent[1]["avg_score"], 1) if best_agent else 0
    worst_agent_name = worst_agent[1]["name"] if worst_agent else "N/A"
    worst_agent_score = round(worst_agent[1]["avg_score"], 1) if worst_agent else 0

    # ---- TREATMENTS DISCUSSED ----
    treatments = {}
    for call in calls:
        if call.ai_key_topics:
            for topic in call.ai_key_topics:
                treatments[topic] = treatments.get(topic, 0) + 1

    top_treatments = sorted(treatments.items(), key=lambda x: x[1], reverse=True)[:5]
    treatments_json = json.dumps({t[0]: t[1] for t in top_treatments})

    # ---- CONVERSION METRICS ----
    meetings_booked = len([c for c in calls if c.ai_intent == "booking"])
    deals_won = db.query(PipelineDeal).filter(
        PipelineDeal.clinic_id == clinic_id,
        PipelineDeal.status == "won",
        PipelineDeal.actual_close_date >= week_start,
        PipelineDeal.actual_close_date < week_end
    ).count()

    conversion_rate = (meetings_booked / total_calls * 100) if total_calls > 0 else 0

    # ---- PREVIOUS WEEK COMPARISON ----
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start
    prev_calls = db.query(Call).filter(
        Call.clinic_id == clinic_id,
        Call.call_date >= prev_week_start,
        Call.call_date < prev_week_end,
        Call.overall_score.isnot(None)
    ).all()

    prev_avg_score = sum(c.overall_score for c in prev_calls) / len(prev_calls) if prev_calls else 0
    prev_meetings_booked = len([c for c in prev_calls if c.ai_intent == "booking"])
    prev_conversion = (prev_meetings_booked / len(prev_calls) * 100) if prev_calls else 0

    score_change = avg_overall_score - prev_avg_score
    conversion_change = conversion_rate - prev_conversion

    previous_week_comparison = json.dumps({
        "prev_avg_score": round(prev_avg_score, 1),
        "score_change": round(score_change, 1),
        "prev_conversion": round(prev_conversion, 1),
        "conversion_change": round(conversion_change, 1)
    })

    # ---- CALLS PER AGENT ----
    calls_per_agent = {}
    for agent_id, data in agents_data.items():
        calls_per_agent[data["name"]] = data["total_calls"]

    calls_per_agent_json = json.dumps(calls_per_agent)

    # ---- AVERAGE DURATION ----
    avg_duration = sum(c.duration_seconds for c in calls) / total_calls if calls else 0

    # ---- SCORING DIMENSION ANALYSIS ----
    dimensions = {
        "greeting": avg_greeting,
        "discovery": avg_discovery,
        "presentation": avg_presentation,
        "objection": avg_objection,
        "closing": avg_closing
    }
    lowest_dimension = min(dimensions, key=dimensions.get)
    lowest_dimension_score = round(dimensions[lowest_dimension], 1)

    # ---- STRUGGLING AGENT ----
    struggling_agent_name = worst_agent_name
    struggling_agent_score = worst_agent_score

    # ---- MOST IMPROVED AGENT ----
    most_improved_agent_name = "N/A"
    most_improved_before = 0
    most_improved_after = 0

    if prev_calls and agents_data:
        prev_agents_data = {}
        for call in prev_calls:
            if call.agent_id not in prev_agents_data:
                prev_agents_data[call.agent_id] = []
            prev_agents_data[call.agent_id].append(call.overall_score)

        improvements = {}
        for agent_id, data in agents_data.items():
            prev_score = sum(prev_agents_data.get(agent_id, [0])) / len(prev_agents_data.get(agent_id, [0])) if agent_id in prev_agents_data else 0
            curr_score = data["avg_score"]
            improvement = curr_score - prev_score
            if improvement > 0:
                improvements[agent_id] = {
                    "improvement": improvement,
                    "name": data["name"],
                    "prev": prev_score,
                    "curr": curr_score
                }

        if improvements:
            most_improved = max(improvements.items(), key=lambda x: x[1]["improvement"])
            most_improved_agent_name = most_improved[1]["name"]
            most_improved_before = round(most_improved[1]["prev"], 1)
            most_improved_after = round(most_improved[1]["curr"], 1)

    # ---- CALL AI COACH FOR SUMMARY ----
    specialty = clinic_obj.specialty if clinic_obj else "general"
    clinic_name = clinic_obj.name if clinic_obj else "Clinic"

    ai_prompt = WEEKLY_REPORT_PROMPT.format(
        clinic_name=clinic_name,
        specialty=specialty,
        week_start=week_start.strftime("%Y-%m-%d"),
        week_end=week_end.strftime("%Y-%m-%d"),
        total_calls=total_calls,
        avg_duration_seconds=int(avg_duration),
        calls_per_agent_json=calls_per_agent_json,
        avg_overall_score=round(avg_overall_score, 1),
        avg_greeting_score=round(avg_greeting, 1),
        avg_discovery_score=round(avg_discovery, 1),
        avg_presentation_score=round(avg_presentation, 1),
        avg_objection_handling_score=round(avg_objection, 1),
        avg_closing_score=round(avg_closing, 1),
        sentiment_distribution_json=json.dumps(sentiment_distribution),
        meetings_booked=meetings_booked,
        deals_won=deals_won,
        conversion_rate=round(conversion_rate, 1),
        prev_week_conversion=round(prev_conversion, 1),
        best_agent_name=best_agent_name,
        best_agent_score=best_agent_score,
        most_improved_agent_name=most_improved_agent_name,
        most_improved_before=most_improved_before,
        most_improved_after=most_improved_after,
        lowest_dimension=lowest_dimension,
        lowest_dimension_score=lowest_dimension_score,
        struggling_agent_name=struggling_agent_name,
        struggling_agent_score=struggling_agent_score,
        treatments_discussed_json=treatments_json,
        previous_week_comparison_json=previous_week_comparison
    )

    ai_summary = {}
    ai_recommendations = []
    revenue_impact = {}

    try:
        client = get_client()
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=3000,
            system=WEEKLY_REPORT_SYSTEM,
            messages=[{"role": "user", "content": ai_prompt}]
        )

        result_text = response.content[0].text
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

        ai_summary = json.loads(result_text.strip())
        ai_recommendations = ai_summary.get("top_3_recommendations", [])
        revenue_impact = ai_summary.get("revenue_impact", {})

    except Exception as e:
        logger.error(f"AI summary generation failed: {e}")
        ai_summary = {
            "executive_summary": "Report generation partially completed",
            "overall_trend": "stable"
        }

    # ---- RETURN STRUCTURED REPORT ----
    return {
        "clinic_id": clinic_id,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_calls": total_calls,
        "avg_score": round(avg_overall_score, 1),
        "best_agent_name": best_agent_name,
        "best_agent_score": best_agent_score,
        "worst_agent_name": worst_agent_name,
        "worst_agent_score": worst_agent_score,
        "conversion_rate": round(conversion_rate, 1),
        "meetings_booked": meetings_booked,
        "deals_won": deals_won,
        "calls_by_day": calls_by_day,
        "sentiment_distribution": sentiment_distribution,
        "top_treatments": {t[0]: t[1] for t in top_treatments},
        "agent_performance": {
            agent_id: {
                "name": data["name"],
                "total_calls": data["total_calls"],
                "avg_score": round(data["avg_score"], 1)
            }
            for agent_id, data in agents_data.items()
        },
        "score_breakdown": {
            "greeting": round(avg_greeting, 1),
            "discovery": round(avg_discovery, 1),
            "presentation": round(avg_presentation, 1),
            "objection_handling": round(avg_objection, 1),
            "closing": round(avg_closing, 1)
        },
        "ai_summary": ai_summary,
        "ai_recommendations": ai_recommendations,
        "revenue_impact": revenue_impact
    }
