"""
CallCoach CRM - Meta Ads Content Generation Router
AI-powered generation of video scripts, ad copy, image ad prompts, carousel prompts.
Following SBA Meta Ads SOP methodology.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity, get_activity_logs
from app.services.prompt_quality import WRITING_QUALITY_DIRECTIVE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meta-content", tags=["meta-content"])


def _call_claude(prompt: str, max_tokens: int = 3000) -> str:
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=WRITING_QUALITY_DIRECTIVE.strip(),
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def _apply_regenerate_changes(prompt: str, data: dict) -> str:
    """Append user's regeneration feedback to the prompt if provided."""
    changes = data.get("regenerate_changes", "")
    if changes and changes.strip():
        prompt += f"\n\nIMPORTANT - USER FEEDBACK (apply these specific changes to your output):\n{changes.strip()}"
    return prompt


def _parse_json_response(text: str):
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except:
        return text


# ---------------------------------------------------------------------------
# Generation History
# ---------------------------------------------------------------------------

@router.get("/history")
def get_generation_history(
    action_filter: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Meta Ads content generation history."""
    logs = get_activity_logs(
        db=db,
        clinic_id=current_user.clinic_id,
        category="script_generation",
        limit=limit,
    )
    # Also get ads category logs
    ads_logs = get_activity_logs(
        db=db,
        clinic_id=current_user.clinic_id,
        category="ads",
        limit=limit,
    )
    # Merge and sort by timestamp descending
    all_logs = logs + ads_logs
    all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    if action_filter:
        all_logs = [l for l in all_logs if action_filter in l.get("action", "")]
    return {"history": all_logs[:limit], "count": len(all_logs[:limit])}


# ---------------------------------------------------------------------------
# Video Ad Scripts
# ---------------------------------------------------------------------------

@router.post("/video-scripts")
def generate_video_scripts(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate video ad scripts for Meta Ads following SBA methodology."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedure = data.get("procedure", "aesthetic treatment")
    target_audience = data.get("target_audience", "women 25-45")
    tone = data.get("tone", "conversational and warm")
    language = data.get("language", "Hinglish")
    num_scripts = data.get("num_scripts", 4)
    script_type = data.get("script_type", "talking_head")
    usp = data.get("usp", "")
    offer = data.get("offer", "")
    doctor_name = data.get("doctor_name", "")

    prompt = f"""You are a Meta Ads video script expert for aesthetic and medical clinics in India.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Doctor: {doctor_name or (clinic.doctor_name if hasattr(clinic, 'doctor_name') else '')}
Procedure: {procedure}
Target Audience: {target_audience}
Tone: {tone}
Language: {language}
USP: {usp or 'Not specified'}
Current Offer: {offer or 'Free consultation'}
Script Type: {script_type}

Generate {num_scripts} video ad scripts. Each script should be:

1. Written for {script_type} format (talking_head = doctor speaking to camera, testimonial = patient story, educational = teaching about procedure, before_after = transformation story)
2. 30-60 seconds long when spoken naturally
3. In {language} (if Hinglish, use natural conversational Hinglish in Roman script)
4. Follow the AIDA framework: Attention hook (first 3 seconds), Interest (problem/pain point), Desire (solution/transformation), Action (clear CTA)
5. Include stage directions in [brackets]
6. Include text overlay suggestions in {{curly braces}}

For each script provide:
- script_number
- title (catchy internal name)
- hook (the first 3 second attention grabber)
- full_script (complete script with stage directions and text overlays)
- cta (call to action line)
- duration_estimate (seconds)
- best_for (what campaign objective this works best for: awareness, consideration, conversion)
- thumbnail_suggestion (what the thumbnail should show)

Format as JSON array."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        result = _call_claude(prompt, 4000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "script_generation", "meta_video_scripts_generated",
                     {"procedure": procedure, "language": language, "num_scripts": num_scripts, "script_type": script_type},
                     current_user.email)
        return {"scripts": parsed, "count": num_scripts}
    except Exception as e:
        logger.error(f"Video script generation failed: {e}")
        raise HTTPException(status_code=500, detail="Script generation failed")


