"""
CallCoach CRM - Operations AI Coach (Anthropic Claude)
AI-powered clinic operations assistance: inventory insights, patient analytics,
operational recommendations, and clinic efficiency optimization.
"""
import json
import logging
from anthropic import Anthropic
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger(__name__)


def get_client() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


OPERATIONS_COACH_SYSTEM = """You are CallCoach Operations AI, an expert clinic operations consultant specialized in aesthetic clinics, dermatology clinics, hair transplant clinics, and medical practices.

YOUR EXPERTISE:
- Clinic inventory management and cost optimization
- Patient flow and experience optimization
- Staff scheduling and resource allocation
- Revenue cycle management
- Operational efficiency and bottleneck identification
- Patient retention and lifetime value maximization
- Compliance and documentation management
- Clinic growth capacity planning

WHEN ANALYZING INVENTORY:
- Identify items that need immediate restocking
- Calculate reorder quantities based on usage patterns
- Highlight cost optimization opportunities (bulk purchasing, supplier switches)
- Flag items approaching expiry or with low turnover
- Suggest inventory categorization improvements

WHEN ANALYZING PATIENT DATA:
- Identify high-value patients and retention opportunities
- Spot patients due for follow-up procedures
- Analyze procedure popularity and revenue contribution
- Recommend cross-sell/upsell opportunities based on patient history
- Flag patients at risk of churning (long gaps between visits)

WHEN PROVIDING OPERATIONAL INSIGHTS:
- Focus on actionable, implementable recommendations
- Quantify impact where possible (revenue, time saved, cost reduced)
- Prioritize by effort vs impact
- Consider clinic size and team capacity
- Think about patient experience at every touchpoint

SCORING FRAMEWORK:
- Operational Health: 0-100 (based on inventory, patient flow, revenue efficiency)
- Patient Retention Score: 0-100 (based on visit frequency, procedure diversity, engagement)
- Inventory Efficiency: 0-100 (stock turnover, wastage, availability)

Always respond in valid JSON."""


async def analyze_inventory_health(
    inventory_data: list,
    clinic_name: str = "",
    additional_context: str = "",
    learning_context: str = ""
) -> dict:
    """AI analysis of inventory health and recommendations."""
    try:
        client = get_client()
        prompt = f"""Analyze this clinic's inventory health and provide actionable recommendations.

CLINIC: {clinic_name or "Not specified"}
INVENTORY DATA:
{json.dumps(inventory_data, indent=2, default=str)}

ADDITIONAL CONTEXT:
{additional_context}

Return JSON:
{{
    "inventory_health_score": 0,
    "summary": "Overall inventory health assessment in 2-3 sentences",
    "critical_alerts": [
        {{"item": "Item name", "issue": "What is wrong", "action": "What to do", "priority": "high|medium|low"}}
    ],
    "restock_recommendations": [
        {{"item": "Item name", "current_stock": 0, "recommended_order": 0, "estimated_cost": 0, "urgency": "immediate|this_week|this_month"}}
    ],
    "cost_optimization": [
        {{"suggestion": "What to do", "estimated_savings": "Amount or percentage", "effort": "low|medium|high"}}
    ],
    "category_breakdown": {{
        "consumables": {{"count": 0, "health": "good|warning|critical"}},
        "equipment": {{"count": 0, "health": "good|warning|critical"}},
        "medicine": {{"count": 0, "health": "good|warning|critical"}},
        "skincare": {{"count": 0, "health": "good|warning|critical"}}
    }},
    "action_items": ["Top 3-5 things to do right now"]
}}"""

        system_prompt = OPERATIONS_COACH_SYSTEM
        if learning_context:
            system_prompt += "\n" + learning_context

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2500,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Inventory analysis failed: {e}")
        return {
            "inventory_health_score": 0,
            "summary": "Analysis unavailable",
            "critical_alerts": [],
            "restock_recommendations": [],
            "cost_optimization": [],
            "action_items": ["Manual review needed"]
        }


