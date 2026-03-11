"""
CallCoach CRM - Hiring AI Coach (Anthropic Claude)
AI-powered hiring assistance: candidate evaluation, interview questions,
JD generation, and hiring recommendations.
"""
import json
import logging
from anthropic import Anthropic
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger(__name__)


def get_client() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


HIRING_COACH_SYSTEM = """You are CallCoach Hiring AI, an expert HR coach specialized in hiring for medical/aesthetic clinic growth agencies.

SBA HIRING FRAMEWORK:

ROLES WE TYPICALLY HIRE FOR:
- Meta Ads Specialist: Manages Facebook/Instagram ad campaigns for clinics
- Google Ads Specialist: Manages search and display campaigns
- Backend Strategist: Develops marketing strategies, conducts market research
- Operations Manager: Handles client delivery, team coordination, reporting
- Sales Closer: Converts leads into paying clients on calls
- Social Media Manager: Manages organic content across platforms
- Content Strategist: Plans content calendars, scripts, brand positioning
- Video Editor: Edits reels, YouTube content, ad creatives
- Intern: Supports various departments

EVALUATION DIMENSIONS:
1. Technical Skills (role-specific): Can they actually do the job?
2. Communication: Clear, professional, good listener
3. Cultural Fit: Startup mindset, ownership, proactive
4. Problem Solving: Can they think on their feet?
5. Growth Potential: Willingness to learn, ambition
6. Domain Knowledge: Understanding of aesthetics/medical marketing
7. Portfolio/Track Record: Past results and work quality
8. Work Ethic: Reliability, deadline management, attention to detail

SCORING GUIDE:
- 9-10: Exceptional. Immediate hire recommendation.
- 7-8: Strong candidate. Minor gaps that can be trained.
- 5-6: Average. Significant development needed.
- 3-4: Below average. Major concerns.
- 1-2: Not suitable for the role.

When evaluating candidates, be specific with evidence. Reference what they said or showed.
When generating interview questions, make them practical and scenario-based.
When writing JDs, make them compelling but honest. No corporate fluff.

Always respond in valid JSON."""


async def evaluate_candidate(
    candidate_name: str,
    position_title: str,
    department: str,
    interview_notes: str,
    resume_summary: str = "",
    additional_context: str = "",
    learning_context: str = ""
) -> dict:
    """AI evaluation of a candidate based on interview notes and resume."""
    try:
        client = get_client()
        prompt = f"""Evaluate this candidate for an SBA agency role.

POSITION: {position_title} ({department})
CANDIDATE: {candidate_name}

RESUME SUMMARY:
{resume_summary or "Not provided"}

INTERVIEW NOTES:
{interview_notes}

ADDITIONAL CONTEXT:
{additional_context}

Return JSON:
{{
    "overall_score": 0,
    "recommendation": "strong_yes|yes|maybe|no|strong_no",
    "score_card": {{
        "technical_skills": {{"score": 0, "notes": "Evidence-based assessment"}},
        "communication": {{"score": 0, "notes": "Evidence-based assessment"}},
        "cultural_fit": {{"score": 0, "notes": "Evidence-based assessment"}},
        "problem_solving": {{"score": 0, "notes": "Evidence-based assessment"}},
        "growth_potential": {{"score": 0, "notes": "Evidence-based assessment"}},
        "domain_knowledge": {{"score": 0, "notes": "Evidence-based assessment"}},
        "portfolio_track_record": {{"score": 0, "notes": "Evidence-based assessment"}},
        "work_ethic": {{"score": 0, "notes": "Evidence-based assessment"}}
    }},
    "strengths": ["Specific strength 1", "Strength 2"],
    "concerns": ["Specific concern 1", "Concern 2"],
    "training_needs": ["What they would need to learn"],
    "suggested_next_steps": "What to do next with this candidate",
    "offer_recommendation": {{
        "should_offer": true,
        "suggested_role_level": "junior|mid|senior",
        "compensation_notes": "Any notes on compensation based on assessment"
    }}
}}"""

        system_prompt = HIRING_COACH_SYSTEM
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
        logger.error(f"Candidate evaluation failed: {e}")
        return {
            "overall_score": 0,
            "recommendation": "unable_to_evaluate",
            "score_card": {},
            "strengths": [],
            "concerns": ["AI evaluation failed"],
            "training_needs": [],
            "suggested_next_steps": "Evaluate manually",
        }


