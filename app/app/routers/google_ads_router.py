"""
CallCoach CRM - Google Ads Router
Google Ads management, lead sync, campaign monitoring, and reporting.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-ads", tags=["google-ads"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GoogleAdsConfigUpdate(BaseModel):
    customer_id: Optional[str] = None
    developer_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    login_customer_id: Optional[str] = None
    is_active: Optional[bool] = None

class GoogleAdsCampaignOut(BaseModel):
    id: str
    name: str
    status: str
    budget_amount: float
    campaign_type: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    cost: float = 0
    ctr: float = 0
    cpc: float = 0
    conversion_rate: float = 0

class GoogleAdsLeadOut(BaseModel):
    id: str
    campaign_name: str
    ad_group: str
    keyword: str
    lead_name: str
    lead_phone: str
    lead_email: str
    form_name: str
    submitted_at: str
    synced: bool = False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@router.get("/config")
def get_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Google Ads configuration status."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    gads = settings.get("google_ads", {})
    return {
        "connected": bool(gads.get("customer_id") and gads.get("refresh_token")),
        "customer_id": gads.get("customer_id", ""),
        "login_customer_id": gads.get("login_customer_id", ""),
        "has_developer_token": bool(gads.get("developer_token")),
        "has_refresh_token": bool(gads.get("refresh_token")),
        "is_active": gads.get("is_active", False)
    }


@router.post("/config")
def update_config(
    data: GoogleAdsConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update Google Ads configuration."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    settings = dict(clinic.settings or {})
    gads = dict(settings.get("google_ads", {}))

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if v is not None:
            gads[k] = v

    gads["updated_at"] = datetime.utcnow().isoformat()
    settings["google_ads"] = gads
    clinic.settings = settings
    db.commit()
    return {"status": "updated", "connected": bool(gads.get("customer_id") and gads.get("refresh_token"))}


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

@router.get("/campaigns")
def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List Google Ads campaigns (returns mock data if not connected to real API)."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    gads = settings.get("google_ads", {})

    if not gads.get("customer_id"):
        return {"campaigns": [], "message": "Connect Google Ads in Settings to see campaigns"}

    # Return stored campaign data or empty
    return {"campaigns": gads.get("cached_campaigns", []), "last_synced": gads.get("last_synced", None)}


@router.post("/sync-campaigns")
def sync_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync campaigns from Google Ads API."""
    return {"status": "sync_initiated", "message": "Campaign sync requires Google Ads API credentials. Configure in Settings > Google Ads."}


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

@router.get("/leads")
def list_google_leads(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List leads from Google Ads lead form extensions."""
    from app.models_whatsapp import Lead
    leads = db.query(Lead).filter(
        Lead.clinic_id == current_user.clinic_id,
        Lead.campaign_source == "google"
    ).order_by(Lead.created_at.desc()).limit(100).all()

    return {"leads": [{"id": str(l.id), "name": l.name, "phone": l.phone, "email": l.email,
                       "campaign_name": l.campaign_name, "source": l.source,
                       "status": l.status, "lead_score": l.lead_score,
                       "created_at": l.created_at.isoformat() if l.created_at else None} for l in leads]}


@router.post("/leads/webhook/{api_key}")
def google_ads_lead_webhook(
    api_key: str,
    lead_data: dict,
    db: Session = Depends(get_db)
):
    """Webhook for Google Ads lead form submissions."""
    from app.models import Clinic
    from app.models_whatsapp import Lead

    clinic = db.query(Clinic).filter(Clinic.api_key == api_key).first()
    if not clinic:
        raise HTTPException(status_code=401, detail="Invalid API key")

    lead = Lead(
        clinic_id=clinic.id,
        name=lead_data.get("name", ""),
        phone=lead_data.get("phone", ""),
        email=lead_data.get("email", ""),
        source="form_google",
        campaign_source="google",
        campaign_name=lead_data.get("campaign_name", "Google Ads"),
        form_data=lead_data,
        status="new"
    )
    db.add(lead)
    db.commit()
    return {"status": "lead_created", "lead_id": str(lead.id)}


# ---------------------------------------------------------------------------
# Performance & Reports
# ---------------------------------------------------------------------------

@router.get("/performance")
def get_performance(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Google Ads performance summary."""
    from app.models_expanded import AdPerformance
    from sqlalchemy import func
    from datetime import timedelta

    since = datetime.utcnow() - timedelta(days=days)
    stats = db.query(
        func.sum(AdPerformance.spend),
        func.sum(AdPerformance.impressions),
        func.sum(AdPerformance.clicks),
        func.sum(AdPerformance.conversions)
    ).filter(
        AdPerformance.clinic_id == current_user.clinic_id,
        AdPerformance.platform == "google",
        AdPerformance.date >= since
    ).first()

    spend = float(stats[0] or 0)
    impressions = int(stats[1] or 0)
    clicks = int(stats[2] or 0)
    conversions = int(stats[3] or 0)

    return {
        "period_days": days,
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "ctr": round((clicks / impressions * 100) if impressions > 0 else 0, 2),
        "cpc": round(spend / clicks if clicks > 0 else 0, 2),
        "cpa": round(spend / conversions if conversions > 0 else 0, 2),
        "conversion_rate": round((conversions / clicks * 100) if clicks > 0 else 0, 2)
    }


@router.post("/ai-recommendations")
def get_ai_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered Google Ads optimization recommendations."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from anthropic import Anthropic
    from app.models import Clinic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    prompt = f"""You are an expert Google Ads optimizer for medical/aesthetic clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}

Provide 5 actionable Google Ads optimization recommendations covering:
1. Keyword strategy improvements
2. Ad copy optimization
3. Bid strategy adjustments
4. Landing page suggestions
5. Negative keyword recommendations

Format as JSON array with objects: {{title, description, priority (high/medium/low), expected_impact}}"""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"recommendations": response.content[0].text}
    except Exception as e:
        logger.error(f"Google Ads AI recommendations failed: {e}")
        raise HTTPException(status_code=500, detail="AI recommendations failed")
