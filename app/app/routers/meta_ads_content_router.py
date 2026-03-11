"""
CallCoach CRM - Meta Ads Content Generation Router
AI-powered generation of video scripts, ad copy, image ad prompts, carousel prompts.
Following SBA Meta Ads SOP methodology.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity
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
# Image Ad Prompts (AI image generation prompts)
# ---------------------------------------------------------------------------

@router.post("/image-prompts")
def generate_image_prompts(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI image creation prompts for Meta Ads."""
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

IMPORTANT: Do NOT include real people's faces. Focus on abstract beauty, clinic interiors, treatment concepts, lifestyle shots, and graphical elements.

Format as JSON array."""

    try:
        result = _call_claude(prompt, 3000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "script_generation", "meta_image_prompts_generated",
                     {"procedure": procedure, "num_prompts": num_prompts, "image_type": image_type},
                     current_user.email)
        return {"prompts": parsed, "count": num_prompts}
    except Exception as e:
        logger.error(f"Image prompt generation failed: {e}")
        raise HTTPException(status_code=500, detail="Image prompt generation failed")


# ---------------------------------------------------------------------------
# Carousel Prompts
# ---------------------------------------------------------------------------

@router.post("/carousel-prompts")
def generate_carousel_prompts(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate carousel ad concepts for Meta Ads."""
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
- cta: Call to action for the carousel
- target_objective: awareness, consideration, or conversion

Format as JSON array."""

    try:
        result = _call_claude(prompt, 4000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "script_generation", "meta_carousel_prompts_generated",
                     {"procedure": procedure, "num_carousels": num_carousels, "carousel_type": carousel_type},
                     current_user.email)
        return {"carousels": parsed, "count": num_carousels}
    except Exception as e:
        logger.error(f"Carousel generation failed: {e}")
        raise HTTPException(status_code=500, detail="Carousel generation failed")


# ---------------------------------------------------------------------------
# Campaign Strategy
# ---------------------------------------------------------------------------

@router.post("/campaign-strategy")
def generate_campaign_strategy(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a complete Meta Ads campaign strategy."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    procedures = data.get("procedures", ["aesthetic treatments"])
    budget = data.get("monthly_budget", "50000")
    location = data.get("location", "")
    goals = data.get("goals", "lead generation")

    prompt = f"""You are a Meta Ads strategist for aesthetic clinics following the SBA (Skin Business Accelerator) methodology.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Procedures to Advertise: {', '.join(procedures) if isinstance(procedures, list) else procedures}
Monthly Budget: Rs. {budget}
Location: {location or 'India'}
Goals: {goals}

Create a complete Meta Ads campaign strategy covering:

1. campaign_structure: Array of campaigns with name, objective, daily_budget, procedures_covered
2. ad_set_strategy: Targeting recommendations including age, gender, interests, locations, lookalike audiences, custom audiences
3. funnel_recommendation: Which funnel type to use (direct_lead_form, landing_page, whatsapp_click, messenger) with reasoning
4. creative_mix: Recommended split of video vs image vs carousel ads (percentages)
5. testing_plan: What to A/B test first, second, third
6. budget_allocation: How to split budget across campaigns and ad sets
7. retargeting_setup: Audiences to create and retarget (website visitors, video viewers, page engagers, lead form openers)
8. kpi_targets: Expected CPL, CTR, conversion rate benchmarks for this niche
9. scaling_plan: When and how to scale (at what CPL, what budget increases, when to add new ad sets)
10. first_week_checklist: Day-by-day actions for the first 7 days after launch

Format as JSON object with each section as a key."""

    try:
        result = _call_claude(prompt, 4000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "ads", "meta_campaign_strategy_generated",
                     {"procedures": procedures, "budget": budget, "goals": goals},
                     current_user.email)
        return {"strategy": parsed}
    except Exception as e:
        logger.error(f"Campaign strategy generation failed: {e}")
        raise HTTPException(status_code=500, detail="Strategy generation failed")


# ---------------------------------------------------------------------------
# Retargeting Setup
# ---------------------------------------------------------------------------

@router.post("/retargeting-plan")
def generate_retargeting_plan(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate retargeting audience and ad plan."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    prompt = f"""You are a Meta Ads retargeting expert for aesthetic clinics.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}

Create a comprehensive retargeting plan with:

1. custom_audiences: Array of audiences to create, each with name, source (website, video, page, lead_form, instagram), retention_days, description
2. retargeting_ad_sets: Array of ad sets targeting these audiences, each with audience_name, ad_type (video/image/carousel), messaging_angle, budget_percentage
3. retargeting_scripts: 3 short retargeting video script outlines for people who showed interest but did not convert
4. retargeting_ad_copy: 3 ad copy variations designed specifically for warm retargeting
5. exclusion_audiences: Who to exclude from retargeting
6. frequency_caps: Recommended frequency limits
7. sequence_strategy: How to sequence retargeting (Day 1-3, Day 4-7, Day 8-14, Day 15-30)

Format as JSON object."""

    try:
        result = _call_claude(prompt, 3000)
        parsed = _parse_json_response(result)
        log_activity(db, current_user.clinic_id, "ads", "meta_retargeting_plan_generated",
                     {}, current_user.email)
        return {"plan": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Retargeting plan generation failed")
