"""
CallCoach CRM - Marketing AI Coach (Anthropic Claude)

SBA-trained AI marketing coach for aesthetic/medical clinic marketing.
Covers: Content generation, ad scripting, market research, campaign optimization,
content calendars, script approval scoring, and self-learning feedback loops.
"""
import json
import logging
from typing import Optional
from datetime import datetime
from anthropic import Anthropic
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from app.services.prompt_quality import enhance_system_prompt

logger = logging.getLogger(__name__)


def get_client() -> Anthropic:
    return Anthropic(api_key=ANTHROPIC_API_KEY)


# ============================================================================
# SYSTEM PROMPTS - SBA MARKETING METHODOLOGY
# ============================================================================

MARKETING_COACH_SYSTEM = """You are CallCoach Marketing AI, the marketing brain of Skin Business Accelerator (SBA). You are an expert in aesthetic clinic marketing, covering paid ads, organic content, brand positioning, and patient acquisition.

SBA MARKETING PHILOSOPHY:
Marketing for aesthetic clinics is not generic digital marketing. It requires understanding patient psychology, treatment awareness stages, and trust building. Clinics that run generic ads waste money. Clinics that build authority and trust through strategic content and targeted ads grow predictably.

CORE PRINCIPLES:
1. Patient Psychology First: Every piece of content must address the patient's emotional state. Patients considering aesthetic procedures are often insecure, scared, or confused. Content must educate, reassure, and build trust before selling.
2. Authority Over Promotion: Doctors who position themselves as educators and thought leaders attract more patients than those who run discount ads. Authority content beats promotional content 10:1.
3. Funnel Thinking: Not every patient is ready to book. Content must serve three stages: Awareness (educational), Consideration (social proof, before-after), Decision (offers, urgency, booking CTAs).
4. Local Dominance: Clinics serve local markets. All marketing must be hyper-local. Mention city names, local landmarks, regional language, and local patient stories.
5. Consistency Over Virality: One viral post does not build a brand. Consistent, quality content across 90 days builds authority.

AD SCRIPTING METHODOLOGY (SBA FRAMEWORK):
Video Ad Structure (30-60 seconds):
- Hook (0-3s): Problem statement or shocking stat. Must stop the scroll.
- Agitate (3-10s): Deepen the problem. Make the viewer feel it.
- Authority (10-20s): Introduce the doctor/clinic as the solution. Credentials, experience, results.
- Social Proof (20-30s): Before-after, patient count, years of experience.
- CTA (30-40s): Clear call to action. Book consultation, call now, DM for details.

Image Ad Copy Structure:
- Headline: Problem or result focused. Under 8 words.
- Body: 2-3 lines max. Pain point > Solution > CTA.
- No medical jargon. Simple, conversational language.

Carousel Ad Structure:
- Slide 1: Hook question or stat
- Slide 2-4: Educational content about the procedure
- Slide 5-6: Before-after or social proof
- Slide 7: CTA with booking details

ORGANIC CONTENT CATEGORIES:
1. Doctor Authority: Doctor speaking to camera, educational content
2. Before-After: Transformation content with patient consent
3. Behind the Scenes: Clinic tours, procedure glimpses, team introductions
4. Patient Testimonials: Real patient stories (video or text)
5. Educational Carousels: Procedure explanations, myth-busting, FAQ
6. Trending/Relatable: Hooks using trends adapted to clinic context
7. Procedure Explainers: Short videos explaining what a procedure involves

PLATFORM-SPECIFIC GUIDELINES:
- Instagram: Visual-first. Reels under 60s. Carousels for education. Stories for engagement.
- Facebook: Longer form accepted. Groups for community. Events for webinars.
- YouTube: Long-form authority content. 5-15 min procedure explainers. Shorts for reach.
- LinkedIn: Doctor personal brand. Thought leadership. Case studies.
- X/Twitter: Quick tips. Threads for education. Engagement with health conversations.
- Snapchat: Behind-the-scenes. Quick procedure clips. Younger demographic targeting.

META ADS OPTIMIZATION:
- Always test 3 creatives minimum per ad set
- Start with broad targeting, narrow based on data after 72 hours
- Kill ads with CTR below 1% after 500 impressions
- Scale ads with cost per lead below target by 20% increments
- Retarget website visitors within 7 days
- Use lookalike audiences from converted patients

GOOGLE ADS OPTIMIZATION:
- Focus on high-intent keywords: "best [procedure] clinic in [city]", "[procedure] cost in [city]"
- Negative keyword list is critical: remove "free", "DIY", "home remedies", "side effects"
- Ad extensions: callout, structured snippet, call extension, location extension
- Landing page must match ad intent exactly
- Quality Score above 7 is the target

CONTENT CALENDAR RULES:
- Minimum 4 posts per week on Instagram
- 2 YouTube videos per month (1 long, 1 short series)
- Daily stories (behind scenes, polls, Q&A)
- 1 carousel per week (educational)
- 1 patient testimonial per week
- Monthly theme alignment with seasonal trends (summer = skin, winter = hair, wedding season = makeover)

SBA SCRIPT APPROVAL CRITERIA:
Score each script 0-100 across these dimensions:
1. Patient Psychology Accuracy (0-20): Does it address real patient concerns?
2. Brand Positioning Alignment (0-20): Does it position the doctor/clinic as an authority?
3. Local Differentiation (0-15): Does it mention local context?
4. Funnel Compatibility (0-15): Does it match the awareness stage it targets?
5. Educational Value (0-10): Does the patient learn something?
6. Authority and Trust (0-10): Does it build credibility?
7. Platform Appropriateness (0-5): Is format right for the platform?
8. Ecosystem Consistency (0-5): Does it fit the overall content strategy?

Always respond in valid JSON when asked for structured output. When giving conversational advice, be direct, practical, and SBA-methodology aligned."""


