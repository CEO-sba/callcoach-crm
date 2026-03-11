"""
CallCoach CRM - Nurture Automation Service
Handles enrolling leads in sequences, processing scheduled sends, and managing the nurture engine.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models_whatsapp import (
    Lead, NurtureSequence, NurtureStep, NurtureEnrollment,
    WhatsAppConfig, WhatsAppConversation, WhatsAppMessage
)
from app.services.whatsapp_service import send_text_message
from app.services.nurture_templates import NURTURE_TEMPLATES

logger = logging.getLogger(__name__)


def enroll_lead_in_sequence(
    db: Session,
    lead_id: str,
    sequence_id: str,
    clinic_id: str,
    metadata: Optional[dict] = None
) -> NurtureEnrollment:
    """Enroll a lead in a nurture sequence."""

    # Check if already enrolled in this sequence
    existing = db.query(NurtureEnrollment).filter(
        NurtureEnrollment.lead_id == lead_id,
        NurtureEnrollment.sequence_id == sequence_id,
        NurtureEnrollment.status.in_(["active", "paused"])
    ).first()

    if existing:
        logger.info(f"Lead {lead_id} already enrolled in sequence {sequence_id}")
        return existing

    # Get first step to calculate first send time
    first_step = db.query(NurtureStep).filter(
        NurtureStep.sequence_id == sequence_id,
        NurtureStep.step_number == 1
    ).first()

    next_send = datetime.utcnow()
    if first_step and first_step.delay_hours > 0:
        next_send = datetime.utcnow() + timedelta(hours=first_step.delay_hours)

    enrollment = NurtureEnrollment(
        lead_id=lead_id,
        sequence_id=sequence_id,
        clinic_id=clinic_id,
        current_step=0,
        status="active",
        next_send_at=next_send,
        metadata=metadata or {}
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    logger.info(f"Lead {lead_id} enrolled in sequence {sequence_id}, first send at {next_send}")
    return enrollment


def _fill_template(template: str, metadata: dict) -> str:
    """Replace placeholders in message template with actual values."""
    result = template
    for key, value in metadata.items():
        result = result.replace(f"{{{key}}}", str(value) if value else "")
    return result


async def process_nurture_sends(db: Session):
    """Process all pending nurture sends. Called by the scheduler every 5 minutes."""

    now = datetime.utcnow()
    pending = db.query(NurtureEnrollment).filter(
        NurtureEnrollment.status == "active",
        NurtureEnrollment.next_send_at <= now
    ).limit(50).all()  # Process 50 at a time to avoid overload

    if not pending:
        return

    logger.info(f"Processing {len(pending)} nurture sends")

    for enrollment in pending:
        try:
            await _process_single_enrollment(db, enrollment)
        except Exception as e:
            logger.error(f"Error processing enrollment {enrollment.id}: {e}")


async def _process_single_enrollment(db: Session, enrollment: NurtureEnrollment):
    """Process a single nurture enrollment - send the next message."""

    # Get the next step
    next_step_number = enrollment.current_step + 1
    step = db.query(NurtureStep).filter(
        NurtureStep.sequence_id == enrollment.sequence_id,
        NurtureStep.step_number == next_step_number
    ).first()

    if not step:
        # No more steps, complete the enrollment
        enrollment.status = "completed"
        enrollment.completed_at = datetime.utcnow()
        enrollment.next_send_at = None
        db.commit()
        logger.info(f"Enrollment {enrollment.id} completed (no more steps)")
        return

    # Get lead and clinic WhatsApp config
    lead = db.query(Lead).filter(Lead.id == enrollment.lead_id).first()
    if not lead or not lead.phone:
        logger.warning(f"Lead {enrollment.lead_id} has no phone, skipping")
        return

    config = db.query(WhatsAppConfig).filter(
        WhatsAppConfig.clinic_id == enrollment.clinic_id,
        WhatsAppConfig.is_active == True
    ).first()

    if not config:
        logger.warning(f"No active WhatsApp config for clinic {enrollment.clinic_id}")
        return

    # Prepare message
    message_text = _fill_template(step.message_template, enrollment.metadata or {})

    # If AI-generated, personalize with Claude
    if step.is_ai_generated:
        message_text = await _ai_personalize_message(db, enrollment, message_text, lead)

    # Send via WhatsApp
    if step.channel == "whatsapp":
        wa_msg_id = await send_text_message(
            config.phone_number_id,
            config.access_token,
            lead.phone,
            message_text
        )

        # Save the message in the conversation
        conversation = db.query(WhatsAppConversation).filter(
            WhatsAppConversation.clinic_id == enrollment.clinic_id,
            WhatsAppConversation.wa_phone == lead.phone
        ).first()

        if conversation:
            msg = WhatsAppMessage(
                conversation_id=conversation.id,
                direction="outbound",
                message_type="text",
                content=message_text,
                wa_message_id=wa_msg_id,
                sender_type="ai_employee",
                status="sent" if wa_msg_id else "failed"
            )
            db.add(msg)
            conversation.last_message_at = datetime.utcnow()
            conversation.last_message_preview = message_text[:200]

        if wa_msg_id:
            logger.info(f"Nurture message sent to {lead.phone}: step {next_step_number}")
        else:
            logger.error(f"Failed to send nurture message to {lead.phone}")

    # Update enrollment: move to next step
    enrollment.current_step = next_step_number

    # Calculate next send time
    next_next_step = db.query(NurtureStep).filter(
        NurtureStep.sequence_id == enrollment.sequence_id,
        NurtureStep.step_number == next_step_number + 1
    ).first()

    if next_next_step:
        enrollment.next_send_at = datetime.utcnow() + timedelta(hours=next_next_step.delay_hours)
    else:
        # This was the last step
        enrollment.status = "completed"
        enrollment.completed_at = datetime.utcnow()
        enrollment.next_send_at = None

    db.commit()


async def _ai_personalize_message(
    db: Session,
    enrollment: NurtureEnrollment,
    base_message: str,
    lead: Lead
) -> str:
    """Use Claude to personalize a nurture message based on conversation history."""
    try:
        from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
        if not ANTHROPIC_API_KEY:
            return base_message

        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Get recent conversation history
        conversation = db.query(WhatsAppConversation).filter(
            WhatsAppConversation.clinic_id == enrollment.clinic_id,
            WhatsAppConversation.wa_phone == lead.phone
        ).first()

        context = ""
        if conversation:
            recent_msgs = db.query(WhatsAppMessage).filter(
                WhatsAppMessage.conversation_id == conversation.id
            ).order_by(WhatsAppMessage.created_at.desc()).limit(10).all()

            if recent_msgs:
                context = "Recent conversation:\n"
                for msg in reversed(recent_msgs):
                    direction = "Patient" if msg.direction == "inbound" else "Us"
                    context += f"{direction}: {msg.content}\n"

        prompt = f"""Personalize this nurture follow-up message for a patient.

