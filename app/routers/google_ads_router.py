"""
CallCoach CRM - Google Ads Router
Google Ads management, lead sync, campaign monitoring, and reporting.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity, get_activity_logs
from app.services.prompt_quality import WRITING_QUALITY_DIRECTIVE

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
    log_activity(db, current_user.clinic_id, "ads", "google_ads_config_updated",
                 {"connected": bool(gads.get("customer_id") and gads.get("refresh_token"))},
                 current_user.email)
    return {"status": "updated", "connected": bool(gads.get("customer_id") and gads.get("refresh_token"))}


# ---------------------------------------------------------------------------
# Generation History
# ---------------------------------------------------------------------------

@router.get("/history")
def get_generation_history(
    action_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Google Ads content generation history."""
    logs = get_activity_logs(db=db, clinic_id=current_user.clinic_id, category="script_generation", limit=limit)
    ads_logs = get_activity_logs(db=db, clinic_id=current_user.clinic_id, category="ads", limit=limit)
    content_logs = get_activity_logs(db=db, clinic_id=current_user.clinic_id, category="content", limit=limit)
    all_logs = logs + ads_logs + content_logs
    # Filter to only google-related logs
    google_keywords = ["google", "keyword", "landing_page", "search_ad", "campaign_structure"]
    all_logs = [l for l in all_logs if any(kw in l.get("action", "") for kw in google_keywords)]
    all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    if action_filter:
        all_logs = [l for l in all_logs if action_filter in l.get("action", "")]
    return {"history": all_logs[:limit], "count": len(all_logs[:limit])}


def _apply_regenerate_changes(prompt: str, data: dict) -> str:
    """Append user's regeneration feedback to the prompt if provided."""
    changes = data.get("regenerate_changes", "")
    if changes and changes.strip():
        prompt += f"\n\nIMPORTANT - USER FEEDBACK (apply these specific changes to your output):\n{changes.strip()}"
    return prompt


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
    lead_data: dict = Body(...),
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
    log_activity(db, clinic.id, "lead", "google_ads_lead_received",
                 {"campaign_name": lead_data.get("campaign_name", ""), "name": lead_data.get("name", "")})
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
            system=WRITING_QUALITY_DIRECTIVE.strip(),
            messages=[{"role": "user", "content": prompt}]
        )
        result_data = {"recommendations": response.content[0].text}
        log_activity(db, current_user.clinic_id, "ads", "google_ads_ai_recommendations_generated",
                     {"output": result_data}, current_user.email)
        return result_data
    except Exception as e:
        logger.error(f"Google Ads AI recommendations failed: {e}")
        raise HTTPException(status_code=500, detail="AI recommendations failed")


def _call_claude_gads(prompt: str, max_tokens: int = 3000) -> str:
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")
    from anthropic import Anthropic
    import json as _json
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=max_tokens, system=WRITING_QUALITY_DIRECTIVE.strip(), messages=[{"role": "user", "content": prompt}])
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"): text = text[4:]
        text = text.strip()
    try:
        return _json.loads(text)
    except:
        return text


# ---------------------------------------------------------------------------
# Google Ads Content Generation
# ---------------------------------------------------------------------------

