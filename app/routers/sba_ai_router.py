"""
CallCoach CRM - SBA AI Router
Business coaching, decision-making, and deep audits powered by Claude.
"""
import json
import logging
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Clinic
from app.auth import get_current_user
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sba-ai", tags=["sba-ai"])

# ---------------------------------------------------------------------------
# SBA AI System Prompt - Business Coach & Auditor
# ---------------------------------------------------------------------------

SBA_SYSTEM_PROMPT = """You are SBA AI, the intelligent business coach and strategic advisor built into the Skin Business Accelerator (SBA) CRM platform.

## WHO YOU ARE
You are a senior-level business strategist, growth consultant, and operations auditor specifically trained for the aesthetic clinic, dermatology, hair transplant, and cosmetic surgery industry. You operate as an extension of the SBA consulting methodology.

## YOUR CAPABILITIES
1. **Business Decision Making** - Help clinic owners and marketing teams make data-driven decisions about growth, investment, hiring, and strategy
2. **Deep Business Audits** - Conduct thorough audits of marketing performance, operations, revenue systems, and growth infrastructure
3. **Strategic Planning** - Build growth plans, quarterly roadmaps, revenue projections, and expansion strategies
4. **Marketing Strategy** - Advise on Meta Ads, Google Ads, SEO, organic content, and patient acquisition
5. **Sales & Conversion** - Optimize front desk systems, consultation frameworks, and lead conversion
6. **Operations** - Improve team structure, SOPs, CRM workflows, and automation systems
7. **Financial Analysis** - Revenue planning, pricing models, profitability analysis, and budgeting

## SBA METHODOLOGY & FRAMEWORKS

### Patient Acquisition Framework
- Meta Ads: Hook-based video scripts, carousel ads, story ads targeting local demographics
- Google Ads: Intent-based search campaigns for specific procedures (hair transplant, PRP, laser, botox, etc.)
- SEO & GMB: Local SEO dominance, Google Business Profile optimization, citation building
- Content: Authority-building content for doctors, educational videos, patient journey content

### Conversion System
- Front desk SOP: Every call is a potential conversion, structured greeting, qualification, booking
- Consultation framework: Build trust, educate, present options, handle objections, close
- WhatsApp nurture: Automated follow-up sequences, reminder systems, re-engagement campaigns
- CRM pipeline: Lead tracking from first touch to procedure completion

### Revenue Growth Model
- Increase walk-ins through paid + organic acquisition
- Improve conversion rates through front desk + consultation optimization
- Increase average ticket size through treatment bundling and upselling
- Build retention through follow-up systems and loyalty programs
- Build authority through personal branding of doctors

### Audit Framework
When conducting audits, analyze:
1. **Marketing Audit**: Ad spend efficiency, CPL, CPA, ROAS, creative performance, targeting accuracy
2. **Operations Audit**: Team structure, SOPs adherence, tool utilization, bottlenecks
3. **Revenue Audit**: Revenue per lead, conversion rates at each stage, patient lifetime value
4. **Content Audit**: Brand positioning, content consistency, authority building, engagement metrics
5. **Technology Audit**: CRM usage, automation gaps, data tracking completeness

## RESPONSE STYLE
- Be direct, strategic, and actionable
- Use tables when comparing data or options
- Use bullet points for clarity
- Always tie recommendations to revenue impact
- Think like a consultant billing $500/hour - every response should deliver real value
- Avoid generic advice - be specific to the aesthetic/medical clinic industry
- When auditing, provide scores (1-10) for each area with specific improvement actions
- Always prioritize practical implementation over theory

## AUDIT MODES
When asked for an audit, follow this structure:
1. **Current State Assessment** - What exists today (score 1-10)
2. **Gap Analysis** - What is missing vs. best practice
3. **Priority Actions** - Top 3-5 immediate fixes (ranked by revenue impact)
4. **90-Day Roadmap** - Phased implementation plan
5. **Expected Impact** - Revenue/growth projections from improvements

## IMPORTANT RULES
- You have deep knowledge of the Indian aesthetic and dermatology clinic market
- You understand pricing dynamics in Tier 1, 2, and 3 Indian cities
- You know the competitive landscape of aesthetic clinics
- You can advise on both English and Hindi/Hinglish marketing
- Always frame advice in terms of ROI and patient acquisition cost
- When you don't have specific data, say so and explain what data would be needed
- Never give vague advice like "improve your marketing" - always specify exactly what to do

You are talking to clinic owners, marketing managers, or SBA team members. Treat them as smart professionals who want actionable insights, not hand-holding."""


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation: Optional[List[ChatMessage]] = []
    mode: Optional[str] = "coach"  # coach, audit, strategy, quick

class AuditRequest(BaseModel):
    audit_type: str  # marketing, operations, revenue, content, technology, full
    context: Optional[str] = ""
    clinic_data: Optional[dict] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat")
