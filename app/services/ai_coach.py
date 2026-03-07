"""
CallCoach CRM - AI Coaching Engine (Anthropic Claude)

This is the core intelligence layer. It handles:
1. Post-call analysis (summary, sentiment, scoring, tips)
2. Live coaching (real-time tips during calls)
3. Progressive growth tracking (patterns over time)
4. Deal health assessment
"""
import json
import logging
from typing import Optional
from datetime import datetime, timedelta
from anthropic import Anthropic
from sqlalchemy.orm import Session
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger(__name__)


def get_client() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


# ---- SYSTEM PROMPTS ----

CALL_ANALYZER_SYSTEM = """You are CallCoach AI, an expert sales coach specializing in medical aesthetics, dermatology, hair transplant, and cosmetic surgery clinics. You analyze phone calls between clinic staff and patients/prospects.

Your analysis must be practical, specific, and actionable. You think like a seasoned clinic sales director who has closed thousands of consultations.

When analyzing a call transcript, you evaluate across these dimensions:
1. GREETING & RAPPORT (0-100): Warmth, professionalism, name usage, building connection
2. DISCOVERY (0-100): Identifying patient needs, concerns, motivations, budget signals
3. PRESENTATION (0-100): Explaining treatments clearly, matching solutions to needs, building value
4. OBJECTION HANDLING (0-100): Addressing concerns about price, pain, results, timing
5. CLOSING (0-100): Asking for the booking, creating urgency, clear next steps
6. RAPPORT (0-100): Empathy, active listening cues, personalisation
7. ACTIVE LISTENING (0-100): Acknowledging concerns, asking follow-up questions, not interrupting
8. URGENCY CREATION (0-100): Limited slots, seasonal offers, progressive concern framing
9. FOLLOW-UP SETUP (0-100): Getting contact details, setting callback time, sending info

You always provide:
- Specific quotes from the transcript as evidence
- Exact phrases they should have used instead
- One micro-win they can implement on their very next call

Respond ONLY in valid JSON format."""


CALL_ANALYSIS_PROMPT = """Analyze this clinic phone call transcript and return a comprehensive JSON analysis.

CALL CONTEXT:
- Call Type: {call_type}
- Direction: {direction}
- Duration: {duration} seconds
- Agent: {agent_name}

TRANSCRIPT:
{transcript}

Return this exact JSON structure:
{{
    "summary": "2-3 sentence summary of what happened on this call",
    "sentiment": "positive|neutral|negative|mixed",
    "intent": "booking|inquiry|complaint|follow_up|price_check|cancellation|referral|other",
    "key_topics": ["topic1", "topic2"],
    "action_items": [
        "Specific action item 1",
        "Specific action item 2"
    ],
    "objections_detected": [
        {{"objection": "exact objection text", "handled": true/false, "handling_quality": "good|weak|missed"}}
    ],
    "buying_signals": [
        {{"signal": "what they said", "strength": "strong|moderate|weak"}}
    ],
    "scores": {{
        "greeting_score": 0-100,
        "discovery_score": 0-100,
        "presentation_score": 0-100,
        "objection_handling_score": 0-100,
        "closing_score": 0-100,
        "rapport_score": 0-100,
        "active_listening_score": 0-100,
        "urgency_creation_score": 0-100,
        "follow_up_setup_score": 0-100,
        "overall_score": 0-100
    }},
    "scoring_details": {{
        "greeting": "Why this score - with specific quote evidence",
        "discovery": "Why this score",
        "presentation": "Why this score",
        "objection_handling": "Why this score",
        "closing": "Why this score",
        "rapport": "Why this score",
        "active_listening": "Why this score",
        "urgency_creation": "Why this score",
        "follow_up_setup": "Why this score"
    }},
    "what_went_well": [
        "Specific thing done well with quote",
        "Another thing done well"
    ],
    "what_to_improve": [
        "Specific improvement area with exact alternative phrase to use",
        "Another improvement"
    ],
    "improvement_tips": [
        {{
            "area": "discovery|closing|objection_handling|etc",
            "tip": "Specific actionable tip",
            "example_phrase": "Exact script they can use next time",
            "priority": "high|medium|low"
        }}
    ],
    "micro_win": "One small change to make on the very next call that will have immediate impact",
    "extracted_contact": {{
        "name": "Caller's full name if mentioned in the transcript, or null",
        "phone": "Caller's phone number if mentioned in the transcript, or null",
        "email": "Caller's email if mentioned in the transcript, or null"
    }}
}}"""