@router.post("/generate-search-ads")
def generate_search_ads(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate responsive search ad copy for Google Ads."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedure = data.get("procedure", "aesthetic treatment")
    location = data.get("location", "")
    num_ads = data.get("num_ads", 3)
    usp = data.get("usp", "")

    prompt = f"""You are a Google Ads search campaign expert for aesthetic and medical clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Procedure: {procedure}
Location: {location or 'India'}
USP: {usp or 'Expert doctors, advanced technology, trusted results'}

Generate {num_ads} Responsive Search Ads. Each ad must include:

1. headlines: Array of 15 headlines (max 30 characters each). Mix of:
   - Procedure name keywords
   - Location-based ("Best [Procedure] in [City]")
   - Benefit-focused ("Natural Looking Results")
   - Trust signals ("Board Certified Doctors")
   - Offer-based ("Free Consultation Today")
   - Urgency ("Limited Slots Available")
2. descriptions: Array of 4 descriptions (max 90 characters each). Focus on benefits, social proof, CTA.
3. sitelink_extensions: 4 sitelinks with title (max 25 chars) and description (max 35 chars each line, 2 lines)
4. callout_extensions: 6 callouts (max 25 chars each)
5. structured_snippets: header and values for structured snippet extensions
6. keyword_suggestions: 10 high-intent keywords to target with this ad

Format as JSON array of ad objects."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        parsed = _call_claude_gads(prompt, 4000)
        result_data = {"ads": parsed, "count": num_ads}
        log_activity(db, current_user.clinic_id, "script_generation", "google_search_ads_generated",
                     {"procedure": procedure, "location": location, "num_ads": num_ads, "output": result_data},
                     current_user.email)
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Search ad generation failed")


@router.post("/generate-keywords")
def generate_keywords(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate keyword research for Google Ads campaigns."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedures = data.get("procedures", ["aesthetic treatment"])
    location = data.get("location", "")

    prompt = f"""You are a Google Ads keyword research expert for aesthetic and medical clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Procedures: {', '.join(procedures) if isinstance(procedures, list) else procedures}
Location: {location or 'India'}

For each procedure, provide:

1. high_intent_keywords: 10 transactional keywords (people ready to book)
2. research_keywords: 10 informational keywords (people researching)
3. competitor_keywords: 5 competitor-related keywords
4. negative_keywords: 10 negative keywords to exclude
5. long_tail_keywords: 10 long-tail keywords with lower competition
6. local_keywords: 5 location-specific keywords
7. estimated_cpc_range: Low and high CPC estimate in INR
8. match_type_recommendation: Which match type to use for each group

Format as JSON object with procedure names as keys."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        parsed = _call_claude_gads(prompt, 3000)
        result_data = {"keywords": parsed}
        log_activity(db, current_user.clinic_id, "ads", "google_keyword_research_generated",
                     {"procedures": procedures, "location": location, "output": result_data},
                     current_user.email)
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Keyword research failed")


@router.post("/generate-landing-page")
def generate_landing_page_copy(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate landing page copy optimized for Google Ads conversions."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedure = data.get("procedure", "aesthetic treatment")
    doctor_name = data.get("doctor_name", "")

    prompt = f"""You are a landing page conversion expert for aesthetic clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Doctor: {doctor_name}
Procedure: {procedure}

Generate complete landing page copy sections:

1. hero_section: headline (max 10 words), subheadline (max 20 words), cta_button_text
2. problem_section: 3 pain points the patient experiences
3. solution_section: How this procedure solves their problem
4. process_section: 3-5 steps of the treatment process
5. benefits_section: 6 key benefits with icons suggestions
6. social_proof_section: 3 testimonial templates, stats to showcase
7. doctor_section: Doctor bio template, credentials to highlight
8. faq_section: 8 frequently asked questions with answers
9. urgency_section: Offer text, countdown suggestion, limited slots messaging
10. form_section: Form headline, form fields to include, submit button text

Format as JSON object."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        parsed = _call_claude_gads(prompt, 3500)
        result_data = {"landing_page": parsed}
        log_activity(db, current_user.clinic_id, "content", "google_landing_page_copy_generated",
                     {"procedure": procedure, "doctor_name": doctor_name, "output": result_data},
                     current_user.email)
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Landing page copy generation failed")


@router.post("/generate-campaign-structure")
def generate_campaign_structure(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a complete Google Ads campaign structure."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedures = data.get("procedures", ["aesthetic treatments"])
    budget = data.get("monthly_budget", "50000")
    location = data.get("location", "")

    prompt = f"""You are a Google Ads campaign architect for aesthetic clinics following SBA methodology.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Procedures: {', '.join(procedures) if isinstance(procedures, list) else procedures}
Monthly Budget: Rs. {budget}
Location: {location or 'India'}

Create a complete Google Ads campaign structure:

1. campaigns: Array of campaigns, each with name, type (Search/Display/PMax), daily_budget, bidding_strategy
2. ad_groups: For each campaign, list ad groups with name, keywords, negative_keywords
3. budget_split: How to allocate budget across campaigns (percentages)
4. bidding_strategy: Recommended bidding for each campaign stage (learning, optimization, scaling)
5. conversion_tracking: What conversions to track (form_submit, phone_call, whatsapp_click, booking)
6. audience_signals: For PMax campaigns, audience signals to use
7. geo_targeting: Location targeting recommendations
8. schedule: Ad scheduling recommendations (best hours and days)
9. first_month_plan: Week-by-week plan for the first 30 days
10. scaling_triggers: When to increase budget, add campaigns, or pause underperformers

Format as JSON object."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        parsed = _call_claude_gads(prompt, 4000)
        result_data = {"structure": parsed}
        log_activity(db, current_user.clinic_id, "ads", "google_campaign_structure_generated",
                     {"procedures": procedures, "budget": budget, "location": location, "output": result_data},
                     current_user.email)
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Campaign structure generation failed")
