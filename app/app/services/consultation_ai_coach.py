"""
CallCoach CRM - Consultation AI Coach (Anthropic Claude)

AI-powered analysis of patient consultations.
Analyzes transcriptions, provides recommendations, detects buying signals,
and coaches doctors/staff on consultation effectiveness.
"""
import json
import logging
from anthropic import Anthropic
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from app.services.prompt_quality import enhance_system_prompt

logger = logging.getLogger(__name__)


def get_client() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


CONSULTATION_ANALYZER_SYSTEM = """You are CallCoach Consultation AI, an expert in analyzing medical/aesthetic consultation conversations. You evaluate how effectively the doctor or consultant handles patient consultations.

SBA CONSULTATION FRAMEWORK:
A great consultation follows this structure:

1. WARM WELCOME (0-2 min): Greet by name, make comfortable, brief personal connection. The patient should feel like a person, not a case number.

2. PROBLEM UNDERSTANDING (2-8 min): Let the patient explain their concern fully. Ask clarifying questions. Understand their expectation. Questions: "What brings you in today?", "How long has this been a concern?", "What result are you hoping for?", "Have you tried anything before?"

3. CLINICAL ASSESSMENT (8-15 min): Doctor examines and explains findings. Use visual aids or before-after photos. Explain the medical perspective in simple terms. Connect the clinical finding to the patient's stated concern.

4. TREATMENT RECOMMENDATION (15-20 min): Recommend based on patient's specific situation. Explain: what the treatment involves, expected results, recovery time, number of sessions. Never just name a treatment. Always explain WHY this treatment for THIS patient.

5. OBJECTION HANDLING (if needed): Common objections: cost, fear, recovery time, "need to think about it". Handle with empathy: validate concern, provide information, offer flexible options. Never pressure.

6. CLOSING & NEXT STEPS (20-25 min): Clear next steps. Book the procedure or follow-up. Explain pre-procedure prep. Provide written summary if possible.

ANALYSIS DIMENSIONS:
- Patient Communication: How well were concerns understood and addressed
- Clinical Explanation: Clarity of medical explanations
- Treatment Matching: How well the recommendation fits patient needs
- Trust Building: Empathy, active listening, personal connection
- Conversion Effectiveness: How well the consultation leads toward booking
- Follow-up Planning: Clear next steps established

When scoring, use 0-100 scale. Be specific with evidence from the transcript.

Always respond in valid JSON."""


CONSULTATION_ANALYSIS_PROMPT = """Analyze this patient consultation transcript.

CONSULTATION DETAILS:
- Doctor/Consultant: {doctor_name}
- Patient: {patient_name}
- Duration: {duration} minutes

TRANSCRIPT:
{transcript}

Return this JSON:
{{
    "summary": "2-3 sentence summary of the consultation",
    "patient_concerns": ["Primary concern 1", "Concern 2"],
    "procedures_discussed": ["Procedure 1", "Procedure 2"],
    "recommended_treatment": "What was recommended",
    "sentiment": "positive|neutral|negative|mixed",
    "key_topics": ["topic1", "topic2"],
    "scores": {{
        "patient_communication": 0,
        "clinical_explanation": 0,
        "treatment_matching": 0,
        "trust_building": 0,
        "conversion_effectiveness": 0,
        "follow_up_planning": 0,
        "overall": 0
    }},
    "scoring_details": {{
        "patient_communication": "Evidence-based explanation",
        "clinical_explanation": "Evidence-based explanation",
        "treatment_matching": "Evidence-based explanation",
        "trust_building": "Evidence-based explanation",
        "conversion_effectiveness": "Evidence-based explanation",
        "follow_up_planning": "Evidence-based explanation"
    }},
    "buying_signals": [
        {{"signal": "What patient said", "strength": "strong|moderate|weak"}}
    ],
    "objections_raised": [
        {{"objection": "What they said", "handled": true, "handling_quality": "good|weak|missed"}}
    ],
    "what_went_well": ["Specific positive with quote evidence"],
    "improvements": [
        {{
            "area": "Area to improve",
            "current": "What happened in the consultation",
            "suggested": "What to do instead",
            "example_phrase": "Exact phrase to use next time"
        }}
    ],
    "follow_up_actions": [
        "Specific action item 1",
        "Action item 2"
    ],
    "patient_readiness": {{
        "level": "ready_to_book|considering|needs_more_info|unlikely",
        "next_best_action": "Specific next step to move patient forward"
    }}
}}"""