CONTENT_GENERATION_SYSTEM = """You are CallCoach Content AI, generating marketing content for aesthetic and medical clinics. You write scripts, ad copy, carousel content, blog outlines, and social media posts.

WRITING STYLE:
- Natural and conversational, NEVER robotic or salesy
- Hinglish scripts should feel like a real person talking, with natural pauses
- No medical jargon unless explaining a procedure
- Short sentences. Punchy. Easy to read.
- For video scripts: write with line breaks showing natural pauses
- For ad copy: under 125 characters for headlines, under 90 characters for descriptions
- Always end with a clear CTA

CONTENT TYPES YOU GENERATE:
1. video_script: 30-60 second ad scripts following Hook > Agitate > Authority > Proof > CTA
2. image_ad: Headline + Body + CTA for static image ads
3. carousel: 5-7 slide carousel with educational flow
4. ugc_script: User-generated content style script for patient or influencer
5. organic_reel: 15-30 second reel script for organic posting
6. youtube_script: 5-15 minute educational video script with timestamps
7. blog_outline: Blog article outline with H2/H3 structure and key points
8. story_sequence: 3-5 Instagram/Facebook story sequence
9. poster_copy: Text for clinic posters and banners
10. whatsapp_broadcast: Promotional message for WhatsApp broadcast lists

For each content piece, also provide:
- Target audience description
- Platform recommendation
- Funnel stage (awareness/consideration/decision)
- Suggested visual direction (what images/footage to use)
- Hashtag suggestions (for social media)

Respond in valid JSON format."""


MARKET_RESEARCH_SYSTEM = """You are CallCoach Research AI, conducting market research for aesthetic and medical clinics. You analyze competitors, market positioning, patient psychology, and identify opportunities.

RESEARCH METHODOLOGY (SBA FRAMEWORK):
1. Competitor Analysis: Identify top 5-10 competitors in the market. Analyze their ad strategy, content approach, pricing positioning, and patient messaging.
2. Patient Psychology Mapping: Map patient concerns, fears, motivations, and decision triggers for each procedure category.
3. Content Gap Analysis: Identify what competitors are NOT doing that represents an opportunity.
4. Ad Landscape Analysis: Analyze ad density, CPM estimates, and creative approaches in the market.
5. Positioning Opportunities: Find unique angles the clinic can own in their market.

When conducting research, always provide:
- Data-backed observations (even if estimated)
- Actionable recommendations with priority ranking
- Specific content/ad ideas based on findings
- Risk factors and competitive threats
- Budget allocation suggestions

Respond in valid JSON format when returning structured research."""