# ---------------------------------------------------------------------------
# Ad Copy (Primary Text, Headlines, Descriptions)
# ---------------------------------------------------------------------------

@router.post("/ad-copy")
def generate_ad_copy(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate ad copy variations for Meta Ads."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedure = data.get("procedure", "aesthetic treatment")
    target_audience = data.get("target_audience", "women 25-45")
    language = data.get("language", "English")
    campaign_objective = data.get("campaign_objective", "lead_generation")
    offer = data.get("offer", "Free consultation")
    pain_points = data.get("pain_points", "")
    num_variations = data.get("num_variations", 5)

    prompt = f"""You are a Meta Ads copywriter for aesthetic and medical clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Procedure: {procedure}
Target Audience: {target_audience}
Language: {language}
Campaign Objective: {campaign_objective}
Offer: {offer}
Pain Points: {pain_points or 'General concerns about the procedure'}

Generate {num_variations} complete ad copy sets. Each set must include:

1. primary_text: The main ad body text (125-250 characters). This appears above the image/video. Use storytelling, pain-agitate-solve, or social proof angles. Mix approaches across variations.
2. headline: Bold text below image (max 40 characters). Action-oriented, benefit-focused.
3. description: Secondary text below headline (max 30 characters). Supporting info.
4. link_description: Text on the CTA button area.
5. angle: What psychological angle this copy uses (fear_of_missing_out, social_proof, authority, transformation, urgency, educational, empathy)
6. best_placement: Where this copy works best (feed, stories, reels, all)

Format as JSON array. Make each variation distinctly different in approach."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        result = _call_claude(prompt, 3000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "script_generation", "meta_ad_copy_generated",
                     {"procedure": procedure, "language": language, "num_variations": num_variations, "objective": campaign_objective},
                     current_user.email)
        return {"ad_copy": parsed, "count": num_variations}
    except Exception as e:
        logger.error(f"Ad copy generation failed: {e}")
        raise HTTPException(status_code=500, detail="Ad copy generation failed")


# ---------------------------------------------------------------------------
# Image Ad Prompts (AI image generation prompts) + Usage Guides
# ---------------------------------------------------------------------------

@router.post("/image-prompts")
def generate_image_prompts(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI image creation prompts for Meta Ads with usage guides."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedure = data.get("procedure", "aesthetic treatment")
    style = data.get("style", "professional and clean")
    num_prompts = data.get("num_prompts", 6)
    image_type = data.get("image_type", "mixed")

    prompt = f"""You are a creative director for aesthetic clinic advertising.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Procedure: {procedure}
Visual Style: {style}
Image Type: {image_type} (options: before_after_concept, lifestyle, clinical, infographic, offer_announcement, doctor_authority, mixed)

Generate {num_prompts} detailed AI image generation prompts that a designer can use with Midjourney, DALL-E, or similar tools.

For each prompt provide:
- prompt_number
- concept: Brief description of what the image shows
- ai_prompt: Detailed prompt for AI image generation (include style, lighting, composition, colors, mood). 50-100 words. Be very specific.
- text_overlay: What text should be overlaid on the image (for the designer to add)
- ad_format: Which Meta Ads format this works best for (1080x1080 feed, 1080x1920 story, 1200x628 link)
- use_case: Where to use this (feed_ad, story_ad, carousel_card, reel_cover)
- color_palette: Suggested colors (hex codes)
- platform_guide: Specific platform to use this prompt on (Midjourney, DALL-E 3, Ideogram, Leonardo AI, or Canva AI)
- how_to_use: Step-by-step instructions on how to use this exact prompt on the recommended platform to get the best output (4-6 steps)
- tips: 2-3 tips for getting better results with this specific prompt

IMPORTANT: Do NOT include real people's faces. Focus on abstract beauty, clinic interiors, treatment concepts, lifestyle shots, and graphical elements.

Format as JSON array."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        result = _call_claude(prompt, 4000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "script_generation", "meta_image_prompts_generated",
                     {"procedure": procedure, "num_prompts": num_prompts, "image_type": image_type},
                     current_user.email)
        return {"prompts": parsed, "count": num_prompts}
    except Exception as e:
        logger.error(f"Image prompt generation failed: {e}")
        raise HTTPException(status_code=500, detail="Image prompt generation failed")