async def analyze_consultation(
    transcript: str,
    doctor_name: str = "Doctor",
    patient_name: str = "Patient",
    duration_minutes: int = 0,
    learning_context: str = ""
) -> dict:
    """Full AI analysis of a consultation transcript."""
    try:
        client = get_client()
        prompt = CONSULTATION_ANALYSIS_PROMPT.format(
            doctor_name=doctor_name,
            patient_name=patient_name,
            duration=duration_minutes,
            transcript=transcript[:8000]
        )

        system_prompt = CONSULTATION_ANALYZER_SYSTEM
        if learning_context:
            system_prompt += "\n" + learning_context

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4000,
            system=enhance_system_prompt(system_prompt),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json(response.content[0].text)
        return json.loads(result_text)

    except json.JSONDecodeError as e:
        logger.error(f"Consultation analysis JSON error: {e}")
        return _fallback_analysis()
    except Exception as e:
        logger.error(f"Consultation analysis failed: {e}")
        return _fallback_analysis()


async def ask_consultation_coach(
    question: str,
    transcript: str = "",
    analysis_summary: str = "",
    context: dict = None,
    learning_context: str = ""
) -> dict:
    """Interactive Q&A about a consultation."""
    try:
        client = get_client()
        context_text = f"""
CONSULTATION CONTEXT:
Summary: {analysis_summary}
{f'Transcript excerpt: {transcript[:3000]}' if transcript else ''}
Additional context: {json.dumps(context or {})}

USER QUESTION: {question}"""

        system_prompt = CONSULTATION_ANALYZER_SYSTEM
        if learning_context:
            system_prompt += "\n" + learning_context

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            system=enhance_system_prompt(system_prompt),
            messages=[{"role": "user", "content": context_text}]
        )
        return {"answer": response.content[0].text.strip()}

    except Exception as e:
        logger.error(f"Consultation coach Q&A failed: {e}")
        return {"answer": "Unable to respond. Check API configuration."}


async def generate_consultation_summary_for_patient(
    transcript: str,
    procedures_discussed: list,
    doctor_name: str = ""
) -> dict:
    """Generate a patient-friendly summary of the consultation."""
    try:
        client = get_client()
        prompt = f"""Create a patient-friendly summary of this consultation that can be sent to the patient after the visit.

DOCTOR: {doctor_name}
PROCEDURES DISCUSSED: {json.dumps(procedures_discussed)}

TRANSCRIPT:
{transcript[:5000]}

Return JSON:
{{
    "patient_summary": "A warm, clear summary written for the patient (3-5 paragraphs)",
    "procedures_explained": [
        {{"name": "Procedure", "simple_explanation": "What it is in patient-friendly language", "expected_result": "What to expect"}}
    ],
    "next_steps": ["Step 1 for patient", "Step 2"],
    "pre_procedure_notes": "Any preparation instructions if applicable"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            system="You are a medical communication specialist. Write clear, warm, patient-friendly summaries. Avoid medical jargon. Be reassuring but accurate.",
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Patient summary generation failed: {e}")
        return {"patient_summary": "Summary generation failed.", "next_steps": []}


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _fallback_analysis() -> dict:
    return {
        "summary": "Analysis could not be completed.",
        "patient_concerns": [],
        "procedures_discussed": [],
        "recommended_treatment": "",
        "sentiment": "neutral",
        "key_topics": [],
        "scores": {
            "patient_communication": 0, "clinical_explanation": 0,
            "treatment_matching": 0, "trust_building": 0,
            "conversion_effectiveness": 0, "follow_up_planning": 0, "overall": 0
        },
        "scoring_details": {},
        "buying_signals": [],
        "objections_raised": [],
        "what_went_well": [],
        "improvements": [],
        "follow_up_actions": ["Review consultation manually"],
        "patient_readiness": {"level": "unknown", "next_best_action": "Follow up with patient"}
    }
