"""
CallCoach CRM - Leads Router
Lead management, form webhook, and lead scoring.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_whatsapp import Lead, ClinicApiKey, NurtureSequence
from app.schemas_whatsapp import LeadCreate, LeadUpdate, LeadOut, NurtureEnrollmentCreate
from app.services.lead_scoring import calculate_lead_score, update_lead_score
from app.services.nurture_service import auto_enroll_lead, enroll_lead_in_sequence, _build_enrollment_metadata

from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leads", tags=["leads"])


# ---------------------------------------------------------------------------
# Public Webhook (for form submissions from landing pages)
# ---------------------------------------------------------------------------

@router.post("/webhook/{api_key}")
async def lead_webhook(api_key: str, request: Request, db: Session = Depends(get_db)):
    """
    Public webhook for form submissions.
    Landing pages POST form data here with UTM parameters.
    Each clinic has a unique api_key.
    """
    # Validate API key
    key_record = db.query(ClinicApiKey).filter(
        ClinicApiKey.api_key == api_key,
        ClinicApiKey.is_active == True
    ).first()

    if not key_record:
        raise HTTPException(status_code=403, detail="Invalid API key")

    clinic_id = key_record.clinic_id

    # Parse form data (support both JSON and form-encoded)
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    # Extract standard fields
    name = data.get("name", data.get("full_name", data.get("first_name", "")))
    phone = data.get("phone", data.get("mobile", data.get("phone_number", "")))
    email = data.get("email", data.get("email_address", ""))

    # UTM tracking
    utm_source = data.get("utm_source", data.get("source", ""))
    utm_medium = data.get("utm_medium", data.get("medium", ""))
    utm_campaign = data.get("utm_campaign", data.get("campaign", ""))
    utm_content = data.get("utm_content", "")

    # Procedure interest
    procedure = data.get("procedure", data.get("treatment", data.get("service", data.get("interest", ""))))

    # Determine source
    source = "form_google"
    if utm_source:
        source_lower = utm_source.lower()
        if "meta" in source_lower or "facebook" in source_lower or "instagram" in source_lower:
            source = "form_meta"
        elif "google" in source_lower:
            source = "form_google"
        else:
            source = f"form_{source_lower}"

    # Check for duplicate (same phone or email in same clinic)
    existing_lead = None
    if phone:
        from app.services.whatsapp_service import normalize_phone
        phone = normalize_phone(phone)
        existing_lead = db.query(Lead).filter(
            Lead.clinic_id == clinic_id,
            Lead.phone == phone
        ).first()

    if not existing_lead and email:
        existing_lead = db.query(Lead).filter(
            Lead.clinic_id == clinic_id,
            Lead.email == email
        ).first()

    if existing_lead:
        # Update existing lead with new form data
        if name and not existing_lead.name:
            existing_lead.name = name
        if email and not existing_lead.email:
            existing_lead.email = email
        if procedure and not existing_lead.procedure_interest:
            existing_lead.procedure_interest = procedure
        existing_lead.form_data = data
        existing_lead.updated_at = datetime.utcnow()
        lead = existing_lead
    else:
        # Create new lead
        lead = Lead(
            clinic_id=clinic_id,
            name=name,
            phone=phone,
            email=email,
            source=source,
            campaign_name=utm_campaign,
            campaign_source=utm_source,
            campaign_medium=utm_medium,
            campaign_content=utm_content,
            procedure_interest=procedure,
            form_data=data
        )
        db.add(lead)

    db.flush()

    # Calculate lead score
    lead.lead_score = calculate_lead_score(db, lead)
    db.commit()

    # Auto-enroll in nurture sequence
    try:
        auto_enroll_lead(db, lead)
    except Exception as e:
        logger.error(f"Auto-enrollment failed for lead {lead.id}: {e}")

    try:
        log_activity(db, clinic_id, "lead", "lead_captured_webhook",
                     {"name": name, "phone": phone, "source": source,
                      "procedure": procedure, "campaign": utm_campaign,
                      "is_duplicate": bool(existing_lead), "score": lead.lead_score})
    except Exception:
        pass

    return {
        "status": "success",
        "lead_id": lead.id,
        "lead_score": lead.lead_score,
        "message": "Lead captured successfully"
    }


# ---------------------------------------------------------------------------
# Authenticated Lead Management
# ---------------------------------------------------------------------------

@router.get("", response_model=list[LeadOut])
def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[int] = None,
    procedure: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List leads with filters."""
    query = db.query(Lead).filter(Lead.clinic_id == current_user.clinic_id)

    if status:
        query = query.filter(Lead.status == status)
    if source:
        query = query.filter(Lead.source == source)
    if min_score is not None:
        query = query.filter(Lead.lead_score >= min_score)
    if procedure:
        query = query.filter(Lead.procedure_interest.ilike(f"%{procedure}%"))
    if search:
        query = query.filter(
            (Lead.name.ilike(f"%{search}%")) |
            (Lead.phone.ilike(f"%{search}%")) |
            (Lead.email.ilike(f"%{search}%"))
        )

    return query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/stats")
