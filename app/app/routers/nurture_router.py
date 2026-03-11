"""
CallCoach CRM - Nurture Sequence Router
Manage nurture sequences, steps, and enrollments.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
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
    return {"status": "seeded", "template_count": count}


@router.get("/template-categories")
def list_template_categories(current_user: User = Depends(get_current_user)):
    """List all available pre-built template categories."""
    return get_all_template_categories()


# Import datetime for resume endpoint
from datetime import datetime