# ---------------------------------------------------------------------------
# Carousel Prompts + Usage Guides
# ---------------------------------------------------------------------------

@router.post("/carousel-prompts")
def generate_carousel_prompts(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate carousel ad concepts for Meta Ads with usage guides."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedure = data.get("procedure", "aesthetic treatment")
    num_carousels = data.get("num_carousels", 3)
    language = data.get("language", "English")
    carousel_type = data.get("carousel_type", "educational")

    prompt = f"""You are a Meta Ads carousel expert for aesthetic clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Procedure: {procedure}
Language: {language}
Carousel Type: {carousel_type} (options: educational, before_after_journey, faq, process_steps, benefits, social_proof, comparison)

Generate {num_carousels} complete carousel ad concepts. Each carousel should have 5-8 cards.

For each carousel provide:
- carousel_number
- theme: The overall theme/angle
- primary_text: The ad body text for this carousel
- headline: The ad headline
- cards: Array of card objects, each with:
  - card_number
  - image_concept: What this card's image shows
  - ai_image_prompt: Detailed AI image generation prompt for this card
  - text_overlay_headline: Bold text on the card (max 6 words)
  - text_overlay_body: Supporting text on the card (max 15 words)
  - platform_to_use: Best AI platform for generating this card image (Midjourney, DALL-E 3, Canva AI, Leonardo AI)
- cta: Call to action for the carousel
- target_objective: awareness, consideration, or conversion
- design_guide: Step-by-step instructions on how to create this carousel from scratch, including which tools to use for image generation, how to assemble cards in Canva or Meta Creative Hub, text placement tips, and final export settings for Meta Ads

Format as JSON array."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        result = _call_claude(prompt, 5000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "script_generation", "meta_carousel_prompts_generated",
                     {"procedure": procedure, "num_carousels": num_carousels, "carousel_type": carousel_type},
                     current_user.email)
        return {"carousels": parsed, "count": num_carousels}
    except Exception as e:
        logger.error(f"Carousel generation failed: {e}")
        raise HTTPException(status_code=500, detail="Carousel generation failed")


# ---------------------------------------------------------------------------
# Campaign Strategy (SBA SOP Aligned)
# ---------------------------------------------------------------------------

@router.post("/campaign-strategy")
def generate_campaign_strategy(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a complete Meta Ads campaign strategy following SBA SOPs."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedures = data.get("procedures", ["aesthetic treatments"])
    budget = data.get("monthly_budget", "50000")
    location = data.get("location", "")
    goals = data.get("goals", "lead generation")

    prompt = f"""You are a Meta Ads strategist for aesthetic clinics strictly following the SBA (Skin Business Accelerator) methodology.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Procedures to Advertise: {', '.join(procedures) if isinstance(procedures, list) else procedures}
Monthly Budget: Rs. {budget}
Location: {location or 'India'}
Goals: {goals}

SBA CORE PRINCIPLES YOU MUST FOLLOW:

1. FUNNEL STRATEGY (SBA SOP):
   - PRIMARY FUNNEL: WhatsApp Click-to-Chat ads. This is the #1 recommended funnel for aesthetic clinics in India. Patients prefer WhatsApp over forms. Use "Send Message" CTA pointing to WhatsApp.
   - SECONDARY FUNNEL: Progressive multi-step lead forms on Meta. Use progressive disclosure: Step 1 asks name + phone, Step 2 asks procedure interest + preferred date. Reduces form abandonment by 40-60%.
   - TERTIARY FUNNEL: Google Search Ads with dedicated landing pages for high-intent keywords. Landing page should have WhatsApp CTA button prominently placed.
   - NEVER recommend direct Meta lead forms as primary. They generate low-quality leads. Always recommend WhatsApp-first or progressive forms.

2. CAMPAIGN STRUCTURE (SBA SOP):
   - Separate campaigns by procedure category, not by audience
   - Use Advantage+ placements, let Meta optimize
   - Set campaign budget optimization (CBO) at campaign level
   - Minimum 3 ad creatives per ad set (1 video, 1 image, 1 carousel)

3. TARGETING (SBA SOP):
   - Start broad (age + gender + location only) for Advantage+ to learn
   - Layer interests only if budget is below Rs. 30,000/month
   - Create lookalike audiences from converted leads after 50+ conversions
   - Always exclude existing patients and converted leads

4. CREATIVE STRATEGY (SBA SOP):
   - 60% video content (talking head by doctor + patient testimonials)
   - 25% image ads (before/after concepts, offer announcements, authority posts)
   - 15% carousel ads (procedure education, FAQ, social proof)
   - All creatives must feature the doctor's face or voice for trust building
   - Hinglish scripts for North India, regional language for South India

5. BUDGET ALLOCATION (SBA SOP):
   - 70% on prospecting (cold audiences, WhatsApp click-to-chat)
   - 20% on retargeting (video viewers, page visitors, form abandoners)
   - 10% on brand awareness (reach campaigns for local area)

Create a complete Meta Ads campaign strategy covering:

1. campaign_structure: Array of campaigns with name, objective, daily_budget, procedures_covered, funnel_type (whatsapp_click/progressive_form/landing_page)
2. ad_set_strategy: Targeting for each ad set including age, gender, location radius, interest layers (if applicable), custom audiences, lookalike setup
3. funnel_recommendation: Detailed funnel architecture explaining WhatsApp click-to-chat as primary, progressive forms as secondary, and when to use Google landing pages. Include WhatsApp auto-reply setup notes.
4. creative_mix: Exact split with specific creative types for each campaign
5. testing_plan: Structured A/B testing roadmap. Week 1 test creatives, Week 2 test audiences, Week 3 test offers, Week 4 test placements
6. budget_allocation: Day-by-day budget ramp plan for first 14 days. Start at 50% budget, scale to 100% after optimization signals.
7. retargeting_setup: Warm audience segments to create (video viewers 50%+, page visitors 7 days, WhatsApp openers, form abandoners). Retargeting ad content for each segment.
8. kpi_targets: Expected benchmarks for this procedure category and location. CPL range, CTR range, WhatsApp conversation rate, consultation booking rate, show-up rate.
9. scaling_plan: Clear scaling triggers (scale when CPL is below target for 3+ days). Budget increase rules (20% every 3 days). New ad set expansion criteria.
10. first_week_checklist: Detailed day-by-day action plan for first 7 days post-launch with specific checks and optimizations.
11. whatsapp_integration: How to set up WhatsApp Business API for ad responses, auto-reply message templates, AI chatbot handoff flow, and lead capture into CRM.
12. google_ads_complement: How to complement this Meta strategy with Google Search Ads targeting high-intent keywords for the same procedures. Include recommended Google Ads budget split.

Format as JSON object with each section as a key."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        result = _call_claude(prompt, 6000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "ads", "meta_campaign_strategy_generated",
                     {"procedures": procedures, "budget": budget, "goals": goals, "location": location},
                     current_user.email)
        return {"strategy": parsed}
    except Exception as e:
        logger.error(f"Campaign strategy generation failed: {e}")
        raise HTTPException(status_code=500, detail="Strategy generation failed")