LIVE_COACHING_SYSTEM = """You are CallCoach AI providing REAL-TIME coaching during a live clinic phone call. Your tips appear on the agent's screen while they're talking.

RULES:
- Be extremely brief (max 15 words per tip)
- Focus on the IMMEDIATE next thing to say or do
- Detect objections and suggest responses instantly
- Spot buying signals and suggest closing techniques
- Never repeat the same tip twice in a session
- Use action verbs: "Ask about...", "Mention...", "Try saying..."
- Flag missed opportunities immediately

You receive transcript chunks as they happen. Respond with coaching tips in JSON format."""


LIVE_COACHING_PROMPT = """LIVE CALL IN PROGRESS for a {clinic_specialty} clinic.

Recent transcript chunk:
{transcript_chunk}

Full context so far:
{full_context}

Previous tips given (do not repeat):
{previous_tips}

Analyze the latest chunk and return JSON:
{{
    "tips": [
        {{
            "type": "coaching_tip|objection_alert|closing_cue|buying_signal|warning",
            "content": "Brief actionable tip (max 15 words)",
            "urgency": "immediate|when_appropriate|fyi",
            "category": "discovery|presentation|objection|closing|rapport|follow_up"
        }}
    ],
    "detected_intent": "what the caller seems to want right now",
    "caller_mood": "positive|neutral|hesitant|negative|excited"
}}

Only include tips if there's something actionable. Return empty tips array if nothing new to say."""


PROGRESSIVE_GROWTH_SYSTEM = """You are CallCoach AI analyzing a sales agent's performance over time at a medical/aesthetic clinic. You identify patterns, trends, and create personalized growth plans.

Focus on:
1. Score trends across dimensions
2. Recurring weaknesses
3. Improvements since last period
4. Specific habits to build
5. Milestone celebrations

Be encouraging but honest. Frame feedback constructively."""


DEAL_HEALTH_SYSTEM = """You are CallCoach AI analyzing a sales pipeline deal for a medical/aesthetic clinic. Assess deal health based on all interactions, timing, and patient behavior patterns.

Consider:
- Time in current stage
- Number of touchpoints
- Sentiment trend across calls
- Buying signals vs objections ratio
- Follow-up consistency
- Treatment value and typical conversion rates"""


# ---- ANALYSIS FUNCTIONS ----

async def analyze_call(
    transcript: str,
    call_type: str = "inbound",
    direction: str = "inbound",
    duration: int = 0,
    agent_name: str = "Agent"
) -> dict:
    """Full post-call AI analysis."""
    try:
        client = get_client()
        prompt = CALL_ANALYSIS_PROMPT.format(
            call_type=call_type,
            direction=direction,
            duration=duration,
            agent_name=agent_name,
            transcript=transcript
        )

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=CALL_ANALYZER_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text
        # Clean potential markdown code fences
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

        return json.loads(result_text.strip())

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        return _fallback_analysis()
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return _fallback_analysis()


async def get_live_coaching_tip(
    transcript_chunk: str,
    full_context: str,
    previous_tips: list,
    clinic_specialty: str = "aesthetic"
) -> dict:
    """Real-time coaching tip during a live call."""
    try:
        client = get_client()
        prompt = LIVE_COACHING_PROMPT.format(
            clinic_specialty=clinic_specialty,
            transcript_chunk=transcript_chunk,
            full_context=full_context[-3000:],  # Keep context manageable
            previous_tips=json.dumps(previous_tips[-10:])  # Last 10 tips
        )

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=500,
            system=LIVE_COACHING_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

        return json.loads(result_text.strip())

    except Exception as e:
        logger.error(f"Live coaching failed: {e}")
        return {"tips": [], "detected_intent": "unknown", "caller_mood": "neutral"}