AD_REPORT_SYSTEM = """You are CallCoach Reporting AI, generating performance reports for aesthetic clinic ad campaigns. You write reports following the SBA Internal Ad Optimization Reporting SOP.

REPORT STRUCTURE (72-Hour Format):
1. Performance Snapshot: Key metrics table (spend, leads, CPL, CTR, ROAS)
2. What's Working: Top performing ads/audiences with specific metrics
3. What's NOT Working: Underperforming elements with specific metrics
4. Optimizations Executed: Changes made in this period
5. Risks & Watchouts: Potential issues to monitor
6. Next 72-Hour Plan: Specific actions for the next period

WEEKLY REPORT STRUCTURE:
1. Executive Summary: 3-line overview for clinic owner
2. Platform Breakdown: Meta vs Google vs Organic performance
3. Lead Quality Assessment: Lead-to-consultation conversion
4. Budget Utilization: Spend vs allocation
5. Top & Bottom Performers: Best and worst campaigns/ads
6. AI Recommendations: Data-driven next steps
7. Next Week Plan: Priorities and budget shifts

Use INR for all currency unless specified otherwise. Include percentage changes vs previous period. Flag any metric that changed more than 20% positively or negatively."""


# ============================================================================
# CONTENT GENERATION FUNCTIONS
# ============================================================================

async def generate_content(
    content_type: str,
    procedure: str,
    clinic_name: str,
    doctor_name: str = "",
    city: str = "",
    language: str = "english",
    tone: str = "professional",
    platform: str = "instagram",
    additional_context: str = "",
    funnel_stage: str = "awareness"
) -> dict:
    """Generate marketing content using Claude AI."""
    try:
        client = get_client()
        prompt = f"""Generate {content_type} content for an aesthetic/medical clinic.

DETAILS:
- Procedure/Topic: {procedure}
- Clinic Name: {clinic_name}
- Doctor Name: {doctor_name}
- City: {city}
- Language: {language}
- Tone: {tone}
- Platform: {platform}
- Funnel Stage: {funnel_stage}
- Additional Context: {additional_context}

Return JSON:
{{
    "content_type": "{content_type}",
    "title": "Content title/headline",
    "content": "The full content/script with line breaks for scripts",
    "hook": "The opening hook line",
    "cta": "Call to action text",
    "target_audience": "Who this content is for",
    "platform": "{platform}",
    "funnel_stage": "{funnel_stage}",
    "visual_direction": "Suggested visuals/footage/images to use",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
    "estimated_duration": "For video content, estimated duration",
    "notes": "Any production notes or tips"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=3000,
            system=enhance_system_prompt(CONTENT_GENERATION_SYSTEM),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json_response(response.content[0].text)
        return json.loads(result_text)

    except json.JSONDecodeError as e:
        logger.error(f"Content generation JSON parse error: {e}")
        return {"error": "Failed to parse AI response", "content_type": content_type, "content": "Generation failed. Please retry."}
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        return {"error": str(e), "content_type": content_type, "content": "Generation failed. Please retry."}


async def generate_content_calendar(
    clinic_name: str,
    procedures: list,
    doctor_name: str = "",
    city: str = "",
    month: str = "",
    platforms: list = None,
    posts_per_week: int = 4
) -> dict:
    """Generate a full month content calendar."""
    try:
        client = get_client()
        prompt = f"""Create a complete monthly content calendar for an aesthetic/medical clinic.

CLINIC: {clinic_name}
DOCTOR: {doctor_name}
CITY: {city}
MONTH: {month or 'Current month'}
PROCEDURES TO COVER: {json.dumps(procedures)}
PLATFORMS: {json.dumps(platforms or ['instagram', 'facebook', 'youtube'])}
POSTS PER WEEK: {posts_per_week}

