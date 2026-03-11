"""
CallCoach CRM - Meta Integration Router
Handles Meta OAuth, lead form webhook, and social account connections.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_whatsapp import MetaConfig, Lead, SocialAccount
from app.schemas_whatsapp import MetaConnectRequest, MetaConfigOut
from app.services.lead_scoring import calculate_lead_score
from app.services.nurture_service import auto_enroll_lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meta", tags=["meta"])


# ---------------------------------------------------------------------------
# Meta Connection
# ---------------------------------------------------------------------------

@router.get("/config", response_model=Optional[MetaConfigOut])
def get_meta_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Meta integration config."""
    config = db.query(MetaConfig).filter(
        MetaConfig.clinic_id == current_user.clinic_id
    ).first()
    return config


@router.post("/connect", response_model=MetaConfigOut)
def connect_meta(
    data: MetaConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect Meta (Facebook/Instagram) account."""
    config = db.query(MetaConfig).filter(
        MetaConfig.clinic_id == current_user.clinic_id
    ).first()

    if config:
        config.access_token = data.access_token
        config.page_id = data.page_id
        config.page_name = data.page_name
        config.is_active = True
        config.connected_at = datetime.utcnow()
    else:
        config = MetaConfig(
            clinic_id=current_user.clinic_id,
            access_token=data.access_token,
            page_id=data.page_id,
            page_name=data.page_name,
            is_active=True,
            connected_at=datetime.utcnow()
        )
        db.add(config)

    db.commit()
    db.refresh(config)
    return config


@router.delete("/disconnect")
def disconnect_meta(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Meta account."""
    config = db.query(MetaConfig).filter(
        MetaConfig.clinic_id == current_user.clinic_id
    ).first()
    if config:
        config.is_active = False
        db.commit()
    return {"status": "disconnected"}


# ---------------------------------------------------------------------------
# Meta Lead Form Webhook (public)
# ---------------------------------------------------------------------------

@router.get("/webhook")
async def verify_meta_webhook(request: Request):
    """Meta webhook verification for lead forms."""
    from app.config import META_APP_SECRET
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    # Use app secret as verify token for simplicity
    if mode == "subscribe" and token == META_APP_SECRET and challenge:
        return int(challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_meta_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive Meta lead form submissions."""
    try:
        body = await request.json()
    except Exception:
        return {"status": "ok"}

    # Parse lead form data
    entries = body.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            if change.get("field") == "leadgen":
                value = change.get("value", {})
                await _process_meta_lead(db, value)

    return {"status": "ok"}


async def _process_meta_lead(db: Session, lead_data: dict):
    """Process a lead from Meta lead form."""
    page_id = lead_data.get("page_id")
    form_id = lead_data.get("form_id")
    leadgen_id = lead_data.get("leadgen_id")

    # Find the clinic by page_id
    config = db.query(MetaConfig).filter(
        MetaConfig.page_id == str(page_id),
        MetaConfig.is_active == True
    ).first()

    if not config:
        logger.warning(f"No Meta config for page_id: {page_id}")
        return

    # Fetch actual lead data from Meta API
    # In production, you'd call: GET /{leadgen_id}?access_token={token}&fields=...
    # For now, we create a lead with the metadata we have
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://graph.facebook.com/v21.0/{leadgen_id}",
                params={
                    "access_token": config.access_token,
                    "fields": "field_data,created_time,ad_id,ad_name,campaign_id,campaign_name,form_id,form_name"
                }
            )
            if resp.status_code != 200:
                logger.error(f"Failed to fetch Meta lead {leadgen_id}: {resp.text}")
                return

            data = resp.json()
    except Exception as e:
        logger.error(f"Error fetching Meta lead: {e}")
        return

    # Parse field data
    field_data = {
        f["name"]: f["values"][0] if f.get("values") else ""
        for f in data.get("field_data", [])
    }

    name = field_data.get("full_name", field_data.get("first_name", ""))
    phone = field_data.get("phone_number", field_data.get("phone", ""))
    email = field_data.get("email", "")

    if phone:
        from app.services.whatsapp_service import normalize_phone
        phone = normalize_phone(phone)

    # Check for duplicate
    existing = None
    if phone:
        existing = db.query(Lead).filter(
            Lead.clinic_id == config.clinic_id,
            Lead.phone == phone
        ).first()

    if existing:
        existing.form_data = field_data
        existing.campaign_name = data.get("campaign_name", "")
        existing.updated_at = datetime.utcnow()
        lead = existing
    else:
        lead = Lead(
            clinic_id=config.clinic_id,
            name=name,
            phone=phone,
            email=email,
            source="meta_lead_form",
            campaign_name=data.get("campaign_name", ""),
            campaign_source="meta",
            campaign_medium="social",
            form_data=field_data
        )
        db.add(lead)

    db.flush()
    lead.lead_score = calculate_lead_score(db, lead)
    db.commit()

    # Auto-enroll
    try:
        auto_enroll_lead(db, lead)
    except Exception as e:
        logger.error(f"Meta lead auto-enroll failed: {e}")

    logger.info(f"Meta lead created/updated: {lead.id} from form {form_id}")
