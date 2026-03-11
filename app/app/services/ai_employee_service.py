"""
CallCoach CRM - AI Employee Service
Claude-powered WhatsApp chatbot brain for clinic patient engagement.
"""
import json
import logging
from datetime import datetime
from anthropic import Anthropic
from sqlalchemy.orm import Session

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from app.models_whatsapp import (
    AIEmployee, WhatsAppConversation, WhatsAppMessage, Lead
)

logger = logging.getLogger(__name__)


def get_client() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_system_prompt(ai_employee: AIEmployee) -> str:
    """Build the system prompt from AI Employee configuration."""

    procedures_text = ""
    if ai_employee.procedures_offered:
        procedures_lines = []
        for proc in ai_employee.procedures_offered:
            line = f"- {proc.get('name', 'Unknown')}"
            if proc.get('description'):
                line += f": {proc['description']}"
            if proc.get('price_range'):
                line += f" (Price range: {proc['price_range']})"
            if proc.get('duration'):
                line += f" [Duration: {proc['duration']}]"
            procedures_lines.append(line)
        procedures_text = "\n".join(procedures_lines)

    hours_text = ""
    if ai_employee.business_hours:
        bh = ai_employee.business_hours
        day_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
        days = [day_map.get(d, str(d)) for d in bh.get("days", [])]
        hours_text = f"{bh.get('start', '09:00')} to {bh.get('end', '19:00')}, {', '.join(days)}"

    # Choose tone instruction
    tone_instructions = {
        "professional": "Maintain a professional, respectful tone. Be courteous and informative.",
        "friendly": "Be warm and friendly, like talking to a trusted friend. Use casual but respectful language.",
        "warm": "Be empathetic and caring. Show genuine concern for the patient's needs and comfort."
    }
    tone = tone_instructions.get(ai_employee.tone, tone_instructions["professional"])

    # Language instruction
    lang_instructions = {
        "english": "Respond in English only.",
        "hindi": "Respond in Hindi only. Use Devanagari script.",
        "hinglish": "Respond in Hinglish (a natural mix of Hindi and English, written in Roman script). This is how people actually talk in India. Example: 'Aapko koi bhi concern ho toh feel free to ask. Humari team aapki help ke liye ready hai.'"
    }
    lang = lang_instructions.get(ai_employee.language, lang_instructions["english"])

    doctor_info = f"\nDoctor: {ai_employee.doctor_name}" if ai_employee.doctor_name else ""

    system_prompt = f"""You are {ai_employee.name}, the AI assistant for a medical/aesthetic clinic. You handle WhatsApp conversations with potential patients.

CLINIC INFORMATION:
{doctor_info}
Address: {ai_employee.clinic_address or 'Not specified'}
Phone: {ai_employee.clinic_phone or 'Not specified'}
Booking Link: {ai_employee.booking_link or 'Not available'}
Business Hours: {hours_text or 'Mon-Sat 9:00 AM to 7:00 PM'}

PROCEDURES OFFERED:
{procedures_text or 'General consultations available. Ask the team for specific procedure details.'}

YOUR BEHAVIOR RULES:
1. {tone}
2. {lang}
3. Your primary goal is to answer patient questions and guide them toward booking a consultation.
4. Never diagnose conditions. Always say the doctor will assess during consultation.
5. When discussing prices, give ranges if available. Never guarantee exact prices without consultation.
6. If a patient asks something you do not know, say: "That's a great question! Let me check with the team and get back to you. In the meantime, would you like to book a consultation with the doctor?"
7. Never be pushy. If a patient says no or shows disinterest, respect it gracefully.
8. If the conversation gets complex, medical, or the patient seems upset, say: "I want to make sure you get the best help. Let me connect you with our team. They'll reach out shortly."
9. Keep messages concise. WhatsApp is not email. Use short paragraphs, max 3-4 lines per message.
10. Use the patient's name when you know it. It builds trust.
11. Always try to end with a question or clear next step to keep the conversation moving.
12. For price inquiries without a specific procedure: ask what they're looking to address first.
13. If they share images or documents, acknowledge them and recommend an in-person consultation for proper assessment.

CONVERSATION FLOW:
- First message: Greet warmly, acknowledge their interest, ask how you can help.
- Understanding phase: Ask about their concerns, what they're looking to address.
- Information phase: Share relevant procedure info, pricing ranges, doctor credentials.
- Booking phase: Guide toward scheduling a consultation. Share booking link if available.
- Follow up: If they hesitate, offer to answer more questions and gently circle back to booking.

IMPORTANT:
- You are NOT a doctor. Never provide medical advice or diagnosis.
- Be honest about what you know and don't know.
- If after hours, acknowledge the message and let them know the team will respond during business hours.
- Keep track of context from previous messages in the conversation."""

    # If user has customized the system prompt, use that instead
    if ai_employee.system_prompt:
        system_prompt = ai_employee.system_prompt

    return system_prompt


def _is_within_business_hours(ai_employee: AIEmployee) -> bool:
    """Check if current time is within configured business hours."""
    if not ai_employee.business_hours:
        return True  # Default: always available

    now = datetime.utcnow()  # TODO: timezone support
    bh = ai_employee.business_hours
    current_day = now.isoweekday()  # Mon=1, Sun=7
    current_time = now.strftime("%H:%M")

    days = bh.get("days", [1, 2, 3, 4, 5, 6])
    start = bh.get("start", "09:00")
    end = bh.get("end", "19:00")

    if current_day not in days:
        return False

    if current_time < start or current_time > end:
        return False

    return True