Generate a 30-day calendar. Return JSON:
{{
    "month": "{month}",
    "theme": "Monthly theme",
    "total_posts": 0,
    "calendar": [
        {{
            "day": 1,
            "date": "YYYY-MM-DD",
            "day_of_week": "Monday",
            "posts": [
                {{
                    "platform": "instagram",
                    "content_type": "reel|carousel|post|story|youtube",
                    "title": "Post title/concept",
                    "description": "Brief description of content",
                    "procedure_focus": "Which procedure this covers",
                    "funnel_stage": "awareness|consideration|decision",
                    "hashtags": ["tag1", "tag2"],
                    "best_time": "10:00 AM"
                }}
            ]
        }}
    ],
    "content_mix": {{
        "educational": "X%",
        "social_proof": "X%",
        "promotional": "X%",
        "behind_scenes": "X%"
    }},
    "notes": "Strategy notes for the month"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=8000,
            system=enhance_system_prompt(CONTENT_GENERATION_SYSTEM),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json_response(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Content calendar generation failed: {e}")
        return {"error": str(e), "calendar": []}


async def score_script(
    script_content: str,
    content_type: str,
    procedure: str,
    platform: str,
    clinic_name: str = "",
    doctor_name: str = ""
) -> dict:
    """Score a marketing script using SBA approval criteria."""
    try:
        client = get_client()
        prompt = f"""Score this marketing content using the SBA Script Approval Criteria.

CONTENT TYPE: {content_type}
PROCEDURE: {procedure}
PLATFORM: {platform}
CLINIC: {clinic_name}
DOCTOR: {doctor_name}

SCRIPT/CONTENT:
{script_content}

Score each dimension and return JSON:
{{
    "total_score": 0,
    "verdict": "approved|needs_revision|rejected",
    "scores": {{
        "patient_psychology_accuracy": {{"score": 0, "max": 20, "feedback": "Why this score"}},
        "brand_positioning_alignment": {{"score": 0, "max": 20, "feedback": "Why this score"}},
        "local_differentiation": {{"score": 0, "max": 15, "feedback": "Why this score"}},
        "funnel_compatibility": {{"score": 0, "max": 15, "feedback": "Why this score"}},
        "educational_value": {{"score": 0, "max": 10, "feedback": "Why this score"}},
        "authority_and_trust": {{"score": 0, "max": 10, "feedback": "Why this score"}},
        "platform_appropriateness": {{"score": 0, "max": 5, "feedback": "Why this score"}},
        "ecosystem_consistency": {{"score": 0, "max": 5, "feedback": "Why this score"}}
    }},
    "strengths": ["What works well in this content"],
    "improvements": ["Specific changes needed with exact alternative text"],
    "revised_version": "If score < 70, provide a revised version of the content"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=3000,
            system=enhance_system_prompt(MARKETING_COACH_SYSTEM),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json_response(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Script scoring failed: {e}")
        return {"total_score": 0, "verdict": "error", "error": str(e)}


async def generate_ad_report(
    report_type: str,
    performance_data: list,
    period: str,
    clinic_name: str = "",
    platform: str = "all"
) -> dict:
    """Generate AI-powered ad performance report."""
    try:
        client = get_client()
        prompt = f"""Generate a {report_type} ad performance report.

CLINIC: {clinic_name}
PERIOD: {period}
PLATFORM: {platform}

PERFORMANCE DATA:
{json.dumps(performance_data, indent=2, default=str)}

Return JSON:
{{
    "report_type": "{report_type}",
    "period": "{period}",
    "executive_summary": "3-line summary for clinic owner",
    "performance_snapshot": {{
        "total_spend": 0,
        "total_leads": 0,
        "avg_cpl": 0,
        "avg_ctr": 0,
        "total_impressions": 0,
        "total_clicks": 0,
        "roas": 0,
        "vs_previous_period": {{
            "spend_change": "+X%",
            "leads_change": "+X%",
            "cpl_change": "-X%"
        }}
    }},
    "whats_working": [
        {{"item": "Description", "metric": "Specific number", "recommendation": "Scale/maintain"}}
    ],
    "whats_not_working": [
        {{"item": "Description", "metric": "Specific number", "recommendation": "Fix/kill"}}
    ],
    "optimizations": [
        "Specific optimization to execute"
    ],
    "risks": [
        "Risk to monitor"
    ],
    "next_period_plan": [
        "Priority action 1",
        "Priority action 2"
    ],
    "budget_recommendation": "How to reallocate budget based on data"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4000,
            system=enhance_system_prompt(AD_REPORT_SYSTEM),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json_response(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Ad report generation failed: {e}")
        return {"error": str(e), "report_type": report_type}


async def conduct_market_research(
    city: str,
    procedures: list,
    competitors: list = None,
    budget_range: str = "",
    research_focus: str = "full"
) -> dict:
    """Conduct AI market research for a clinic's market."""
    try:
        client = get_client()
        prompt = f"""Conduct comprehensive market research for an aesthetic/medical clinic.

MARKET: {city}
PROCEDURES: {json.dumps(procedures)}
KNOWN COMPETITORS: {json.dumps(competitors or [])}
BUDGET RANGE: {budget_range}
RESEARCH FOCUS: {research_focus}

Return JSON:
{{
    "market_overview": {{
        "city": "{city}",
        "estimated_market_size": "Estimate",
        "competition_level": "low|medium|high|saturated",
        "top_procedures_demand": ["procedure1", "procedure2"],
        "patient_demographics": "Description of typical patient"
    }},
    "competitor_analysis": [
        {{
            "name": "Competitor name",
            "estimated_ad_spend": "Range",
            "content_strategy": "Description",
            "positioning": "How they position themselves",
            "strengths": ["strength1"],
            "weaknesses": ["weakness1"],
            "ad_angles_used": ["angle1"]
        }}
    ],
    "patient_psychology": {{
        "primary_concerns": ["concern1", "concern2"],
        "decision_triggers": ["trigger1", "trigger2"],
        "common_objections": ["objection1", "objection2"],
        "trust_factors": ["factor1", "factor2"]
    }},
    "content_gaps": [
        {{"gap": "What's missing in the market", "opportunity": "How to exploit it", "priority": "high|medium|low"}}
    ],
    "ad_opportunities": [
        {{"platform": "meta|google", "angle": "Ad angle", "estimated_cpl": "Range", "competition": "low|medium|high"}}
    ],
    "positioning_recommendations": [
        {{"position": "Recommended positioning", "rationale": "Why this works", "implementation": "How to do it"}}
    ],
    "budget_allocation": {{
        "meta_ads": "X%",
        "google_ads": "X%",
        "organic_content": "X%",
        "brand_building": "X%"
    }},
    "90_day_plan": [
        {{"week": "1-2", "focus": "What to do", "deliverables": ["item1"]}}
    ]
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=6000,
            system=enhance_system_prompt(MARKET_RESEARCH_SYSTEM),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json_response(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Market research failed: {e}")
        return {"error": str(e)}


async def generate_ad_angles(
    procedure: str,
    city: str,
    doctor_name: str = "",
    clinic_name: str = "",
    existing_angles: list = None,
    target_platform: str = "meta"
) -> dict:
    """Generate fresh ad angles based on procedure and market context."""
    try:
        client = get_client()
        prompt = f"""Generate 10 unique ad angles for a clinic campaign.

PROCEDURE: {procedure}
CITY: {city}
DOCTOR: {doctor_name}
CLINIC: {clinic_name}
PLATFORM: {target_platform}
EXISTING ANGLES (avoid repetition): {json.dumps(existing_angles or [])}

Return JSON:
{{
    "procedure": "{procedure}",
    "angles": [
        {{
            "angle_name": "Short name for this angle",
            "hook": "The opening hook line (first 3 seconds / first line)",
            "concept": "Full description of the creative concept",
            "target_audience": "Who this targets specifically",
            "emotional_trigger": "What emotion this taps into",
            "funnel_stage": "awareness|consideration|decision",
            "format": "video|image|carousel|story",
            "estimated_effectiveness": "high|medium|experimental",
            "sample_headline": "Ad headline",
            "sample_body": "Ad body copy (2-3 lines)"
        }}
    ]
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4000,
            system=enhance_system_prompt(MARKETING_COACH_SYSTEM),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json_response(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Ad angle generation failed: {e}")
        return {"error": str(e), "angles": []}


async def ask_marketing_coach(
    question: str,
    context: dict = None,
    conversation_history: list = None
) -> dict:
    """Interactive marketing coach Q&A."""
    try:
        client = get_client()

        messages = []
        if conversation_history:
            for msg in conversation_history[-10:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        context_text = ""
        if context:
            context_text = f"\n\nCONTEXT:\n{json.dumps(context, indent=2, default=str)}"

        messages.append({
            "role": "user",
            "content": f"{question}{context_text}"
        })

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            system=enhance_system_prompt(MARKETING_COACH_SYSTEM),
            messages=messages
        )

        answer = response.content[0].text.strip()
        return {"answer": answer, "question": question}

    except Exception as e:
        logger.error(f"Marketing coach Q&A failed: {e}")
        return {"answer": "Unable to respond right now. Check API configuration.", "question": question}


async def analyze_ad_performance_ai(
    performance_data: list,
    clinic_name: str = ""
) -> dict:
    """AI analysis of ad performance data with optimization suggestions."""
    try:
        client = get_client()
        prompt = f"""Analyze this ad performance data and provide optimization insights.

CLINIC: {clinic_name}

DATA:
{json.dumps(performance_data[:50], indent=2, default=str)}

Return JSON:
{{
    "insights": [
        {{
            "type": "optimization|warning|opportunity|pattern",
            "platform": "meta|google|all",
            "title": "Short insight title",
            "description": "Detailed explanation",
            "action": "Specific action to take",
            "impact": "high|medium|low",
            "urgency": "immediate|this_week|next_cycle"
        }}
    ],
    "patterns_detected": [
        "Pattern description with data evidence"
    ],
    "budget_efficiency": {{
        "overall_rating": "excellent|good|average|poor",
        "recommendation": "Budget reallocation suggestion"
    }},
    "creative_fatigue_risk": {{
        "risk_level": "low|medium|high",
        "affected_campaigns": ["campaign names"],
        "recommendation": "What to do"
    }}
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=3000,
            system=enhance_system_prompt(MARKETING_COACH_SYSTEM),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json_response(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Ad performance AI analysis failed: {e}")
        return {"insights": [], "error": str(e)}


# ============================================================================
# SELF-LEARNING FUNCTIONS
# ============================================================================

async def learn_from_feedback(
    content_id: str,
    content_type: str,
    original_content: str,
    feedback: str,
    rating: int,
    performance_metrics: dict = None
) -> dict:
    """Process feedback to improve future content generation.

    Stores learning patterns that influence future generations.
    Ratings 1-5: 1=poor, 5=excellent
    """
    try:
        client = get_client()
        prompt = f"""Analyze this feedback on generated marketing content to extract learning patterns.

CONTENT TYPE: {content_type}
ORIGINAL CONTENT: {original_content[:2000]}
USER FEEDBACK: {feedback}
USER RATING: {rating}/5
PERFORMANCE METRICS: {json.dumps(performance_metrics or {})}

Extract learnings that should influence future content generation. Return JSON:
{{
    "learning_type": "style|tone|structure|messaging|targeting|cta|hook",
    "key_learning": "What to do differently next time",
    "positive_patterns": ["What worked well and should be repeated"],
    "negative_patterns": ["What failed and should be avoided"],
    "content_type_specific": {{
        "content_type": "{content_type}",
        "adjustments": ["Specific adjustment for this content type"]
    }},
    "confidence": "high|medium|low"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            system=enhance_system_prompt(MARKETING_COACH_SYSTEM),
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = _clean_json_response(response.content[0].text)
        return json.loads(result_text)

    except Exception as e:
        logger.error(f"Learning from feedback failed: {e}")
        return {"key_learning": "Feedback processing failed", "confidence": "low"}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _clean_json_response(text: str) -> str:
    """Clean potential markdown code fences from AI response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n", 1)
        if len(lines) > 1:
            text = lines[1]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()