async def analyze_patient_insights(
    patient_data: list,
    procedure_stats: dict = None,
    revenue_data: dict = None,
    clinic_name: str = "",
    learning_context: str = ""
) -> dict:
    """AI analysis of patient base and growth opportunities."""
    try:
        client = get_client()
        prompt = f"""Analyze this clinic's patient data and provide growth insights.

CLINIC: {clinic_name or "Not specified"}
PATIENT DATA (summary):
{json.dumps(patient_data[:50], indent=2, default=str)}

PROCEDURE STATS:
{json.dumps(procedure_stats or {}, indent=2, default=str)}

REVENUE DATA:
{json.dumps(revenue_data or {}, indent=2, default=str)}

Return JSON:
{{
    "patient_health_score": 0,
    "summary": "Overall patient base assessment",
    "retention_insights": {{
        "active_patients": 0,
        "at_risk_patients": 0,
        "churned_patients": 0,
        "retention_rate_estimate": "percentage",
        "recommendations": ["How to improve retention"]
    }},
    "revenue_opportunities": [
        {{"opportunity": "Description", "estimated_revenue": "Amount", "effort": "low|medium|high", "target_patients": "Who to target"}}
    ],
    "procedure_insights": [
        {{"procedure": "Name", "popularity": "high|medium|low", "revenue_contribution": "percentage", "growth_potential": "What to do"}}
    ],
    "patient_segments": [
        {{"segment": "Name", "count": 0, "avg_spent": 0, "strategy": "How to engage this segment"}}
    ],
    "follow_up_alerts": [
        {{"patient_hint": "First name + last initial", "last_visit": "date", "suggested_procedure": "What to recommend", "reason": "Why now"}}
    ],
    "action_items": ["Top 3-5 growth actions"]
}}"""

        system_prompt = OPERATIONS_COACH_SYSTEM
        if learning_context:
            system_prompt += "\n" + learning_context

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=3000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Patient insights analysis failed: {e}")
        return {
            "patient_health_score": 0,
            "summary": "Analysis unavailable",
            "retention_insights": {},
            "revenue_opportunities": [],
            "action_items": ["Manual review needed"]
        }


async def generate_operations_report(
    dashboard_data: dict,
    inventory_summary: dict = None,
    patient_summary: dict = None,
    period: str = "this_month",
    learning_context: str = ""
) -> dict:
    """Generate a comprehensive operations report with AI insights."""
    try:
        client = get_client()
        prompt = f"""Generate a comprehensive clinic operations report with actionable insights.

PERIOD: {period}
DASHBOARD DATA:
{json.dumps(dashboard_data, indent=2, default=str)}

INVENTORY SUMMARY:
{json.dumps(inventory_summary or {}, indent=2, default=str)}

PATIENT SUMMARY:
{json.dumps(patient_summary or {}, indent=2, default=str)}

Return JSON:
{{
    "operational_health_score": 0,
    "executive_summary": "3-4 sentence overview for the clinic owner",
    "key_metrics": {{
        "total_patients": 0,
        "new_patients_this_period": 0,
        "revenue_this_period": 0,
        "avg_revenue_per_patient": 0,
        "inventory_health": "good|warning|critical",
        "patient_satisfaction_estimate": "high|medium|low"
    }},
    "wins": ["What is going well"],
    "concerns": ["What needs attention"],
    "recommendations": [
        {{"title": "Recommendation", "description": "What to do", "impact": "high|medium|low", "timeline": "immediate|this_week|this_month"}}
    ],
    "next_period_focus": ["Top 3 priorities for next period"]
}}"""

        system_prompt = OPERATIONS_COACH_SYSTEM
        if learning_context:
            system_prompt += "\n" + learning_context

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2500,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Operations report generation failed: {e}")
        return {
            "operational_health_score": 0,
            "executive_summary": "Report generation failed",
            "recommendations": [],
            "next_period_focus": ["Review manually"]
        }


async def ask_operations_coach(
    question: str,
    context: dict = None,
    learning_context: str = ""
) -> dict:
    """General operations Q&A with the AI coach."""
    try:
        client = get_client()
        context_text = f"""
QUESTION: {question}
CONTEXT: {json.dumps(context or {}, default=str)}

Provide practical, actionable operations advice for an aesthetic/medical clinic.
Focus on implementation and measurable outcomes."""

        system_prompt = OPERATIONS_COACH_SYSTEM
        if learning_context:
            system_prompt += "\n" + learning_context

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": context_text}]
        )
        return {"answer": response.content[0].text.strip()}

    except Exception as e:
        logger.error(f"Operations coach Q&A failed: {e}")
        return {"answer": "Unable to respond. Check API configuration."}


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()