async def sba_ai_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chat with SBA AI business coach."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    # Get clinic context if available
    clinic_context = ""
    if current_user.clinic_id:
        clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
        if clinic:
            clinic_context = f"\n\nCLINIC CONTEXT:\n- Name: {clinic.name}\n- City: {clinic.city or 'Not set'}\n- Specialty: {clinic.specialty or 'General'}\n- Email: {clinic.email or 'Not set'}"

    # Build mode-specific instruction
    mode_instructions = {
        "coach": "\n\nYou are in COACHING mode. Provide strategic business advice, answer questions, and guide decision-making.",
        "audit": "\n\nYou are in AUDIT mode. Conduct thorough analysis, score current state (1-10), identify gaps, and provide actionable improvement plans with timelines.",
        "strategy": "\n\nYou are in STRATEGY mode. Build detailed strategic plans, roadmaps, and frameworks. Be comprehensive and implementation-focused.",
        "quick": "\n\nYou are in QUICK ANSWER mode. Give concise, direct answers. No fluff. Maximum 3-4 bullet points."
    }

    system = SBA_SYSTEM_PROMPT + clinic_context + mode_instructions.get(req.mode, mode_instructions["coach"])

    # Build messages array
    messages = []
    for msg in (req.conversation or []):
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
        )

        reply = response.content[0].text if response.content else "No response generated."

        return {
            "reply": reply,
            "mode": req.mode,
            "model": ANTHROPIC_MODEL,
            "tokens_used": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            }
        }

    except Exception as e:
        logger.error(f"SBA AI chat error: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.post("/audit")
async def sba_ai_audit(
    req: AuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a structured SBA audit."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    clinic_context = ""
    if current_user.clinic_id:
        clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
        if clinic:
            clinic_context = f"\nClinic: {clinic.name} | City: {clinic.city or 'N/A'} | Specialty: {clinic.specialty or 'General'}"

    audit_prompts = {
        "marketing": "Conduct a comprehensive MARKETING AUDIT for this clinic. Cover: paid ads (Meta + Google), organic content, SEO/GMB, brand positioning, patient acquisition funnel. Score each area 1-10.",
        "operations": "Conduct a comprehensive OPERATIONS AUDIT. Cover: team structure, SOPs, CRM utilization, automation, communication workflows, reporting systems. Score each area 1-10.",
        "revenue": "Conduct a comprehensive REVENUE AUDIT. Cover: revenue per lead, conversion rates (inquiry to consultation, consultation to procedure), average ticket size, patient retention, lifetime value. Score each area 1-10.",
        "content": "Conduct a comprehensive CONTENT AUDIT. Cover: Instagram presence, YouTube strategy, doctor authority content, patient testimonials, educational content, brand consistency. Score each area 1-10.",
        "technology": "Conduct a comprehensive TECHNOLOGY AUDIT. Cover: CRM setup, automation workflows, WhatsApp integration, lead tracking, reporting dashboards, data hygiene. Score each area 1-10.",
        "full": "Conduct a FULL 360-DEGREE BUSINESS AUDIT covering all areas: Marketing, Operations, Revenue, Content, and Technology. Score each major area 1-10, identify the top 5 revenue-impacting gaps, and provide a 90-day priority action plan."
    }

    audit_instruction = audit_prompts.get(req.audit_type, audit_prompts["full"])
    user_context = f"\n\nAdditional context provided: {req.context}" if req.context else ""
    clinic_data_str = f"\n\nClinic data: {json.dumps(req.clinic_data)}" if req.clinic_data else ""

    full_prompt = f"""{audit_instruction}{clinic_context}{user_context}{clinic_data_str}

Structure your audit as:
1. Executive Summary (2-3 lines)
2. Area-by-Area Scores (table format)
3. Top Gaps (ranked by revenue impact)
4. Priority Actions (next 30 days)
5. 90-Day Roadmap
6. Expected Revenue Impact"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SBA_SYSTEM_PROMPT + "\n\nYou are in AUDIT mode. Be thorough, specific, and score everything 1-10.",
            messages=[{"role": "user", "content": full_prompt}],
        )

        reply = response.content[0].text if response.content else "Audit could not be generated."

        return {
            "audit": reply,
            "audit_type": req.audit_type,
            "model": ANTHROPIC_MODEL,
            "generated_at": datetime.utcnow().isoformat(),
            "tokens_used": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            }
        }

    except Exception as e:
        logger.error(f"SBA AI audit error: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.get("/suggestions")
async def get_ai_suggestions(
    current_user: User = Depends(get_current_user),
):
    """Get quick-start suggestion prompts for SBA AI."""
    return {
        "coach": [
            "How should I allocate a 50K monthly ad budget between Meta and Google for a hair transplant clinic?",
            "What's the ideal team structure for a clinic doing 20L monthly revenue?",
            "How do I price a PRP package to maximize conversions?",
            "What KPIs should I track weekly for my clinic marketing?",
        ],
        "audit": [
            "Run a full marketing audit for my clinic",
            "Audit my front desk conversion process",
            "Analyze my Meta Ads performance and suggest optimizations",
            "Review my clinic's content strategy",
        ],
        "strategy": [
            "Build a 90-day growth plan to go from 10L to 25L monthly revenue",
            "Create a patient acquisition strategy for a new clinic launch",
            "Design a doctor personal branding roadmap",
            "Plan a multi-location expansion strategy",
        ],
        "quick": [
            "What's a good CPL for hair transplant leads in Delhi?",
            "Best time to post on Instagram for clinic content?",
            "How many follow-ups should we do before marking a lead cold?",
            "What conversion rate should I expect from consultation to procedure?",
        ]
    }
