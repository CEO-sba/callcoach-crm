"""
CallCoach CRM - SEO & GMB Router
SEO tools, GMB optimization, backlink tracking, and AI SEO coaching.
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
from app.services.activity_logger import log_activity
from app.services.prompt_quality import enhance_system_prompt, WRITING_QUALITY_DIRECTIVE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/seo", tags=["seo"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GMBConfigUpdate(BaseModel):
    business_name: Optional[str] = None
    business_id: Optional[str] = None
    location_id: Optional[str] = None
    api_key: Optional[str] = None
    categories: Optional[list] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

class SEOAuditRequest(BaseModel):
    website_url: str
    focus_keywords: Optional[list] = None
    procedures: Optional[list] = None

class BacklinkEntry(BaseModel):
    source_url: str
    target_url: str
    anchor_text: str = ""
    domain_authority: int = 0
    status: str = "active"
    notes: str = ""

class SEOCoachMessage(BaseModel):
    message: str
    context: Optional[str] = None


# ---------------------------------------------------------------------------
# GMB Configuration
# ---------------------------------------------------------------------------

@router.get("/gmb/config")
def get_gmb_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get GMB configuration."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    gmb = settings.get("gmb", {})
    return {
        "connected": bool(gmb.get("business_id")),
        "business_name": gmb.get("business_name", ""),
        "business_id": gmb.get("business_id", ""),
        "address": gmb.get("address", ""),
        "phone": gmb.get("phone", ""),
        "website": gmb.get("website", ""),
        "categories": gmb.get("categories", []),
        "optimization_score": gmb.get("optimization_score", 0)
    }


@router.post("/gmb/config")
def update_gmb_config(
    data: GMBConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update GMB configuration."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    settings = dict(clinic.settings or {})
    gmb = dict(settings.get("gmb", {}))
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if v is not None:
            gmb[k] = v
    gmb["updated_at"] = datetime.utcnow().isoformat()
    settings["gmb"] = gmb
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "content", "gmb_config_updated",
                 {"fields_updated": list(update_data.keys())}, current_user.email)
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# GMB AI Optimization
# ---------------------------------------------------------------------------

@router.post("/gmb/optimize")
def gmb_ai_optimize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI-powered GMB profile optimization suggestions."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from anthropic import Anthropic
    from app.models import Clinic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    gmb = settings.get("gmb", {})

    prompt = f"""You are a Google Business Profile (GMB) optimization expert for medical/aesthetic clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Specialty: {clinic.specialty if clinic else 'Aesthetics'}
Location: {gmb.get('address', 'Not specified')}
Website: {gmb.get('website', 'Not specified')}
Categories: {', '.join(gmb.get('categories', []))}

Provide a comprehensive GMB optimization plan:

