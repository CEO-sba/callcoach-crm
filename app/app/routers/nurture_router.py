"""
CallCoach CRM - Nurture Sequence Router
Manage nurture sequences, steps, and enrollments.
"""
import logging
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity
from app.models_whatsapp import (
    NurtureSequence, NurtureStep, NurtureEnrollment, Lead
)
from app.schemas_whatsapp import (
    NurtureSequenceCreate, NurtureSequenceOut, NurtureSequenceDetail,
    NurtureStepCreate, NurtureStepOut,
    NurtureEnrollmentCreate, NurtureEnrollmentOut
)
from app.services.nurture_service import (
    enroll_lead_in_sequence, seed_templates_for_clinic, _build_enrollment_metadata
)
from app.services.nurture_templates import get_all_template_categories

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nurture", tags=["nurture"])


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------

@router.get("/sequences", response_model=list[NurtureSequenceOut])
def list_sequences(
    procedure_category: Optional[str] = None,
    is_template: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List nurture sequences for the clinic."""
    query = db.query(NurtureSequence).filter(
        NurtureSequence.clinic_id == current_user.clinic_id
    )
    if procedure_category:
        query = query.filter(NurtureSequence.procedure_category == procedure_category)
    if is_template is not None:
        query = query.filter(NurtureSequence.is_template == is_template)

    return query.order_by(NurtureSequence.created_at.desc()).all()


@router.get("/sequences/{sequence_id}", response_model=NurtureSequenceDetail)
def get_sequence(
    sequence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sequence with all steps."""
    seq = db.query(NurtureSequence).filter(
        NurtureSequence.id == sequence_id,
        NurtureSequence.clinic_id == current_user.clinic_id
    ).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return seq


@router.post("/sequences", response_model=NurtureSequenceOut)
def create_sequence(
    data: NurtureSequenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a custom nurture sequence."""
    sequence = NurtureSequence(
        clinic_id=current_user.clinic_id,
        name=data.name,
        description=data.description,
        procedure_category=data.procedure_category,
        trigger_type=data.trigger_type,
        is_template=False,
        total_steps=len(data.steps)
    )
    db.add(sequence)
    db.flush()

    for step_data in data.steps:
        step = NurtureStep(
            sequence_id=sequence.id,
            step_number=step_data.step_number,
            delay_hours=step_data.delay_hours,
            delay_type=step_data.delay_type,
            message_template=step_data.message_template,
            channel=step_data.channel,
            step_type=step_data.step_type,
            is_ai_generated=step_data.is_ai_generated
        )
        db.add(step)

    db.commit()
    db.refresh(sequence)
    log_activity(db, current_user.clinic_id, "nurture", "nurture_sequence_created",
                 {"name": data.name, "procedure": data.procedure_category, "steps": len(data.steps)},
                 current_user.email)
    return sequence


@router.put("/sequences/{sequence_id}/toggle")
def toggle_sequence(
    sequence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle sequence active/inactive."""
    seq = db.query(NurtureSequence).filter(
        NurtureSequence.id == sequence_id,
        NurtureSequence.clinic_id == current_user.clinic_id
    ).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")

    seq.is_active = not seq.is_active
    db.commit()
    return {"is_active": seq.is_active}


@router.delete("/sequences/{sequence_id}")
def delete_sequence(
    sequence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a sequence and its steps."""
    seq = db.query(NurtureSequence).filter(
        NurtureSequence.id == sequence_id,
        NurtureSequence.clinic_id == current_user.clinic_id
    ).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")

    # Cancel active enrollments
    db.query(NurtureEnrollment).filter(
        NurtureEnrollment.sequence_id == sequence_id,
        NurtureEnrollment.status == "active"
    ).update({"status": "cancelled"})

    # Delete steps
    db.query(NurtureStep).filter(NurtureStep.sequence_id == sequence_id).delete()
    db.delete(seq)
    db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Steps (edit individual steps in a sequence)
# ---------------------------------------------------------------------------

@router.put("/steps/{step_id}")
def update_step(
    step_id: str,
    data: NurtureStepCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a nurture step's message or timing."""
    step = db.query(NurtureStep).filter(NurtureStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    # Verify ownership
    seq = db.query(NurtureSequence).filter(
        NurtureSequence.id == step.sequence_id,
        NurtureSequence.clinic_id == current_user.clinic_id
    ).first()
    if not seq:
        raise HTTPException(status_code=403, detail="Not authorized")

    step.message_template = data.message_template
    step.delay_hours = data.delay_hours
    step.delay_type = data.delay_type
    step.channel = data.channel
    step.is_ai_generated = data.is_ai_generated

    db.commit()
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------

@router.get("/enrollments", response_model=list[NurtureEnrollmentOut])
def list_enrollments(
    status: Optional[str] = None,
    lead_id: Optional[str] = None,
    sequence_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List nurture enrollments."""
    query = db.query(NurtureEnrollment).filter(
        NurtureEnrollment.clinic_id == current_user.clinic_id
    )
    if status:
        query = query.filter(NurtureEnrollment.status == status)
    if lead_id:
        query = query.filter(NurtureEnrollment.lead_id == lead_id)
    if sequence_id:
        query = query.filter(NurtureEnrollment.sequence_id == sequence_id)

    return query.order_by(NurtureEnrollment.enrolled_at.desc()).offset(skip).limit(limit).all()


@router.post("/enrollments", response_model=NurtureEnrollmentOut)
def create_enrollment(
    data: NurtureEnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually enroll a lead in a nurture sequence."""
    lead = db.query(Lead).filter(
        Lead.id == data.lead_id,
        Lead.clinic_id == current_user.clinic_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    seq = db.query(NurtureSequence).filter(
        NurtureSequence.id == data.sequence_id,
        NurtureSequence.clinic_id == current_user.clinic_id
    ).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")

    metadata = data.metadata or _build_enrollment_metadata(db, lead)
    enrollment = enroll_lead_in_sequence(db, lead.id, seq.id, current_user.clinic_id, metadata)
    log_activity(db, current_user.clinic_id, "nurture", "lead_enrolled_in_sequence",
                 {"lead_id": data.lead_id, "lead_name": lead.name, "sequence_id": data.sequence_id,
                  "sequence_name": seq.name}, current_user.email)
    return enrollment


@router.put("/enrollments/{enrollment_id}/pause")
def pause_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pause a nurture enrollment."""
    enrollment = db.query(NurtureEnrollment).filter(
        NurtureEnrollment.id == enrollment_id,
        NurtureEnrollment.clinic_id == current_user.clinic_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.status = "paused"
    db.commit()
    return {"status": "paused"}


@router.put("/enrollments/{enrollment_id}/resume")
def resume_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resume a paused enrollment."""
    enrollment = db.query(NurtureEnrollment).filter(
        NurtureEnrollment.id == enrollment_id,
        NurtureEnrollment.clinic_id == current_user.clinic_id,
        NurtureEnrollment.status == "paused"
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found or not paused")

    enrollment.status = "active"
    enrollment.next_send_at = datetime.utcnow()  # Send next step immediately
    db.commit()
    return {"status": "active"}


@router.put("/enrollments/{enrollment_id}/cancel")
def cancel_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a nurture enrollment."""
    enrollment = db.query(NurtureEnrollment).filter(
        NurtureEnrollment.id == enrollment_id,
        NurtureEnrollment.clinic_id == current_user.clinic_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    enrollment.status = "cancelled"
    enrollment.next_send_at = None
    db.commit()
    return {"status": "cancelled"}


# ---------------------------------------------------------------------------
# Template Seeding
# ---------------------------------------------------------------------------

@router.post("/seed-templates")
def seed_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Seed pre-built nurture templates for the clinic. Safe to call multiple times."""
    seed_templates_for_clinic(db, current_user.clinic_id)
    count = db.query(NurtureSequence).filter(
        NurtureSequence.clinic_id == current_user.clinic_id,
        NurtureSequence.is_template == True
    ).count()
    log_activity(db, current_user.clinic_id, "nurture", "nurture_templates_seeded",
                 {"template_count": count}, current_user.email)
    return {"status": "seeded", "template_count": count}


@router.get("/template-categories")
def list_template_categories(current_user: User = Depends(get_current_user)):
    """List all available pre-built template categories."""
    return get_all_template_categories()


# Import datetime for resume endpoint
from datetime import datetime
import httpx, json
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL


# ---------------------------------------------------------------------------
# AI Nurture Sequence Generation (60 messages, 12 months)
# ---------------------------------------------------------------------------

@router.post("/generate-sequence")
async def generate_nurture_sequence(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a 60-message, 12-month nurture sequence for any procedure using AI.
    Saves directly as a new NurtureSequence with steps."""

    procedure_name = data.get("procedure_name", "").strip()
    procedure_description = data.get("procedure_description", "")
    clinic_name = data.get("clinic_name", "our clinic")
    doctor_name = data.get("doctor_name", "our doctor")
    tone = data.get("tone", "warm, professional, educational")
    language = data.get("language", "English")

    if not procedure_name:
        raise HTTPException(status_code=400, detail="procedure_name is required")

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="AI not configured. Add Anthropic API key in Settings.")

    # Build the prompt for 60-message generation
    prompt = f"""Generate a complete WhatsApp nurture sequence for a medical/aesthetic clinic.

PROCEDURE: {procedure_name}
DESCRIPTION: {procedure_description}
CLINIC NAME: {clinic_name}
DOCTOR NAME: {doctor_name}
TONE: {tone}
LANGUAGE: {language}

REQUIREMENTS:
- Generate EXACTLY 60 messages spread over 12 months (365 days)
- Messages should be sent via WhatsApp, so keep them concise (max 300 characters each)
- CRITICAL TONE RULE: Write like a real human, NOT like an AI. Messages should feel like they come from a friendly clinic coordinator, not a marketing bot. Use casual language, short sentences, natural pauses. Avoid overly polished or corporate-sounding phrases. No "I hope this message finds you well" or "We are delighted to inform you" type language. Think WhatsApp chat, not email newsletter.
- Use these placeholders in messages: {{name}}, {{procedure}}, {{clinic_name}}, {{doctor_name}}, {{booking_link}}, {{phone}}
- Message schedule distribution:
  * Month 1 (Days 1-30): 10 messages (high frequency for warm leads)
  * Month 2 (Days 31-60): 8 messages
  * Month 3 (Days 61-90): 7 messages
  * Months 4-6 (Days 91-180): 5 messages per month (15 total)
  * Months 7-9 (Days 181-270): 4 messages per month (12 total)
  * Months 10-12 (Days 271-365): 3 messages per month (8 total, rounding up)

MESSAGE CATEGORIES (mix throughout):
1. Educational: Explain the procedure, benefits, what to expect, recovery
2. Social proof: Mention success stories, patient satisfaction, before/after results
3. Objection handling: Address common fears (pain, cost, downtime, results)
4. Authority building: Doctor credentials, clinic expertise, certifications
5. Urgency/offers: Limited time offers, seasonal discounts, booking nudges
6. Check-in: Ask if they have questions, offer free consultations
7. Testimonial: Share patient experience stories
8. FAQ: Answer common questions about the procedure
9. Lifestyle: How the procedure improves quality of life
10. Re-engagement: For leads who haven't responded

Return a JSON array of 60 objects, each with:
- "step_number": integer (1-60)
- "delay_days": integer (days from enrollment, starting at 0 for first message)
- "message": the WhatsApp message text with placeholders
- "category": which category from the list above

Return ONLY the JSON array, no other text."""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 8000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )

        if resp.status_code != 200:
            logger.error(f"AI API error: {resp.status_code} {resp.text[:500]}")
            raise HTTPException(status_code=502, detail="AI generation failed")

        result = resp.json()
        ai_text = result["content"][0]["text"].strip()

        # Parse JSON from AI response (handle markdown code blocks)
        if ai_text.startswith("```"):
            ai_text = ai_text.split("```")[1]
            if ai_text.startswith("json"):
                ai_text = ai_text[4:]
        ai_text = ai_text.strip()

        steps_data = json.loads(ai_text)

        if not isinstance(steps_data, list) or len(steps_data) < 30:
            raise HTTPException(status_code=502, detail="AI generated insufficient messages")

        # Create the sequence
        category_slug = procedure_name.lower().replace(" ", "_").replace("-", "_")[:50]
        sequence = NurtureSequence(
            clinic_id=current_user.clinic_id,
            name=f"{procedure_name} - 12 Month Nurture ({len(steps_data)} msgs)",
            description=f"AI-generated 12-month nurture sequence for {procedure_name}. {len(steps_data)} WhatsApp messages covering education, social proof, objection handling, and re-engagement.",
            procedure_category=category_slug,
            trigger_type="manual",
            is_template=False,
            is_active=True,
            total_steps=len(steps_data)
        )
        db.add(sequence)
        db.flush()

        # Create steps
        for s in steps_data:
            step_num = s.get("step_number", 1)
            delay_days = s.get("delay_days", 0)
            delay_hours = delay_days * 24
            msg = s.get("message", "")

            # Determine display delay_type
            if delay_days == 0:
                delay_type = "hours"
            elif delay_days % 7 == 0:
                delay_type = "weeks"
            else:
                delay_type = "days"

            step = NurtureStep(
                sequence_id=sequence.id,
                step_number=step_num,
                delay_hours=delay_hours,
                delay_type=delay_type,
                message_template=msg,
                channel="whatsapp",
                step_type="message",
                is_ai_generated=True  # Allow further AI personalization at send time
            )
            db.add(step)

        db.commit()
        db.refresh(sequence)

        log_activity(db, current_user.clinic_id, "script_generation", "ai_nurture_sequence_generated",
                     {"procedure": procedure_name, "total_steps": sequence.total_steps,
                      "language": language, "tone": tone}, current_user.email)

        return {
            "status": "created",
            "sequence_id": str(sequence.id),
            "name": sequence.name,
            "total_steps": sequence.total_steps,
            "procedure_category": sequence.procedure_category,
            "message": f"Generated {sequence.total_steps} nurture messages for {procedure_name}"
        }

    except json.JSONDecodeError:
        logger.error("Failed to parse AI nurture response as JSON")
        raise HTTPException(status_code=502, detail="AI response format error. Try again.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Nurture generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