Base message:
{base_message}

Patient name: {lead.name or 'there'}
Procedure interest: {lead.procedure_interest or 'not specified'}

{context}

Rules:
- Keep the same intent and structure as the base message
- Make it feel personal based on the conversation history
- Keep it concise (WhatsApp, not email)
- Don't be pushy
- Maintain a warm, professional tone
- Return ONLY the personalized message, nothing else"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"AI personalization failed: {e}")
        return base_message


def seed_templates_for_clinic(db: Session, clinic_id: str, clinic_name: str = "", doctor_name: str = ""):
    """Create nurture sequences from all pre-built templates for a clinic."""

    for template_key, template_data in NURTURE_TEMPLATES.items():
        # Check if already seeded
        existing = db.query(NurtureSequence).filter(
            NurtureSequence.clinic_id == clinic_id,
            NurtureSequence.procedure_category == template_data["procedure_category"],
            NurtureSequence.is_template == True
        ).first()

        if existing:
            continue

        # Create sequence
        sequence = NurtureSequence(
            clinic_id=clinic_id,
            name=template_data["name"],
            description=template_data["description"],
            procedure_category=template_data["procedure_category"],
            trigger_type="manual",
            is_active=True,
            is_template=True,
            total_steps=len(template_data["steps"])
        )
        db.add(sequence)
        db.flush()

        # Create steps
        for step_data in template_data["steps"]:
            step = NurtureStep(
                sequence_id=sequence.id,
                step_number=step_data["step_number"],
                delay_hours=step_data["delay_hours"],
                delay_type=step_data["delay_type"],
                message_template=step_data["message_template"],
                channel="whatsapp",
                step_type="message",
                is_ai_generated=step_data.get("is_ai_generated", False)
            )
            db.add(step)

    db.commit()
    logger.info(f"Seeded nurture templates for clinic {clinic_id}")


