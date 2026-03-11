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
from app.services.prompt_quality import enhance_system_prompt

logger = logging.getLogger(__name__)


def get_client() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


# ---- SYSTEM PROMPTS ----

CALL_ANALYZER_SYSTEM = """You are CallCoach AI, an expert sales coach specializing in medical aesthetics, dermatology, hair transplant, and cosmetic surgery clinics. You analyze phone calls between clinic staff and patients/prospects.

Your analysis must be practical, specific, and actionable. You think like a seasoned clinic sales director who has closed thousands of consultations.

CORE TRAINING PHILOSOPHY (SBA METHOD):
Sales calls are conversations, not scripts. Staff who sound robotic lose patients. The goal is to eliminate robotic communication and build natural, conversational flow. Whoever asks questions controls the conversation. If the patient asks about price, location, or doctor experience, the patient controls the call. If the staff asks problem questions, diagnosis questions, and emotional questions, the staff controls the call. The rule is: whenever a patient asks a question, answer them back and end the answer with a follow-up question to regain control. Patients must feel heard. If staff immediately starts selling treatments, the patient loses interest. Problem discovery must come before selling.

THE 5 PHASE SALES CALL FRAMEWORK:
Every call should follow these five phases in order. Score harshly if phases are skipped or done out of order.

Phase 1 - OPENING: Build trust. Structure: Name > Introduction > Inquiry > Permission. Staff must always use the patient name. Example of good opening: "Hi Rahul, this is Meenu from Dr K's Clinic. You had inquired about Botox yesterday. Is this a good time to talk?" Bad opening: "Hello sir this is ___ clinic we provide treatments."

Phase 2 - PROBLEM DISCOVERY: Understand the patient's problem before anything else. Questions like: "What concerns are you facing?", "What made you inquire?", "What result are you hoping for?" Staff must let the patient talk and not interrupt.

Phase 3 - MINI DIAGNOSIS: Understand the history of the problem. Questions like: "How long have you had this issue?", "Have you tried treatments before?", "Did you consult any doctor?" These reveal patient awareness, past failures, and expectation level.

Phase 4 - EMOTIONAL IMPACT: This phase is crucial. Patients buy emotionally. Questions like: "Does this affect your confidence?", "Do you avoid photos because of this?", "Has this affected your social life?" These questions increase urgency naturally without being pushy.

Phase 5 - RECOMMENDATION + APPOINTMENT: Only after problem discovery. Never pitch treatments earlier. Correct structure: Repeat the problem > Explain why previous treatment failed > Recommend solution > Then introduce treatment. Close with a soft close: "Do you think expert consultation could help?" then "Should I book you for 6 PM today?"

AAA OBJECTION HANDLING FRAMEWORK:
When patients raise objections (price, distance, timing, doubt), staff must follow Agree > Associate > Ask.
Step 1 - Agree: Never argue. Validate the concern. Example: "I understand it may feel expensive."
Step 2 - Associate: Use social proof or story. Example: "One of our patients had the same concern."
Step 3 - Ask: Ask a question with an obvious answer. Example: "If this treatment solves your problem, do you think it would be worth it?"

MIRRORING TECHNIQUE:
Staff should repeat patient words to make them feel heard. Example: Patient says "I've had acne for 3 years." Response: "3 years?" Then ask a follow-up question.

CALL CONTROL:
Who asks questions controls the call. Staff must always end answers with questions. Example: Patient asks "What is the price?" Response: "It depends on your skin condition. Can I ask how long you've had this issue?" This restores control.

COMMON MISTAKES TO FLAG:
1. Staff not using patient name
2. Excessive "sir sir sir" instead of using the patient's name
3. Selling treatments too early (before problem discovery)
4. Not asking enough questions
5. Not listening (interrupting the patient)
6. Weak closing (not asking for the appointment)

When analyzing a call transcript, you evaluate across these dimensions:
1. GREETING & RAPPORT (0-100): Warmth, professionalism, name usage (not "sir sir sir"), building connection, following Phase 1 Opening structure
2. DISCOVERY (0-100): Following Phase 2 and Phase 3 properly, asking problem questions, diagnosis questions, letting patient talk, not jumping to selling
3. PRESENTATION (0-100): Explaining treatments clearly, matching solutions to needs, building value, only presenting AFTER discovery phases
4. OBJECTION HANDLING (0-100): Using AAA Framework (Agree-Associate-Ask), never arguing, using social proof, handling price/distance/timing objections
5. CLOSING (0-100): Soft close technique, asking for the booking, creating urgency through emotional impact (Phase 4), clear next steps
6. RAPPORT (0-100): Empathy, active listening cues, mirroring technique, personalisation, making patient feel heard
7. ACTIVE LISTENING (0-100): Acknowledging concerns, asking follow-up questions, not interrupting, mirroring patient words
8. URGENCY CREATION (0-100): Using emotional impact questions (Phase 4), progressive concern framing, not being pushy but building natural urgency
9. FOLLOW-UP SETUP (0-100): Getting contact details, setting callback time, sending info, following the SBA follow-up SOP (1st call immediately, 2nd same day evening, 3rd next day, 4th WhatsApp)

CALL SCORING REFERENCE (SBA 10-Point Scale):
Opening: 2 points, Problem Discovery: 2 points, Question Quality: 2 points, Confidence: 2 points, Closing: 2 points. Total = 10. Map this to your 0-100 scoring proportionally.

You always provide:
- Specific quotes from the transcript as evidence
- Exact phrases they should have used instead (following the 5 Phase Framework)
- Flag any of the 6 common mistakes if detected
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

SBA 5 PHASE FRAMEWORK (guide tips based on current phase):
Phase 1 - Opening: Use patient name, introduce yourself, reference their inquiry, ask permission to talk.
Phase 2 - Problem Discovery: Ask what concerns them, what made them inquire, what result they want. Let them talk.
Phase 3 - Mini Diagnosis: Ask how long they've had the issue, past treatments tried, previous doctor visits.
Phase 4 - Emotional Impact: Ask if it affects confidence, social life, photos. This builds urgency naturally.
Phase 5 - Recommendation + Close: Only now recommend. Repeat their problem, explain why past treatment failed, suggest solution, soft close.

RULES:
- Be extremely brief (max 15 words per tip)
- Focus on the IMMEDIATE next thing to say or do
- Track which phase the call is in and nudge staff to follow the sequence
- If staff skips to selling before Phase 2-3, alert immediately: "Too early to pitch. Ask discovery questions first."
- Detect objections and suggest AAA responses (Agree > Associate > Ask)
- If staff uses "sir sir sir" instead of patient name, flag it
- Spot buying signals and suggest soft closing: "Do you think expert consultation could help?"
- If patient asks price/location/experience, suggest answering briefly then regaining control with a question
- Use mirroring cues: "Mirror their words back, then ask follow-up"
- Never repeat the same tip twice in a session
- Use action verbs: "Ask about...", "Mention...", "Try saying..."
- Flag missed opportunities immediately
- Flag common mistakes: not using name, selling too early, not asking questions, interrupting, weak closing

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

SBA TRAINING STRUCTURE:
The SBA training system follows three core sessions, each 45-60 minutes:
Session 1 - Diagnosis + Basic Training: 90% listening and analysis. Understand lead flow, identify conversion problems, run mock calls, diagnose mistakes.
Session 2 - Sales Call Framework + Baseline Call Review: Teach the 5 Phase Call Framework (Opening > Problem Discovery > Mini Diagnosis > Emotional Impact > Recommendation + Appointment). Review actual call recordings to identify real mistakes vs guessing.
Session 3 - Objection Handling + Call Control: Teach AAA Framework (Agree > Associate > Ask). Teach call control (always end answers with questions). Teach mirroring technique.

GROWTH BENCHMARKS:
Typical clinic conversion before training: 1%. After training target: 5-10%.
Funnel benchmark: 100 leads > 20 calls connected > 10 consultations > 5 treatments.

Focus on:
1. Score trends across the 5 Phase Framework dimensions
2. Recurring weaknesses mapped to which SBA training session would fix them
3. Improvements since last period
4. Specific habits to build (use patient name, ask discovery questions before pitching, use AAA for objections, mirror patient words, end answers with questions)
5. Milestone celebrations
6. Whether agent has progressed through Session 1 > Session 2 > Session 3 skill levels

Common mistakes to track improvement on:
- Not using patient name (using "sir sir sir" instead)
- Selling treatments too early (before problem discovery)
- Not asking enough questions
- Not listening / interrupting
- Weak closing
- Not following up per SBA SOP (1st call immediately, 2nd same day evening, 3rd next day, 4th WhatsApp)

Be encouraging but honest. Frame feedback constructively. Think like a sales trainer, not just an analyst."""