1. Profile Completeness Check (what's missing)
2. Category Optimization (primary + secondary categories)
3. Business Description (write an optimized 750-character description)
4. Services to Add (list of services with descriptions)
5. Q&A Strategy (10 questions patients commonly ask, with answers)
6. Post Strategy (4 GMB post ideas for this month)
7. Photo Strategy (types of photos to add)
8. Review Response Templates (3 templates: positive, neutral, negative)

Format as JSON with sections as keys."""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2500,
            system=WRITING_QUALITY_DIRECTIVE.strip(),
            messages=[{"role": "user", "content": prompt}]
        )
        log_activity(db, current_user.clinic_id, "content", "gmb_optimization_generated",
                     {"clinic": clinic.name if clinic else "unknown"}, current_user.email)
        return {"optimization_plan": response.content[0].text}
    except Exception as e:
        logger.error(f"GMB optimization failed: {e}")
        raise HTTPException(status_code=500, detail="GMB optimization failed")


@router.post("/gmb/generate-posts")
def generate_gmb_posts(
    num_posts: int = 4,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate GMB posts using AI."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from anthropic import Anthropic
    from app.models import Clinic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    prompt = f"""Generate {num_posts} Google Business Profile posts for an aesthetic/medical clinic.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Specialty: {clinic.specialty if clinic else 'Aesthetics'}

Each post should be:
- Under 1500 characters
- Include a call to action (Book Now, Learn More, Call Us)
- Mix of: offers, educational content, before/after stories (anonymized), clinic updates

Format as JSON array: [{{title, content, cta_type, suggested_image_description}}]"""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            system=WRITING_QUALITY_DIRECTIVE.strip(),
            messages=[{"role": "user", "content": prompt}]
        )
        ai_text = response.content[0].text.strip()
        # Parse JSON from AI response
        import json as _json
        if ai_text.startswith("```"):
            ai_text = ai_text.split("```")[1]
            if ai_text.startswith("json"):
                ai_text = ai_text[4:]
            ai_text = ai_text.strip()
        posts = _json.loads(ai_text)
        log_activity(db, current_user.clinic_id, "content", "gmb_posts_generated",
                     {"num_posts": num_posts}, current_user.email)
        return {"posts": posts}
    except _json.JSONDecodeError:
        log_activity(db, current_user.clinic_id, "content", "gmb_posts_generated",
                     {"num_posts": num_posts, "parse_fallback": True}, current_user.email)
        return {"posts": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Post generation failed")


# ---------------------------------------------------------------------------
# SEO Audit
# ---------------------------------------------------------------------------

@router.post("/audit")
def run_seo_audit(
    data: SEOAuditRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run AI-powered SEO audit on the clinic website."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from anthropic import Anthropic
    from app.models import Clinic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    prompt = f"""You are an expert SEO auditor specializing in medical/aesthetic clinic websites.

Website: {data.website_url}
Focus Keywords: {', '.join(data.focus_keywords or ['aesthetic clinic', 'dermatologist', 'cosmetic treatment'])}
Procedures: {', '.join(data.procedures or ['botox', 'fillers', 'laser treatment'])}
Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}

Provide a comprehensive SEO audit covering:

1. Technical SEO Checklist (page speed, mobile, SSL, sitemap, robots.txt, schema markup)
2. On-Page SEO Analysis (title tags, meta descriptions, H1s, image alt text, internal linking)
3. Content Gap Analysis (what procedure pages are missing, blog topics needed)
4. Local SEO Factors (NAP consistency, citations, local schema)
5. Keyword Opportunities (20 high-intent keywords with estimated volume)
6. Schema Markup Recommendations (MedicalBusiness, Physician, LocalBusiness markup)
7. Page-by-Page Recommendations (homepage, service pages, about page)
8. Priority Action Items (ranked by impact, with effort estimate)

Format as JSON with each section as a key. Include actionable, specific recommendations."""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=3000,
            system=WRITING_QUALITY_DIRECTIVE.strip(),
            messages=[{"role": "user", "content": prompt}]
        )
        log_activity(db, current_user.clinic_id, "content", "seo_audit_generated",
                     {"website": data.website_url, "keywords": data.focus_keywords}, current_user.email)
        return {"audit": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="SEO audit failed")


# ---------------------------------------------------------------------------
# Backlinks
# ---------------------------------------------------------------------------

@router.get("/backlinks")
def list_backlinks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List tracked backlinks."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    backlinks = settings.get("backlinks", [])
    return {"backlinks": backlinks, "total": len(backlinks)}


@router.post("/backlinks")
def add_backlink(
    data: BacklinkEntry,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a backlink to tracking."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    settings = dict(clinic.settings or {})
    backlinks = list(settings.get("backlinks", []))
    backlinks.append({
        "id": str(len(backlinks) + 1),
        "source_url": data.source_url,
        "target_url": data.target_url,
        "anchor_text": data.anchor_text,
        "domain_authority": data.domain_authority,
        "status": data.status,
        "notes": data.notes,
        "added_at": datetime.utcnow().isoformat()
    })
    settings["backlinks"] = backlinks
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "content", "backlink_added",
                 {"source_url": data.source_url, "target_url": data.target_url, "da": data.domain_authority},
                 current_user.email)
    return {"status": "added", "total": len(backlinks)}


@router.post("/backlink-ideas")
def generate_backlink_ideas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered backlink building ideas."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from anthropic import Anthropic
    from app.models import Clinic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    prompt = f"""You are a link building expert for medical/aesthetic clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Location: {clinic.city if hasattr(clinic, 'city') and clinic.city else 'India'}