def lead_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get lead statistics for dashboard."""
    clinic_id = current_user.clinic_id

    total = db.query(Lead).filter(Lead.clinic_id == clinic_id).count()
    new = db.query(Lead).filter(Lead.clinic_id == clinic_id, Lead.status == "new").count()
    contacted = db.query(Lead).filter(Lead.clinic_id == clinic_id, Lead.status == "contacted").count()
    qualified = db.query(Lead).filter(Lead.clinic_id == clinic_id, Lead.status == "qualified").count()
    booked = db.query(Lead).filter(Lead.clinic_id == clinic_id, Lead.status == "consultation_booked").count()
    converted = db.query(Lead).filter(Lead.clinic_id == clinic_id, Lead.status == "converted").count()
    lost = db.query(Lead).filter(Lead.clinic_id == clinic_id, Lead.status == "lost").count()

    # Average score
    from sqlalchemy import func
    avg_score = db.query(func.avg(Lead.lead_score)).filter(
        Lead.clinic_id == clinic_id
    ).scalar() or 0

    # Source breakdown
    sources = db.query(Lead.source, func.count(Lead.id)).filter(
        Lead.clinic_id == clinic_id
    ).group_by(Lead.source).all()

    return {
        "total": total,
        "by_status": {
            "new": new,
            "contacted": contacted,
            "qualified": qualified,
            "consultation_booked": booked,
            "converted": converted,
            "lost": lost
        },
        "average_score": round(avg_score, 1),
        "by_source": {source: count for source, count in sources}
    }


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get lead details."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.clinic_id == current_user.clinic_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: str,
    data: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update lead details."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.clinic_id == current_user.clinic_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    lead.updated_at = datetime.utcnow()

    # Recalculate score after update
    lead.lead_score = calculate_lead_score(db, lead)
    db.commit()
    db.refresh(lead)
    log_activity(db, current_user.clinic_id, "lead", "lead_updated",
                 {"lead_id": lead_id, "fields_updated": list(update_data.keys()),
                  "new_score": lead.lead_score},
                 current_user.email, related_id=lead_id, related_type="lead")
    return lead


@router.post("/{lead_id}/enroll")
def enroll_in_sequence(
    lead_id: str,
    data: NurtureEnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually enroll a lead in a nurture sequence."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.clinic_id == current_user.clinic_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    seq = db.query(NurtureSequence).filter(
        NurtureSequence.id == data.sequence_id
    ).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")

    metadata = data.metadata or _build_enrollment_metadata(db, lead)
    enrollment = enroll_lead_in_sequence(db, lead.id, seq.id, current_user.clinic_id, metadata)
    log_activity(db, current_user.clinic_id, "nurture", "lead_enrolled_in_sequence",
                 {"lead_id": lead_id, "lead_name": lead.name,
                  "sequence_id": str(data.sequence_id)},
                 current_user.email, related_id=enrollment.id, related_type="enrollment")
    return {"status": "enrolled", "enrollment_id": enrollment.id}


@router.post("/{lead_id}/rescore")
def rescore_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recalculate lead score."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.clinic_id == current_user.clinic_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    new_score = update_lead_score(db, lead)
    log_activity(db, current_user.clinic_id, "lead", "lead_rescored",
                 {"lead_id": lead_id, "new_score": new_score},
                 current_user.email, related_id=lead_id, related_type="lead")
    return {"lead_id": lead.id, "new_score": new_score}


# ---------------------------------------------------------------------------
# API Key Management
# ---------------------------------------------------------------------------

@router.get("/api-key/current")
def get_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get or create the clinic's API key for webhooks."""
    key = db.query(ClinicApiKey).filter(
        ClinicApiKey.clinic_id == current_user.clinic_id
    ).first()

    if not key:
        key = ClinicApiKey(clinic_id=current_user.clinic_id)
        db.add(key)
        db.commit()
        db.refresh(key)

    return {
        "api_key": key.api_key,
        "webhook_url": f"/api/leads/webhook/{key.api_key}",
        "is_active": key.is_active
    }


@router.post("/api-key/regenerate")
def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate the clinic's API key."""
    import secrets
    key = db.query(ClinicApiKey).filter(
        ClinicApiKey.clinic_id == current_user.clinic_id
    ).first()

    if key:
        key.api_key = secrets.token_urlsafe(32)
    else:
        key = ClinicApiKey(clinic_id=current_user.clinic_id)
        db.add(key)

    db.commit()
    db.refresh(key)

    return {
        "api_key": key.api_key,
        "webhook_url": f"/api/leads/webhook/{key.api_key}",
        "is_active": key.is_active
    }
