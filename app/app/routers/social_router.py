"""
CallCoach CRM - Social Media Router
Social account management, post scheduling, and AI content generation.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity


def _apply_regenerate_changes(prompt: str, data) -> str:
    """Append user's regeneration feedback to the prompt if provided."""
    changes = ""
    if isinstance(data, dict):
        changes = data.get("regenerate_changes", "")
    elif hasattr(data, "regenerate_changes"):
        changes = getattr(data, "regenerate_changes", "") or ""
    if changes and str(changes).strip():
        prompt += f"\n\nIMPORTANT - USER FEEDBACK (apply these specific changes to your output):\n{str(changes).strip()}"
    return prompt
from app.models_whatsapp import SocialAccount, SocialPost, MarketingInsight
from app.schemas_whatsapp import (
    SocialAccountConnect, SocialAccountOut,
    SocialPostCreate, SocialPostUpdate, SocialPostOut,
    MarketingInsightOut, GenerateAdAnglesRequest, GenerateContentIdeasRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social", tags=["social"])


# ---------------------------------------------------------------------------
# Generation History
# ---------------------------------------------------------------------------

@router.get("/history")
def get_social_generation_history(
    action_filter: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get social content generation history."""
    from app.services.activity_logger import get_activity_logs
    logs = get_activity_logs(db=db, clinic_id=current_user.clinic_id, category="script_generation", limit=limit)
    content_logs = get_activity_logs(db=db, clinic_id=current_user.clinic_id, category="content", limit=limit)
    all_logs = logs + content_logs
    social_keywords = ["content_ideas", "ad_angles", "social"]
    all_logs = [l for l in all_logs if any(kw in l.get("action", "") for kw in social_keywords)]
    all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    if action_filter:
        all_logs = [l for l in all_logs if action_filter in l.get("action", "")]
    return {"history": all_logs[:limit], "count": len(all_logs[:limit])}


# ---------------------------------------------------------------------------
# Social Accounts
# ---------------------------------------------------------------------------

@router.get("/accounts", response_model=list[SocialAccountOut])
def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List connected social accounts."""
    return db.query(SocialAccount).filter(
        SocialAccount.clinic_id == current_user.clinic_id,
        SocialAccount.is_active == True
    ).all()


@router.post("/accounts", response_model=SocialAccountOut)
def connect_account(
    data: SocialAccountConnect,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect a social media account."""
    # Check if already connected
    existing = db.query(SocialAccount).filter(
        SocialAccount.clinic_id == current_user.clinic_id,
        SocialAccount.platform == data.platform,
        SocialAccount.is_active == True
    ).first()

    if existing:
        existing.access_token = data.access_token
        existing.refresh_token = data.refresh_token
        existing.account_name = data.account_name or existing.account_name
        existing.account_id = data.account_id or existing.account_id
        existing.profile_url = data.profile_url or existing.profile_url
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        log_activity(db, current_user.clinic_id, "content", "social_account_reconnected",
                     {"platform": data.platform, "account": data.account_name}, current_user.email)
        return existing

    account = SocialAccount(
        clinic_id=current_user.clinic_id,
        platform=data.platform,
        access_token=data.access_token,
        refresh_token=data.refresh_token,
        account_name=data.account_name,
        account_id=data.account_id,
        profile_url=data.profile_url,
        connected_at=datetime.utcnow()
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    log_activity(db, current_user.clinic_id, "content", "social_account_connected",
                 {"platform": data.platform, "account": data.account_name}, current_user.email)
    return account


@router.delete("/accounts/{account_id}")
def disconnect_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect a social account."""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.clinic_id == current_user.clinic_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_active = False
    db.commit()
    log_activity(db, current_user.clinic_id, "content", "social_account_disconnected",
                 {"platform": account.platform, "account": account.account_name}, current_user.email)
    return {"status": "disconnected"}


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

@router.get("/posts", response_model=list[SocialPostOut])
def list_posts(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List social media posts."""
    query = db.query(SocialPost).filter(
        SocialPost.clinic_id == current_user.clinic_id
    )
    if status:
        query = query.filter(SocialPost.status == status)

    return query.order_by(SocialPost.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/posts", response_model=SocialPostOut)
def create_post(
    data: SocialPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a social media post (draft or scheduled)."""
    post = SocialPost(
        clinic_id=current_user.clinic_id,
        created_by_id=current_user.id,
        content=data.content,
        media_urls=data.media_urls,
        media_type=data.media_type,
        platforms=data.platforms,
        platform_specific=data.platform_specific,
        scheduled_at=data.scheduled_at,
        status="scheduled" if data.scheduled_at else "draft"
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    log_activity(db, current_user.clinic_id, "content", "social_post_created",
                 {"platforms": data.platforms, "status": post.status, "content_preview": data.content[:80]},
                 current_user.email)
    return post


@router.put("/posts/{post_id}", response_model=SocialPostOut)
def update_post(
    post_id: str,
    data: SocialPostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a post."""
    post = db.query(SocialPost).filter(
        SocialPost.id == post_id,
        SocialPost.clinic_id == current_user.clinic_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status == "published":
        raise HTTPException(status_code=400, detail="Cannot edit published post")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a draft or scheduled post."""
    post = db.query(SocialPost).filter(
        SocialPost.id == post_id,
        SocialPost.clinic_id == current_user.clinic_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status == "published":
        raise HTTPException(status_code=400, detail="Cannot delete published post")

    db.delete(post)
    db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# AI Content Generation
# ---------------------------------------------------------------------------

@router.post("/generate-content")
def generate_content_ideas(
    data: GenerateContentIdeasRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI content ideas based on clinic data and call insights."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from app.models import Clinic, Call
    from anthropic import Anthropic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    # Get recent call insights for context
    recent_insights = db.query(MarketingInsight).filter(
        MarketingInsight.clinic_id == current_user.clinic_id
    ).order_by(MarketingInsight.created_at.desc()).limit(10).all()

    insight_context = ""
    if recent_insights:
        insight_context = "\n\nRecent marketing insights from call analysis:\n"
        for ins in recent_insights:
            insight_context += f"- {ins.title}: {ins.content[:200]}\n"

    prompt = f"""Generate {data.num_ideas} {data.content_type} content ideas for {data.platform} for a medical/aesthetic clinic.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
Specialty: {clinic.specialty if clinic else 'General aesthetics'}
{insight_context}

For each idea, provide:
1. Title/Hook (attention-grabbing)
2. Content outline (3-5 bullet points)
3. Call to action
4. Hashtags (if Instagram)

Format as JSON array with objects having: title, outline, cta, hashtags"""

    prompt = _apply_regenerate_changes(prompt, data)

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        log_activity(db, current_user.clinic_id, "script_generation", "content_ideas_generated",
                     {"platform": data.platform, "content_type": data.content_type, "num_ideas": data.num_ideas},
                     current_user.email)
        return {"ideas": response.content[0].text}
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(status_code=500, detail="Content generation failed")


@router.post("/generate-ad-angles")
def generate_ad_angles(
    data: GenerateAdAnglesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate ad angle ideas from call data analysis."""
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    from app.models import Clinic, Call
    from anthropic import Anthropic

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    # Get recent calls for context
    recent_calls = db.query(Call).filter(
        Call.clinic_id == current_user.clinic_id
    ).order_by(Call.created_at.desc()).limit(20).all()

    call_context = ""
    if recent_calls:
        call_context = "\n\nRecent call summaries:\n"
        for call in recent_calls:
            if call.ai_summary:
                call_context += f"- {call.ai_summary[:200]}\n"

    prompt = f"""Based on real patient conversations, generate {data.num_angles} ad angles for a medical/aesthetic clinic.

Clinic: {clinic.name if clinic else 'Aesthetic Clinic'}
{f'Focus on: {data.procedure_category}' if data.procedure_category else ''}
{call_context}

For each ad angle, provide:
1. Headline (max 10 words)
2. Primary text (2-3 sentences, conversational)
3. Target audience description
4. Emotional trigger being used
5. Suggested visual direction

Format as JSON array."""

    prompt = _apply_regenerate_changes(prompt, data)

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        log_activity(db, current_user.clinic_id, "script_generation", "ad_angles_generated",
                     {"num_angles": data.num_angles, "procedure": data.procedure_category},
                     current_user.email)
        return {"angles": response.content[0].text}
    except Exception as e:
        logger.error(f"Ad angle generation failed: {e}")
        raise HTTPException(status_code=500, detail="Ad angle generation failed")


# ---------------------------------------------------------------------------
# Marketing Insights
# ---------------------------------------------------------------------------

@router.get("/insights", response_model=list[MarketingInsightOut])
def list_insights(
    insight_type: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List marketing insights generated from call analysis."""
    query = db.query(MarketingInsight).filter(
        MarketingInsight.clinic_id == current_user.clinic_id
    )
    if insight_type:
        query = query.filter(MarketingInsight.insight_type == insight_type)
    if category:
        query = query.filter(MarketingInsight.category == category)

    return query.order_by(MarketingInsight.created_at.desc()).offset(skip).limit(limit).all()