Generate 15 backlink building strategies specifically for aesthetic/medical clinics:

For each strategy provide:
1. Strategy name
2. Target website types
3. Outreach template (email draft)
4. Expected DA range
5. Difficulty level (easy/medium/hard)
6. Estimated time to acquire

Also include:
- 10 specific directory sites to submit to (with URLs)
- 5 PR/media outreach ideas
- 5 local citation opportunities

Format as JSON."""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            system=WRITING_QUALITY_DIRECTIVE.strip(),
            messages=[{"role": "user", "content": prompt}]
        )
        log_activity(db, current_user.clinic_id, "content", "backlink_ideas_generated",
                     {"clinic": clinic.name if clinic else "unknown"}, current_user.email)
        return {"ideas": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Backlink idea generation failed")


# ---------------------------------------------------------------------------
# SEO Coach (AI Chat)
# ---------------------------------------------------------------------------

@router.post("/coach")
def seo_coach_chat(
    data: SEOCoachMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI SEO Coach - ask anything about SEO for your clinic."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from anthropic import Anthropic
    from app.models import Clinic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    system_prompt = f"""You are an expert SEO coach specializing in medical and aesthetic clinics in India.
You help clinic owners and marketing teams with:
- Technical SEO implementation
- Content strategy for medical practices
- Local SEO and Google Business Profile optimization
- Keyword research for medical procedures
- Schema markup for healthcare websites
- Backlink building strategies for medical sites
- Generative AI SEO (getting cited in ChatGPT, Perplexity, etc.)

Clinic context:
- Name: {clinic.name if clinic else 'Aesthetic Clinic'}
- Specialty: {clinic.specialty if clinic else 'Aesthetics'}

Always provide specific, actionable advice. Include exact implementation steps.
When recommending schema markup, provide the actual JSON-LD code.
When recommending meta tags, write the exact tags.
Keep responses focused and practical."""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            system=enhance_system_prompt(system_prompt),
            messages=[{"role": "user", "content": data.message}]
        )
        log_activity(db, current_user.clinic_id, "content", "seo_coach_query",
                     {"query": data.message[:100]}, current_user.email)
        return {"response": response.content[0].text}
    except Exception as e:
        logger.error(f"SEO coach failed: {e}")
        raise HTTPException(status_code=500, detail="SEO coach failed")


@router.post("/keyword-research")
def keyword_research(
    procedures: list = [],
    location: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI-powered keyword research for clinic procedures."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from anthropic import Anthropic
    from app.models import Clinic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    prompt = f"""Generate comprehensive keyword research for an aesthetic/medical clinic.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Location: {location or 'India'}
Procedures: {', '.join(procedures) if procedures else 'botox, fillers, hair transplant, laser treatment, rhinoplasty'}

For each procedure, provide:
1. Primary keyword (highest volume)
2. 5 long-tail keywords
3. 5 question-based keywords (for FAQ pages)
4. 3 local keywords (with city name)
5. 3 "near me" variants
6. Estimated search intent (informational/transactional/navigational)
7. Content type recommendation (service page / blog / FAQ)

Also provide:
- 10 competitor keywords to target
- 10 "People Also Ask" questions
- 5 featured snippet opportunities

Format as JSON."""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2500,
            system=WRITING_QUALITY_DIRECTIVE.strip(),
            messages=[{"role": "user", "content": prompt}]
        )
        log_activity(db, current_user.clinic_id, "content", "keyword_research_generated",
                     {"procedures": procedures, "location": location}, current_user.email)
        return {"keywords": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Keyword research failed")