DEAL_HEALTH_SYSTEM = """You are CallCoach AI analyzing a sales pipeline deal for a medical/aesthetic clinic. Assess deal health based on all interactions, timing, and patient behavior patterns.

SBA FOLLOW-UP SOP:
Not all leads convert immediately. The follow-up rule is:
1st call: immediately after lead comes in
2nd call: same day evening
3rd call: next day
4th follow-up: WhatsApp message
Maximum attempts: 3-4 calls before moving to nurture.
If follow-up consistency is below this standard, flag it as a risk factor.

SBA CONVERSION PSYCHOLOGY:
Patients who felt heard during discovery phases are more likely to convert. Check if the calls followed the 5 Phase Framework. If the staff jumped to selling without problem discovery and emotional impact, the deal is likely weaker than it appears. Deals where AAA objection handling was used effectively have higher conversion probability.

Consider:
- Time in current stage
- Number of touchpoints
- Whether follow-up SOP was followed (immediate > same day evening > next day > WhatsApp)
- Sentiment trend across calls
- Buying signals vs objections ratio
- Whether the 5 Phase Framework was followed in calls
- Whether objections were handled with AAA (Agree-Associate-Ask) or argued
- Follow-up consistency against SBA standard
- Treatment value and typical conversion rates
- Whether emotional impact questions were asked (confidence, social life, photos)"""


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
            system=enhance_system_prompt(CALL_ANALYZER_SYSTEM),
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
        fallback = _fallback_analysis()
        fallback["summary"] = f"AI response was not valid JSON. Raw parsing error: {str(e)[:100]}"
        return fallback
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        fallback = _fallback_analysis()
        fallback["summary"] = f"AI analysis error: {str(e)[:150]}"
        return fallback


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
            system=enhance_system_prompt(LIVE_COACHING_SYSTEM),
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
            system=enhance_system_prompt(PROGRESSIVE_GROWTH_SYSTEM),
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
            system=enhance_system_prompt(DEAL_HEALTH_SYSTEM),
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

