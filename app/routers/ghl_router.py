"""
CallCoach CRM - GoHighLevel Integration Router

Endpoints for connecting, syncing, and managing GHL integration.
Users add their own GHL API key to pull leads into the CallCoach pipeline.
Includes webhook endpoint for real-time contact sync from GHL.
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GHLIntegration, PipelineDeal, DealActivity, User, Clinic
from app.auth import get_current_user
from app.services.ghl_service import (
    GHLClient,
    map_ghl_opportunity_to_deal,
    map_ghl_contact_to_deal,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/integrations/ghl", tags=["ghl-integration"])


# ── Schemas ──────────────────────────────────────────────────────────

class GHLConnectRequest(BaseModel):
    api_key: str
    location_id: Optional[str] = None
    sync_pipeline_id: Optional[str] = None
    auto_sync_enabled: bool = True

class GHLUpdateRequest(BaseModel):
    location_id: Optional[str] = None
    sync_pipeline_id: Optional[str] = None
    auto_sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None

class GHLStatusResponse(BaseModel):
    is_connected: bool
    is_active: bool = False
    location_id: Optional[str] = None
    sync_pipeline_id: Optional[str] = None
    auto_sync_enabled: bool = False
    last_sync_at: Optional[str] = None
    last_sync_status: str = "never"
    last_sync_error: Optional[str] = None
    total_leads_synced: int = 0
    created_at: Optional[str] = None


# ── Connect / Disconnect ─────────────────────────────────────────────

@router.post("/connect")
async def connect_ghl(
    req: GHLConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Connect a GoHighLevel account by providing an API key.
    Validates the key against GHL's API before saving.
    Only admins and managers can connect integrations.
    """
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Only admins and managers can manage integrations")

    # Validate the API key with GHL
    client = GHLClient(req.api_key, req.location_id)
    try:
        validation = await client.validate_key()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"GHL validation error: {e}")
        raise HTTPException(status_code=502, detail="Could not reach GoHighLevel API. Please try again.")

    # Check if integration already exists for this clinic
    existing = db.query(GHLIntegration).filter(
        GHLIntegration.clinic_id == current_user.clinic_id
    ).first()

    if existing:
        # Update existing integration
        existing.api_key = req.api_key
        existing.location_id = req.location_id
        existing.sync_pipeline_id = req.sync_pipeline_id
        existing.auto_sync_enabled = req.auto_sync_enabled
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
    else:
        # Create new integration
        integration = GHLIntegration(
            clinic_id=current_user.clinic_id,
            api_key=req.api_key,
            location_id=req.location_id,
            sync_pipeline_id=req.sync_pipeline_id,
            auto_sync_enabled=req.auto_sync_enabled,
        )
        db.add(integration)

    db.commit()

    # Fetch available pipelines to help user configure
    pipelines = []
    try:
        pipelines = await client.get_pipelines()
    except Exception:
        pass

    return {
        "status": "connected",
        "message": "GoHighLevel integration connected successfully",
        "pipelines": [
            {"id": p.get("id"), "name": p.get("name")}
            for p in pipelines
        ]
    }


@router.post("/disconnect")
def disconnect_ghl(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect GHL integration (soft delete - keeps synced data)."""
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Only admins and managers can manage integrations")

    integration = db.query(GHLIntegration).filter(
        GHLIntegration.clinic_id == current_user.clinic_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="No GHL integration found")

    integration.is_active = False
    integration.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "disconnected", "message": "GoHighLevel integration disconnected. Synced leads remain in your pipeline."}


# ── Status ───────────────────────────────────────────────────────────

@router.get("/status", response_model=GHLStatusResponse)
def get_ghl_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current GHL integration status."""
    integration = db.query(GHLIntegration).filter(
        GHLIntegration.clinic_id == current_user.clinic_id
    ).first()

    if not integration:
        return GHLStatusResponse(is_connected=False)

    return GHLStatusResponse(
        is_connected=True,
        is_active=integration.is_active,
        location_id=integration.location_id,
        sync_pipeline_id=integration.sync_pipeline_id,
        auto_sync_enabled=integration.auto_sync_enabled,
        last_sync_at=integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        last_sync_status=integration.last_sync_status or "never",
        last_sync_error=integration.last_sync_error,
        total_leads_synced=integration.total_leads_synced or 0,
        created_at=integration.created_at.isoformat() if integration.created_at else None,
    )


@router.patch("/settings")
def update_ghl_settings(
    req: GHLUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update GHL integration settings."""
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Only admins and managers can manage integrations")

    integration = db.query(GHLIntegration).filter(
        GHLIntegration.clinic_id == current_user.clinic_id,
        GHLIntegration.is_active == True
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="No active GHL integration found")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(integration, key, value)
    integration.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "updated", "message": "GHL settings updated"}


# ── Pipelines ────────────────────────────────────────────────────────

@router.get("/pipelines")
async def list_ghl_pipelines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch available pipelines from the connected GHL account."""
    integration = db.query(GHLIntegration).filter(
        GHLIntegration.clinic_id == current_user.clinic_id,
        GHLIntegration.is_active == True
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="No active GHL integration found")

    client = GHLClient(integration.api_key, integration.location_id)
    try:
        pipelines = await client.get_pipelines()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch pipelines: {str(e)[:200]}")

    return {
        "pipelines": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "stages": [
                    {"id": s.get("id"), "name": s.get("name")}
                    for s in p.get("stages", [])
                ]
            }
            for p in pipelines
        ]
    }