async def generate_ai_reply(
    db: Session,
    clinic_id: str,
    conversation_id: str,
    incoming_message: str
) -> str:
    """Generate an AI reply for a WhatsApp conversation."""

    if not ANTHROPIC_API_KEY:
        logger.warning("Anthropic API key not configured, skipping AI reply")
        return None

    # Get AI Employee config
    ai_employee = db.query(AIEmployee).filter(
        AIEmployee.clinic_id == clinic_id
    ).first()

    if not ai_employee or not ai_employee.auto_reply_enabled:
        return None

    # Check business hours - send after hours message if outside
    if not _is_within_business_hours(ai_employee):
        return ai_employee.after_hours_message

    # Get conversation history (last 20 messages for context)
    conversation = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conversation_id
    ).first()

    if not conversation:
        return None

    messages = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.conversation_id == conversation_id
    ).order_by(WhatsAppMessage.created_at.asc()).limit(20).all()

    # Check if this is the first message (send greeting)
    if len(messages) <= 1:
        # Build a greeting that acknowledges their message
        contact_name = conversation.contact_name or ""
        greeting_context = f"The patient's name is {contact_name}. " if contact_name else ""
        greeting_context += f"Their first message is: \"{incoming_message}\""

        system_prompt = _build_system_prompt(ai_employee)
        system_prompt += f"\n\nCONTEXT: This is the very first message from this patient. {greeting_context}. Greet them warmly and respond to what they said."

        try:
            client = get_client()
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=300,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": incoming_message}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Claude API error (greeting): {e}")
            return ai_employee.greeting_message

    # Build conversation history for Claude
    system_prompt = _build_system_prompt(ai_employee)

    # Add context about the patient
    lead = conversation.lead
    if lead:
        lead_context_parts = []
        if lead.name:
            lead_context_parts.append(f"Patient name: {lead.name}")
        if lead.procedure_interest:
            lead_context_parts.append(f"Interested in: {lead.procedure_interest}")
        if lead.source:
            lead_context_parts.append(f"Source: {lead.source}")
        if lead_context_parts:
            system_prompt += f"\n\nPATIENT CONTEXT:\n" + "\n".join(lead_context_parts)

    claude_messages = []
    for msg in messages:
        role = "user" if msg.direction == "inbound" else "assistant"
        content = msg.content or f"[{msg.message_type} message]"
        claude_messages.append({"role": role, "content": content})

    # Ensure the conversation alternates correctly for Claude
    # Remove consecutive same-role messages by combining them
    cleaned_messages = []
    for msg in claude_messages:
        if cleaned_messages and cleaned_messages[-1]["role"] == msg["role"]:
            cleaned_messages[-1]["content"] += "\n" + msg["content"]
        else:
            cleaned_messages.append(msg)

    # Ensure last message is from user
    if not cleaned_messages or cleaned_messages[-1]["role"] != "user":
        cleaned_messages.append({"role": "user", "content": incoming_message})

    try:
        client = get_client()
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            system=system_prompt,
            messages=cleaned_messages
        )
        reply = response.content[0].text.strip()

        # Update lead's procedure interest if we can detect it
        _maybe_update_lead_interest(db, lead, incoming_message, reply)

        return reply

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return None


def _maybe_update_lead_interest(db: Session, lead: Lead, patient_msg: str, ai_reply: str):
    """Try to detect procedure interest from conversation and update lead."""
    if not lead or lead.procedure_interest:
        return  # Already has a procedure interest set

    # Simple keyword matching for procedure detection
    procedure_keywords = {
        "hair transplant": ["hair transplant", "hair loss", "hair fall", "bald", "fue", "fut", "hair restoration"],
        "rhinoplasty": ["rhinoplasty", "nose job", "nose surgery", "nose shape", "nose correction"],
        "botox": ["botox", "wrinkle", "forehead lines", "crow feet", "anti aging"],
        "fillers": ["filler", "lip filler", "cheek filler", "lip augmentation", "volume loss"],
        "liposuction": ["liposuction", "lipo", "fat removal", "body fat", "stubborn fat"],
        "facelift": ["facelift", "face lift", "face sagging", "jowl", "face tightening"],
        "laser hair removal": ["laser hair", "unwanted hair", "hair removal", "laser treatment"],
        "chemical peel": ["chemical peel", "peel", "skin peel", "dark spots treatment"],
        "prp": ["prp", "platelet rich", "vampire facial", "prp hair", "prp face"],
        "microneedling": ["microneedling", "micro needling", "derma pen", "collagen induction"],
        "skin tightening": ["skin tightening", "loose skin", "saggy skin", "skin laxity"],
        "acne treatment": ["acne", "pimple", "breakout", "acne scar"],
        "pigmentation": ["pigmentation", "dark spots", "melasma", "hyperpigmentation", "uneven skin"],
        "hydrafacial": ["hydrafacial", "hydra facial", "deep cleansing facial"],
        "tattoo removal": ["tattoo removal", "remove tattoo", "laser tattoo"],
        "breast augmentation": ["breast augmentation", "breast implant", "breast surgery", "breast enlargement"],
        "tummy tuck": ["tummy tuck", "abdominoplasty", "stomach surgery"],
        "dental veneers": ["veneer", "smile makeover", "teeth whitening", "dental aesthetic"],
    }

    msg_lower = patient_msg.lower()
    for procedure, keywords in procedure_keywords.items():
        for kw in keywords:
            if kw in msg_lower:
                lead.procedure_interest = procedure
                db.commit()
                return