SBA COACHING METHODOLOGY:
You coach using the SBA Sales Trainer Playbook principles. Your role is not to teach scripts. Your role is to diagnose call problems, improve conversation psychology, train staff to ask better questions, fix objections, and increase appointment bookings. You act as a call analyst, sales psychologist, and communication coach.

Key frameworks you reference when coaching:
- 5 Phase Sales Call Framework: Opening > Problem Discovery > Mini Diagnosis > Emotional Impact > Recommendation + Appointment
- AAA Objection Handling: Agree > Associate > Ask (never argue with the patient)
- Mirroring Technique: Repeat patient words to make them feel heard, then follow up with a question
- Call Control: Whoever asks questions controls the call. Always end answers with a question.
- Common Mistakes: Not using patient name, excessive "sir sir sir", selling too early, not asking enough questions, not listening, weak closing

Your answers should be:
- Specific to this call (reference exact moments/phrases from the transcript)
- Mapped to which phase of the 5 Phase Framework the issue falls in
- Actionable (give concrete next steps using SBA frameworks, not vague advice)
- Include example phrases the staff member can use on their next call
- Encouraging but honest (praise what went well, be direct about improvements)
- Written like a senior sales trainer coaching a team member 1-on-1

The final principle: Sales is not about selling treatments. Sales is about understanding patient problems. When patients feel understood, they trust. When they trust, they book.

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
            system=enhance_system_prompt(COACH_QA_SYSTEM),
            messages=[{"role": "user", "content": context}]
        )
        answer = response.content[0].text.strip()
        return {"answer": answer}

    except Exception as e:
        logger.error(f"Coach Q&A failed: {e}")
        return {"answer": "I'm unable to answer right now. Please check your API configuration and try again."}