# ── Sync ─────────────────────────────────────────────────────────────

@router.post("/sync")
async def sync_ghl_leads(
    sync_type: str = "opportunities",  # "opportunities" or "contacts"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pull leads from GoHighLevel and create/update them in the CallCoach pipeline.

    sync_type:
    - "opportunities": Sync from a GHL pipeline (recommended)
    - "contacts": Sync all GHL contacts as new leads
    """
    integration = db.query(GHLIntegration).filter(
        GHLIntegration.clinic_id == current_user.clinic_id,
        GHLIntegration.is_active == True
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="No active GHL integration found")

    client = GHLClient(integration.api_key, integration.location_id)

    created = 0
    updated = 0
    skipped = 0
    errors = []

    try:
        if sync_type == "opportunities":
            # Sync from GHL pipeline opportunities
            all_opps = []
            cursor = None
            for _ in range(20):  # max 20 pages (2000 leads)
                result = await client.get_opportunities(
                    pipeline_id=integration.sync_pipeline_id,
                    limit=100,
                    after=cursor
                )
                opps = result.get("opportunities", [])
                if not opps:
                    break
                all_opps.extend(opps)
                meta = result.get("meta", {})
                cursor = meta.get("startAfterId")
                if not cursor:
                    break

            for opp in all_opps:
                try:
                    deal_data = map_ghl_opportunity_to_deal(opp)
                    result = _upsert_deal(db, current_user, deal_data, opp.get("id"))
                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1
                    else:
                        skipped += 1
                except Exception as e:
                    errors.append(f"Opp {opp.get('id', '?')}: {str(e)[:100]}")

        else:
            # Sync from GHL contacts
            all_contacts = []
            cursor = None
            for _ in range(20):
                result = await client.get_contacts(limit=100, after=cursor)
                contacts = result.get("contacts", [])
                if not contacts:
                    break
                all_contacts.extend(contacts)
                meta = result.get("meta", {})
                cursor = meta.get("startAfterId")
                if not cursor:
                    break

            for contact in all_contacts:
                try:
                    deal_data = map_ghl_contact_to_deal(contact)
                    result = _upsert_deal(db, current_user, deal_data, None)
                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1
                    else:
                        skipped += 1
                except Exception as e:
                    errors.append(f"Contact {contact.get('id', '?')}: {str(e)[:100]}")

        # Update integration sync status
        integration.last_sync_at = datetime.utcnow()
        integration.last_sync_status = "success"
        integration.last_sync_error = None
        integration.total_leads_synced = (integration.total_leads_synced or 0) + created
        db.commit()

    except Exception as e:
        integration.last_sync_at = datetime.utcnow()
        integration.last_sync_status = "failed"
        integration.last_sync_error = str(e)[:500]
        db.commit()
        raise HTTPException(status_code=502, detail=f"Sync failed: {str(e)[:200]}")

    return {
        "status": "completed",
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:10],  # limit error list
        "total_processed": created + updated + skipped,
    }


# ── Internal Helpers ─────────────────────────────────────────────────

def _upsert_deal(
    db: Session,
    current_user: User,
    deal_data: dict,
    ghl_opportunity_id: Optional[str]
) -> str:
    """
    Create or update a PipelineDeal from GHL data.
    Returns: "created", "updated", or "skipped"
    """
    # Check if deal already exists (by GHL opportunity ID or contact phone match)
    existing = None

    if ghl_opportunity_id:
        existing = db.query(PipelineDeal).filter(
            PipelineDeal.clinic_id == current_user.clinic_id,
            PipelineDeal.ghl_opportunity_id == ghl_opportunity_id
        ).first()

    if not existing and deal_data.get("ghl_contact_id"):
        existing = db.query(PipelineDeal).filter(
            PipelineDeal.clinic_id == current_user.clinic_id,
            PipelineDeal.ghl_contact_id == deal_data["ghl_contact_id"]
        ).first()

    if not existing and deal_data.get("contact_phone"):
        # Match by phone number as fallback
        existing = db.query(PipelineDeal).filter(
            PipelineDeal.clinic_id == current_user.clinic_id,
            PipelineDeal.contact_phone == deal_data["contact_phone"]
        ).first()

    if existing:
        # Update only if GHL data is newer or has more info
        changed = False
        if deal_data.get("deal_value") and deal_data["deal_value"] > 0 and existing.deal_value == 0:
            existing.deal_value = deal_data["deal_value"]
            changed = True
        if deal_data.get("contact_email") and not existing.contact_email:
            existing.contact_email = deal_data["contact_email"]
            changed = True
        if deal_data.get("treatment_interest") and not existing.treatment_interest:
            existing.treatment_interest = deal_data["treatment_interest"]
            changed = True
        if deal_data.get("ghl_opportunity_id") and not existing.ghl_opportunity_id:
            existing.ghl_opportunity_id = deal_data["ghl_opportunity_id"]
            changed = True
        if deal_data.get("ghl_contact_id") and not existing.ghl_contact_id:
            existing.ghl_contact_id = deal_data["ghl_contact_id"]
            changed = True

        if changed:
            existing.updated_at = datetime.utcnow()
            db.flush()
            return "updated"
        return "skipped"

    # Create new deal
    new_deal = PipelineDeal(
        clinic_id=current_user.clinic_id,
        contact_name=deal_data["contact_name"],
        contact_phone=deal_data.get("contact_phone"),
        contact_email=deal_data.get("contact_email"),
        title=deal_data["title"],
        treatment_interest=deal_data.get("treatment_interest"),
        deal_value=deal_data.get("deal_value", 0),
        stage=deal_data.get("stage", "new_inquiry"),
        priority=deal_data.get("priority", "medium"),
        source=deal_data.get("source", "gohighlevel"),
        status=deal_data.get("status", "open"),
        ghl_contact_id=deal_data.get("ghl_contact_id"),
        ghl_opportunity_id=deal_data.get("ghl_opportunity_id"),
    )
    db.add(new_deal)
    db.flush()

    # Create activity log
    activity = DealActivity(
        deal_id=new_deal.id,
        user_id=current_user.id,
        activity_type="note",
        description="Auto-imported from GoHighLevel",
        extra_data={"source": "ghl_sync", "ghl_contact_id": deal_data.get("ghl_contact_id")}
    )
    db.add(activity)
    db.flush()

    return "created"


# ── GHL Webhooks (real-time contact sync) ────────────────────────────

webhook_router = APIRouter(prefix="/api/webhooks/ghl", tags=["ghl-webhooks"])


@webhook_router.post("/contact")
async def ghl_contact_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive real-time contact create/update events from GoHighLevel.

    GHL sends webhooks with event types like:
    - ContactCreate
    - ContactUpdate
    - OpportunityCreate
    - OpportunityStatusUpdate
    - OpportunityStageUpdate

    Configure in GHL: Settings > Webhooks > Add webhook URL:
    https://www.callcoachsba.com/api/webhooks/ghl/contact
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type", "")
    location_id = payload.get("locationId") or payload.get("location_id", "")

    logger.info(f"GHL webhook received: type={event_type}, location={location_id}")

    if not location_id:
        # Try to extract from nested data
        location_id = (
            payload.get("contact", {}).get("locationId")
            or payload.get("opportunity", {}).get("locationId")
            or ""
        )

    if not location_id:
        logger.warning("GHL webhook: no locationId found, ignoring")
        return {"status": "ignored", "reason": "no locationId"}

    # Find the clinic integration for this GHL location
    integration = db.query(GHLIntegration).filter(
        GHLIntegration.location_id == location_id,
        GHLIntegration.is_active == True
    ).first()

    if not integration:
        logger.warning(f"GHL webhook: no active integration for location {location_id}")
        return {"status": "ignored", "reason": "no matching integration"}

    # Find an admin user for this clinic to attribute the import
    admin_user = db.query(User).filter(
        User.clinic_id == integration.clinic_id,
        User.role.in_(["admin", "manager"])
    ).first()

    if not admin_user:
        admin_user = db.query(User).filter(
            User.clinic_id == integration.clinic_id
        ).first()

    if not admin_user:
        logger.warning(f"GHL webhook: no user found for clinic {integration.clinic_id}")
        return {"status": "ignored", "reason": "no user for clinic"}

    result = "ignored"

    try:
        if event_type in ("ContactCreate", "ContactUpdate", "ContactDndUpdate"):
            contact_data = payload.get("contact") or payload
            if contact_data:
                deal_data = map_ghl_contact_to_deal(contact_data)
                result = _upsert_deal(db, admin_user, deal_data, None)
                db.commit()

        elif event_type in (
            "OpportunityCreate", "OpportunityStatusUpdate",
            "OpportunityStageUpdate", "OpportunityMonetaryValueUpdate"
        ):
            opp_data = payload.get("opportunity") or payload
            if opp_data:
                deal_data = map_ghl_opportunity_to_deal(opp_data)
                result = _upsert_deal(db, admin_user, deal_data, opp_data.get("id"))
                db.commit()

        # Update sync timestamp
        integration.last_sync_at = datetime.utcnow()
        integration.last_sync_status = "success"
        if result == "created":
            integration.total_leads_synced = (integration.total_leads_synced or 0) + 1
        db.commit()

    except Exception as e:
        logger.error(f"GHL webhook processing error: {e}")
        integration.last_sync_at = datetime.utcnow()
        integration.last_sync_status = "failed"
        integration.last_sync_error = str(e)[:500]
        db.commit()
        return {"status": "error", "message": str(e)[:200]}

    logger.info(f"GHL webhook processed: type={event_type}, result={result}")
    return {"status": "ok", "result": result}