# ---------------------------------------------------------------------------
# Retargeting Setup (Now Operational with Full Inputs)
# ---------------------------------------------------------------------------

@router.post("/retargeting-plan")
def generate_retargeting_plan(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate retargeting audience and ad plan with procedure-specific strategy."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedure = data.get("procedure", "aesthetic treatments")
    monthly_budget = data.get("monthly_budget", "10000")
    location = data.get("location", "")
    current_campaigns = data.get("current_campaigns", "Meta Ads prospecting")
    pixel_installed = data.get("pixel_installed", "yes")
    website_traffic = data.get("website_traffic", "moderate")
    language = data.get("language", "Hinglish")

    prompt = f"""You are a Meta Ads retargeting expert for aesthetic clinics following SBA methodology.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Primary Procedure: {procedure}
Retargeting Budget: Rs. {monthly_budget}/month
Location: {location or 'India'}
Current Active Campaigns: {current_campaigns}
Meta Pixel Installed: {pixel_installed}
Website Traffic Level: {website_traffic} (low = under 500 visitors/month, moderate = 500-2000, high = 2000+)
Preferred Language: {language}

Create a comprehensive, procedure-specific retargeting plan with:

1. custom_audiences: Array of audiences to create, each with:
   - name: Descriptive audience name
   - source: Where the data comes from (website, video_views, page_engagement, lead_form, instagram, whatsapp)
   - retention_days: How many days to keep users in this audience
   - estimated_size: Expected audience size based on traffic level
   - priority: high/medium/low
   - description: What this audience represents and why it matters

2. retargeting_ad_sets: Array of ad sets, each with:
   - ad_set_name: Descriptive name
   - audience_name: Which custom audience to target
   - ad_type: video/image/carousel
   - messaging_angle: What psychological approach to use
   - budget_percentage: What % of retargeting budget to allocate
   - frequency_cap: Maximum times to show per day
   - schedule: How long to run this ad set

3. retargeting_scripts: 4 retargeting video scripts specifically for {procedure}:
   - Script 1: Urgency/scarcity angle (limited slots, seasonal offer)
   - Script 2: Social proof angle (other patients like them chose this)
   - Script 3: Educational angle (addressing the #1 concern that stopped them)
   - Script 4: Direct offer angle (special price for returning visitors)
   Each script should have: title, hook, full_script (in {language}), cta, duration

4. retargeting_ad_copy: 4 ad copy sets specifically for warm retargeting of {procedure} leads:
   - Each with: primary_text, headline, description, angle, targeting_note

5. whatsapp_retargeting: How to retarget WhatsApp conversation starters who did not book:
   - Follow-up message sequences (Day 1, Day 3, Day 7)
   - AI Employee re-engagement prompts
   - Special offers for WhatsApp retargeting

6. exclusion_audiences: Who to exclude from retargeting with reasoning

7. frequency_caps: Recommended frequency limits per audience segment with reasoning

8. sequence_strategy: How to sequence retargeting over 30 days:
   - Day 1-3: Immediate follow-up (highest intent)
   - Day 4-7: Educational content + soft CTA
   - Day 8-14: Social proof + offers
   - Day 15-30: Final push with best offer
   Include which ad creative to show at each stage.

9. pixel_events: Which Meta Pixel events to set up for better retargeting:
   - Standard events (ViewContent, Lead, Schedule, CompleteRegistration)
   - Custom events for clinic websites (ProcedurePageView, PricingPageView, DoctorProfileView)
   - How to set up each event

10. measurement: How to measure retargeting success:
    - Key metrics to track
    - Expected benchmarks for retargeting campaigns
    - When to pause vs scale retargeting

Format as JSON object."""

    try:
        prompt = _apply_regenerate_changes(prompt, data)
        result = _call_claude(prompt, 5000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "ads", "meta_retargeting_plan_generated",
                     {"procedure": procedure, "budget": monthly_budget, "location": location},
                     current_user.email)
        return {"plan": parsed}
    except Exception as e:
        logger.error(f"Retargeting plan generation failed: {e}")
        raise HTTPException(status_code=500, detail="Retargeting plan generation failed")