def auto_enroll_lead(db: Session, lead: Lead):
    """Auto-enroll a lead in appropriate nurture sequence based on source and procedure interest."""

    if not lead.procedure_interest:
        # Enroll in general consultation sequence
        general_seq = db.query(NurtureSequence).filter(
            NurtureSequence.clinic_id == lead.clinic_id,
            NurtureSequence.procedure_category == "general",
            NurtureSequence.is_active == True
        ).first()

        if general_seq:
            metadata = _build_enrollment_metadata(db, lead)
            enroll_lead_in_sequence(db, lead.id, general_seq.id, lead.clinic_id, metadata)
        return

    # Find matching procedure sequence
    # Map common procedure interests to template categories
    procedure_mapping = {
        "hair transplant": "hair_transplant_fue",
        "hair transplant fue": "hair_transplant_fue",
        "hair transplant fut": "hair_transplant_fut",
        "prp": "prp_hair",
        "prp hair": "prp_hair",
        "scalp micropigmentation": "scalp_micropigmentation",
        "rhinoplasty": "rhinoplasty",
        "nose job": "rhinoplasty",
        "facelift": "facelift",
        "blepharoplasty": "blepharoplasty",
        "eyelid surgery": "blepharoplasty",
        "liposuction": "liposuction",
        "breast augmentation": "breast_augmentation",
        "tummy tuck": "tummy_tuck",
        "botox": "botox",
        "fillers": "fillers",
        "chemical peel": "chemical_peel",
        "microneedling": "microneedling",
        "laser hair removal": "laser_hair_removal",
        "acne treatment": "acne_treatment",
        "acne": "acne_treatment",
        "pigmentation": "pigmentation_treatment",
        "pigmentation treatment": "pigmentation_treatment",
        "melasma": "pigmentation_treatment",
        "hydrafacial": "hydrafacial",
        "anti aging": "anti_aging",
        "anti-aging": "anti_aging",
        "tattoo removal": "tattoo_removal",
        "scar treatment": "scar_treatment",
        "coolsculpting": "coolsculpting",
        "skin tightening": "skin_tightening",
        "smile makeover": "smile_makeover",
        "dental veneers": "smile_makeover",
        "teeth whitening": "teeth_whitening",
    }

    category = procedure_mapping.get(lead.procedure_interest.lower(), "general")

    sequence = db.query(NurtureSequence).filter(
        NurtureSequence.clinic_id == lead.clinic_id,
        NurtureSequence.procedure_category == category,
        NurtureSequence.is_active == True
    ).first()

    if not sequence:
        # Fall back to general
        sequence = db.query(NurtureSequence).filter(
            NurtureSequence.clinic_id == lead.clinic_id,
            NurtureSequence.procedure_category == "general",
            NurtureSequence.is_active == True
        ).first()

    if sequence:
        metadata = _build_enrollment_metadata(db, lead)
        enroll_lead_in_sequence(db, lead.id, sequence.id, lead.clinic_id, metadata)


def _build_enrollment_metadata(db: Session, lead: Lead) -> dict:
    """Build metadata dict for nurture message personalization."""
    from app.models import Clinic
    from app.models_whatsapp import AIEmployee

    clinic = db.query(Clinic).filter(Clinic.id == lead.clinic_id).first()
    ai_employee = db.query(AIEmployee).filter(AIEmployee.clinic_id == lead.clinic_id).first()

    metadata = {
        "name": lead.name or "there",
        "procedure": lead.procedure_interest or "your concern",
        "clinic_name": clinic.name if clinic else "our clinic",
        "doctor_name": ai_employee.doctor_name if ai_employee and ai_employee.doctor_name else "our doctor",
        "booking_link": ai_employee.booking_link if ai_employee and ai_employee.booking_link else "",
        "phone": ai_employee.clinic_phone if ai_employee and ai_employee.clinic_phone else (clinic.phone if clinic else ""),
    }
    return metadata