async def analyze_agent_growth(
    agent_name: str,
    recent_scores: list,  # list of {date, scores_dict}
    total_calls: int,
    avg_score_30d: float,
    avg_score_7d: float,
    weakest_areas: list,
    strongest_areas: list
) -> dict:
    """Progressive growth analysis for an agent."""
    try:
        client = get_client()
        prompt = f"""Analyze this agent's growth trajectory and create a personalized coaching plan.

AGENT: {agent_name}
TOTAL CALLS ANALYZED: {total_calls}
30-DAY AVG SCORE: {avg_score_30d}
7-DAY AVG SCORE: {avg_score_7d}
SCORE TREND (last 10 calls): {json.dumps(recent_scores[-10:])}
WEAKEST AREAS: {json.dumps(weakest_areas)}
STRONGEST AREAS: {json.dumps(strongest_areas)}

Return JSON:
{{
    "overall_assessment": "1-2 sentence growth assessment",
    "trend": "improving|stable|declining",
    "growth_rate": "percentage improvement over last period",
    "milestones_achieved": ["milestone 1", "milestone 2"],
    "focus_areas": [
        {{
            "area": "dimension name",
            "current_score": 0-100,
            "target_score": 0-100,
            "specific_drill": "Practice exercise to improve this area",
            "timeline": "expected improvement timeline"
        }}
    ],
    "weekly_goals": [
        "Goal 1 for this week",
        "Goal 2 for this week"
    ],
    "encouragement": "Personalized motivational message based on their actual progress"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            system=PROGRESSIVE_GROWTH_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

        return json.loads(result_text.strip())

    except Exception as e:
        logger.error(f"Growth analysis failed: {e}")
        return {"overall_assessment": "Analysis unavailable", "trend": "stable", "focus_areas": [], "weekly_goals": []}


async def assess_deal_health(
    deal_info: dict,
    call_summaries: list,
    touchpoint_count: int,
    days_in_stage: int
) -> dict:
    """AI assessment of a deal's health and recommended next steps."""
    try:
        client = get_client()
        prompt = f"""Assess this deal's health for a medical/aesthetic clinic.

DEAL: {json.dumps(deal_info)}
CALL SUMMARIES: {json.dumps(call_summaries[-5:])}
TOTAL TOUCHPOINTS: {touchpoint_count}
DAYS IN CURRENT STAGE: {days_in_stage}

Return JSON:
{{
    "health": "hot|healthy|at_risk|cold",
    "win_probability": 0-100,
    "risk_factors": ["risk 1", "risk 2"],
    "positive_signals": ["signal 1", "signal 2"],
    "recommended_action": "Specific next action to move this deal forward",
    "suggested_script": "Opening line for the next call with this patient",
    "urgency_angle": "How to create urgency without being pushy",
    "days_to_act": "number of days before this deal goes cold"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            system=DEAL_HEALTH_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

        return json.loads(result_text.strip())

    except Exception as e:
        logger.error(f"Deal health assessment failed: {e}")
        return {"health": "unknown", "win_probability": 50, "recommended_action": "Follow up with the patient"}


def _fallback_analysis() -> dict:
    """Fallback when AI analysis fails."""
    return {
        "summary": "Analysis could not be completed. Please retry.",
        "sentiment": "neutral",
        "intent": "other",
        "key_topics": [],
        "action_items": ["Review call manually"],
        "objections_detected": [],
        "buying_signals": [],
        "scores": {
            "greeting_score": 0, "discovery_score": 0, "presentation_score": 0,
            "objection_handling_score": 0, "closing_score": 0, "rapport_score": 0,
            "active_listening_score": 0, "urgency_creation_score": 0,
            "follow_up_setup_score": 0, "overall_score": 0
        },
        "scoring_details": {},
        "what_went_well": [],
        "what_to_improve": [],
        "improvement_tips": [],
        "micro_win": "Ensure your AI API key is configured correctly."
    }


COACH_QA_SYSTEM = """You are CallCoach AI, an expert sales coach for medical aesthetics, dermatology, hair transplant, and cosmetic surgery clinics.

You are answering questions from a clinic team member about a specific call they handled. You have access to the call transcript, AI analysis, and scores.

Your answers should be:
- Specific to this call (reference exact moments/phrases from the transcript)
- Actionable (give concrete next steps, not vague advice)
- Encouraging but honest (praise what went well, be direct about improvements)
- Written like a senior sales director coaching a team member 1-on-1

Keep responses concise (2-4 paragraphs max). Use natural language, not bullet points unless asked."""


async def ask_coach_about_call(
    question: str,
    transcript: str,
    ai_summary: str = "",
    ai_sentiment: str = "",
    overall_score: float = 0,
    scores_detail: dict = None,
    what_went_well: list = None,
    what_to_improve: list = None,
    call_type: str = "inbound",
) -> dict:
    """Answer a user question about a specific call using AI coaching context."""
    try:
        client = get_client()
        context = f"""CALL CONTEXT:
- Type: {call_type}
- Overall Score: {overall_score}/100
- Sentiment: {ai_sentiment}
- Summary: {ai_summary}

SCORE BREAKDOWN: {json.dumps(scores_detail or {}, indent=2)}

WHAT WENT WELL: {json.dumps(what_went_well or [])}
WHAT TO IMPROVE: {json.dumps(what_to_improve or [])}

TRANSCRIPT:
{transcript[:6000]}

USER QUESTION: {question}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            system=COACH_QA_SYSTEM,
            messages=[{"role": "user", "content": context}]
        )
        answer = response.content[0].text.strip()
        return {"answer": answer}

    except Exception as e:
        logger.error(f"Coach Q&A failed: {e}")
        return {"answer": "I'm unable to answer right now. Please check your API configuration and try again."}