async def generate_interview_questions(
    position_title: str,
    department: str,
    requirements: list = None,
    interview_round: str = "screening",
    candidate_resume: str = "",
    learning_context: str = ""
) -> dict:
    """Generate tailored interview questions for a role."""
    try:
        client = get_client()
        prompt = f"""Generate interview questions for this SBA agency role.

POSITION: {position_title}
DEPARTMENT: {department}
REQUIREMENTS: {json.dumps(requirements or [])}
INTERVIEW ROUND: {interview_round}
CANDIDATE RESUME: {candidate_resume or "Not provided"}

Return JSON:
{{
    "questions": [
        {{
            "question": "The interview question",
            "purpose": "What this question evaluates",
            "good_answer_signals": ["What a good answer includes"],
            "red_flags": ["What to watch out for"],
            "follow_up": "Optional follow-up question"
        }}
    ],
    "scenario_questions": [
        {{
            "scenario": "Describe a situation...",
            "what_to_evaluate": "What you are looking for",
            "ideal_approach": "How a strong candidate would handle this"
        }}
    ],
    "practical_task": {{
        "task_description": "A hands-on task for the candidate",
        "evaluation_criteria": ["What to look for"],
        "time_limit": "Suggested time"
    }}
}}"""

        system_prompt = HIRING_COACH_SYSTEM
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
        logger.error(f"Interview question generation failed: {e}")
        return {"questions": [], "scenario_questions": [], "practical_task": {}}


async def generate_job_description(
    position_title: str,
    department: str,
    requirements: list = None,
    salary_range: str = "",
    additional_context: str = "",
    learning_context: str = ""
) -> dict:
    """Generate a compelling job description."""
    try:
        client = get_client()
        prompt = f"""Write a job description for this SBA agency role.

POSITION: {position_title}
DEPARTMENT: {department}
REQUIREMENTS: {json.dumps(requirements or [])}
SALARY RANGE: {salary_range or "Not specified"}
CONTEXT: {additional_context}

Make it compelling but honest. No corporate jargon.
Show the candidate what they will actually do day-to-day.
Highlight growth opportunity in a fast-growing agency.

Return JSON:
{{
    "title": "Job Title",
    "tagline": "One-line hook that sells the role",
    "about_company": "2-3 sentences about SBA",
    "role_overview": "What this person will do (3-4 sentences)",
    "responsibilities": ["Daily/weekly responsibilities"],
    "requirements": ["Must-have qualifications"],
    "nice_to_have": ["Bonus qualifications"],
    "what_you_get": ["Benefits and perks of the role"],
    "day_in_the_life": "Describe a typical day in 3-4 sentences",
    "growth_path": "Where this role leads in 1-2 years",
    "application_instructions": "How to apply"
}}"""

        system_prompt = HIRING_COACH_SYSTEM
        if learning_context:
            system_prompt += "\n" + learning_context

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"JD generation failed: {e}")
        return {"title": position_title, "responsibilities": [], "requirements": requirements or []}


async def ask_hiring_coach(
    question: str,
    context: dict = None,
    learning_context: str = ""
) -> dict:
    """General hiring Q&A."""
    try:
        client = get_client()
        context_text = f"""
QUESTION: {question}
CONTEXT: {json.dumps(context or {})}

Provide practical, actionable hiring advice based on SBA methodology."""

        system_prompt = HIRING_COACH_SYSTEM
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
        logger.error(f"Hiring coach Q&A failed: {e}")
        return {"answer": "Unable to respond. Check API configuration."}


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()
