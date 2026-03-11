"""
CallCoach CRM - Marketing Router (Full Rebuild)
Complete marketing hub: AI content generation, ad management, content calendar,
market research, script approval, campaign workspaces, AI coach, self-learning.
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    AdPerformance,
    WeeklyAdReport,
    AIContentGeneration,
    GeneratedContent
)
from app.models_marketing import (
    ContentCalendar,
    ContentCalendarPost,
    MarketResearch,
    CampaignWorkspace,
    MarketingAIFeedback,
    MarketingCoachChat
)
from app.services import marketing_ai_coach

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketing", tags=["marketing"])


# ============================================================================
# 1. MARKETING DASHBOARD
# ============================================================================

@router.get("/dashboard")
async def marketing_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Comprehensive marketing dashboard with all key metrics."""
    clinic_id = current_user.clinic_id
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Ad performance - 30 day
    ad_30d = db.query(
        func.sum(AdPerformance.spend),
        func.sum(AdPerformance.conversions),
        func.sum(AdPerformance.impressions),
        func.sum(AdPerformance.clicks)
    ).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= thirty_days_ago
    ).first()

    total_spend_30d = float(ad_30d[0] or 0)
    total_conversions_30d = int(ad_30d[1] or 0)
    total_impressions_30d = int(ad_30d[2] or 0)
    total_clicks_30d = int(ad_30d[3] or 0)

    # Ad performance - 7 day
    ad_7d = db.query(
        func.sum(AdPerformance.spend),
        func.sum(AdPerformance.conversions),
        func.sum(AdPerformance.impressions),
        func.sum(AdPerformance.clicks)
    ).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= seven_days_ago
    ).first()

    total_spend_7d = float(ad_7d[0] or 0)
    total_conversions_7d = int(ad_7d[1] or 0)

    # Content metrics
    total_content = db.query(func.count(AIContentGeneration.id)).filter(
        AIContentGeneration.clinic_id == clinic_id
    ).scalar() or 0

    approved_content = db.query(func.count(AIContentGeneration.id)).filter(
        AIContentGeneration.clinic_id == clinic_id,
        AIContentGeneration.status == "approved"
    ).scalar() or 0

    # Campaign workspaces
    active_campaigns = db.query(func.count(CampaignWorkspace.id)).filter(
        CampaignWorkspace.clinic_id == clinic_id,
        CampaignWorkspace.status == "active"
    ).scalar() or 0

    # Content calendar
    active_calendar = db.query(ContentCalendar).filter(
        ContentCalendar.clinic_id == clinic_id,
        ContentCalendar.status == "active"
    ).first()

    # Platform breakdown
    platform_data = db.query(
        AdPerformance.platform,
        func.sum(AdPerformance.spend),
        func.sum(AdPerformance.conversions),
        func.sum(AdPerformance.clicks),
        func.sum(AdPerformance.impressions)
    ).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= thirty_days_ago
    ).group_by(AdPerformance.platform).all()

    platforms = {}
    for row in platform_data:
        spend = float(row[1] or 0)
        conversions = int(row[2] or 0)
        clicks = int(row[3] or 0)
        impressions = int(row[4] or 0)
        platforms[row[0]] = {
            "spend": spend,
            "conversions": conversions,
            "clicks": clicks,
            "impressions": impressions,
            "ctr": round((clicks / impressions * 100) if impressions > 0 else 0, 2),
            "cpl": round((spend / conversions) if conversions > 0 else 0, 2)
        }

    # Calculate aggregates
    ctr_30d = round((total_clicks_30d / total_impressions_30d * 100) if total_impressions_30d > 0 else 0, 2)
    cpl_30d = round((total_spend_30d / total_conversions_30d) if total_conversions_30d > 0 else 0, 2)
    cpl_7d = round((total_spend_7d / total_conversions_7d) if total_conversions_7d > 0 else 0, 2)

    return {
        "ad_metrics_30d": {
            "total_spend": total_spend_30d,
            "total_conversions": total_conversions_30d,
            "total_impressions": total_impressions_30d,
            "total_clicks": total_clicks_30d,
            "ctr": ctr_30d,
            "cost_per_lead": cpl_30d
        },
        "ad_metrics_7d": {
            "total_spend": total_spend_7d,
            "total_conversions": total_conversions_7d,
            "cost_per_lead": cpl_7d
        },
        "content_metrics": {
            "total_generated": total_content,
            "approved": approved_content,
            "pending_review": total_content - approved_content
        },
        "campaigns": {
            "active": active_campaigns
        },
        "content_calendar": {
            "active": active_calendar is not None,
            "month": active_calendar.month if active_calendar else None,
            "posts_published": active_calendar.posts_published if active_calendar else 0,
            "total_posts": active_calendar.total_posts if active_calendar else 0
        },
        "platform_breakdown": platforms,
        "period": "Last 30 days"
    }


# ============================================================================
# 2. AD PERFORMANCE TRACKING
# ============================================================================

@router.get("/ad-performance")
async def get_ad_performance(
    platform: Optional[str] = None,
    campaign_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ad performance data with filters."""
    query = db.query(AdPerformance).filter(
        AdPerformance.clinic_id == current_user.clinic_id
    )

    if platform:
        query = query.filter(AdPerformance.platform == platform)
    if campaign_name:
        query = query.filter(AdPerformance.campaign_name.ilike(f"%{campaign_name}%"))
    if start_date:
        try:
            query = query.filter(AdPerformance.date >= datetime.fromisoformat(start_date))
        except ValueError:
            pass
    if end_date:
        try:
            query = query.filter(AdPerformance.date <= datetime.fromisoformat(end_date))
        except ValueError:
            pass

    total = query.count()
    performance = query.order_by(AdPerformance.date.desc()).offset(skip).limit(limit).all()

    return {"ad_performance": performance, "total": total}


@router.post("/ad-performance")
async def create_ad_performance(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually add ad performance data."""
    required = ["platform", "date"]
    for f in required:
        if f not in data:
            raise HTTPException(status_code=400, detail=f"Missing: {f}")

    record = AdPerformance(
        clinic_id=current_user.clinic_id,
        platform=data["platform"],
        campaign_id=data.get("campaign_id"),
        campaign_name=data.get("campaign_name"),
        ad_set_name=data.get("ad_set_name"),
        ad_name=data.get("ad_name"),
        date=datetime.fromisoformat(data["date"]),
        impressions=data.get("impressions", 0),
        clicks=data.get("clicks", 0),
        ctr=data.get("ctr", 0),
        cpc=data.get("cpc", 0),
        spend=data.get("spend", 0),
        conversions=data.get("conversions", 0),
        cost_per_conversion=data.get("cost_per_conversion", 0),
        roas=data.get("roas", 0)
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "created", "id": record.id, "record": record}


@router.post("/ad-performance/bulk")
async def bulk_create_ad_performance(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk import ad performance data."""
    records = data.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail="No records provided")

    created = 0
    for r in records:
        try:
            record = AdPerformance(
                clinic_id=current_user.clinic_id,
                platform=r.get("platform", "meta"),
                campaign_id=r.get("campaign_id"),
                campaign_name=r.get("campaign_name"),
                ad_set_name=r.get("ad_set_name"),
                ad_name=r.get("ad_name"),
                date=datetime.fromisoformat(r["date"]),
                impressions=r.get("impressions", 0),
                clicks=r.get("clicks", 0),
                ctr=r.get("ctr", 0),
                cpc=r.get("cpc", 0),
                spend=r.get("spend", 0),
                conversions=r.get("conversions", 0),
                cost_per_conversion=r.get("cost_per_conversion", 0),
                roas=r.get("roas", 0)
            )
            db.add(record)
            created += 1
        except Exception as e:
            logger.warning(f"Skipping record: {e}")

    db.commit()
    return {"status": "imported", "created": created, "total_submitted": len(records)}


# ============================================================================
# 3. AI-POWERED INSIGHTS & REPORTS
# ============================================================================

@router.get("/ad-performance/insights")
async def get_ai_insights(
    period_days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered optimization insights from ad performance data."""
    clinic_id = current_user.clinic_id
    cutoff = datetime.utcnow() - timedelta(days=period_days)

    performance = db.query(AdPerformance).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= cutoff
    ).all()

    if not performance:
        return {"insights": [], "message": "Not enough data for insights"}

    # Prepare data for AI
    perf_data = []
    for p in performance:
        perf_data.append({
            "platform": p.platform,
            "campaign_name": p.campaign_name,
            "ad_set_name": p.ad_set_name,
            "date": str(p.date),
            "spend": p.spend,
            "impressions": p.impressions,
            "clicks": p.clicks,
            "conversions": p.conversions,
            "ctr": p.ctr,
            "cpc": p.cpc,
            "cost_per_conversion": p.cost_per_conversion
        })

    # Get AI analysis
    analysis = await marketing_ai_coach.analyze_ad_performance_ai(
        performance_data=perf_data,
        clinic_name=f"Clinic {clinic_id}"
    )

    return {
        "insights": analysis.get("insights", []),
        "patterns": analysis.get("patterns_detected", []),
        "budget_efficiency": analysis.get("budget_efficiency", {}),
        "creative_fatigue": analysis.get("creative_fatigue_risk", {}),
        "data_points_analyzed": len(perf_data),
        "period": f"Last {period_days} days"
    }


@router.post("/reports/generate")
async def generate_report(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered ad report (72-hour or weekly)."""
    report_type = data.get("report_type", "72_hour")  # 72_hour or weekly
    platform_filter = data.get("platform", "all")
    clinic_id = current_user.clinic_id

    days = 3 if report_type == "72_hour" else 7
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.query(AdPerformance).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= cutoff
    )
    if platform_filter != "all":
        query = query.filter(AdPerformance.platform == platform_filter)

    performance = query.all()

    if not performance:
        return {"error": "No performance data found for this period"}

    perf_data = [{
        "platform": p.platform, "campaign_name": p.campaign_name,
        "ad_set_name": p.ad_set_name, "date": str(p.date),
        "spend": p.spend, "impressions": p.impressions, "clicks": p.clicks,
        "conversions": p.conversions, "ctr": p.ctr, "cpc": p.cpc,
        "cost_per_conversion": p.cost_per_conversion
    } for p in performance]

    # Generate AI report
    report = await marketing_ai_coach.generate_ad_report(
        report_type=report_type,
        performance_data=perf_data,
        period=f"Last {days} days",
        clinic_name=f"Clinic {clinic_id}",
        platform=platform_filter
    )

    # Save to DB
    total_spend = sum(p.spend or 0 for p in performance)
    total_conversions = sum(p.conversions or 0 for p in performance)
    total_impressions = sum(p.impressions or 0 for p in performance)
    total_clicks = sum(p.clicks or 0 for p in performance)

    db_report = WeeklyAdReport(
        clinic_id=clinic_id,
        platform=platform_filter,
        week_start=cutoff,
        week_end=datetime.utcnow(),
        total_spend=total_spend,
        total_conversions=total_conversions,
        avg_cpc=round((total_spend / total_clicks) if total_clicks > 0 else 0, 2),
        avg_ctr=round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
        avg_cost_per_conversion=round((total_spend / total_conversions) if total_conversions > 0 else 0, 2),
        ai_recommendations=report.get("next_period_plan", []),
        auto_generated=True
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)

    return {
        "report_id": db_report.id,
        "report_type": report_type,
        "ai_report": report,
        "raw_metrics": {
            "total_spend": total_spend,
            "total_conversions": total_conversions,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks
        }
    }


@router.get("/reports")
async def list_reports(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List saved reports."""
    reports = db.query(WeeklyAdReport).filter(
        WeeklyAdReport.clinic_id == current_user.clinic_id
    ).order_by(WeeklyAdReport.created_at.desc()).offset(skip).limit(limit).all()

    total = db.query(func.count(WeeklyAdReport.id)).filter(
        WeeklyAdReport.clinic_id == current_user.clinic_id
    ).scalar() or 0

    return {"reports": reports, "total": total}


# ============================================================================
# 4. AI CONTENT GENERATION
# ============================================================================

@router.post("/content/generate")
async def generate_content(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate marketing content using AI. Real Claude-powered generation."""
    required = ["content_type", "procedure"]
    for f in required:
        if f not in data:
            raise HTTPException(status_code=400, detail=f"Missing: {f}")

    # Get self-learning context
    clinic_id = current_user.clinic_id
    recent_feedback = db.query(MarketingAIFeedback).filter(
        MarketingAIFeedback.clinic_id == clinic_id,
        MarketingAIFeedback.content_type == data["content_type"],
        MarketingAIFeedback.rating >= 4
    ).order_by(MarketingAIFeedback.created_at.desc()).limit(5).all()

    learning_context = ""
    if recent_feedback:
        patterns = [fb.ai_learnings.get("key_learning", "") for fb in recent_feedback if fb.ai_learnings]
        if patterns:
            learning_context = "Based on previous feedback, consider: " + "; ".join(patterns[:3])

    # Generate with AI
    result = await marketing_ai_coach.generate_content(
        content_type=data["content_type"],
        procedure=data["procedure"],
        clinic_name=data.get("clinic_name", ""),
        doctor_name=data.get("doctor_name", ""),
        city=data.get("city", ""),
        language=data.get("language", "english"),
        tone=data.get("tone", "professional"),
        platform=data.get("platform", "instagram"),
        additional_context=data.get("additional_context", "") + " " + learning_context,
        funnel_stage=data.get("funnel_stage", "awareness")
    )

    # Save to DB
    content_record = AIContentGeneration(
        clinic_id=clinic_id,
        content_type=data["content_type"],
        procedure_category=data["procedure"],
        prompt_used=f"Type: {data['content_type']}, Procedure: {data['procedure']}, Platform: {data.get('platform', 'instagram')}",
        generated_content=result.get("content", ""),
        status="generated",
        score=0
    )
    db.add(content_record)
    db.commit()
    db.refresh(content_record)

    return {
        "status": "generated",
        "content_id": content_record.id,
        "generated": result,
        "learning_applied": bool(learning_context)
    }


@router.post("/content/generate-batch")
async def generate_content_batch(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate multiple content pieces at once."""
    items = data.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="No items to generate")

    results = []
    for item in items[:10]:  # max 10 at a time
        try:
            result = await marketing_ai_coach.generate_content(
                content_type=item.get("content_type", "video_script"),
                procedure=item.get("procedure", ""),
                clinic_name=data.get("clinic_name", ""),
                doctor_name=data.get("doctor_name", ""),
                city=data.get("city", ""),
                language=data.get("language", "english"),
                tone=data.get("tone", "professional"),
                platform=item.get("platform", "instagram"),
                funnel_stage=item.get("funnel_stage", "awareness")
            )

            record = AIContentGeneration(
                clinic_id=current_user.clinic_id,
                content_type=item.get("content_type", "video_script"),
                procedure_category=item.get("procedure", ""),
                prompt_used=f"Batch: {item.get('content_type')} for {item.get('procedure')}",
                generated_content=result.get("content", ""),
                status="generated"
            )
            db.add(record)
            results.append({"content_id": None, "generated": result, "status": "success"})
        except Exception as e:
            results.append({"error": str(e), "status": "failed"})

    db.commit()
    return {"status": "batch_complete", "results": results, "total": len(results)}


@router.get("/content")
async def list_content(
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    procedure: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List generated content with filters."""
    query = db.query(AIContentGeneration).filter(
        AIContentGeneration.clinic_id == current_user.clinic_id
    )
    if content_type:
        query = query.filter(AIContentGeneration.content_type == content_type)
    if status:
        query = query.filter(AIContentGeneration.status == status)
    if procedure:
        query = query.filter(AIContentGeneration.procedure_category.ilike(f"%{procedure}%"))

    total = query.count()
    content = query.order_by(AIContentGeneration.created_at.desc()).offset(skip).limit(limit).all()
    return {"content": content, "total": total}


@router.get("/content/{content_id}")
async def get_content(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific content piece."""
    content = db.query(AIContentGeneration).filter(
        AIContentGeneration.id == content_id,
        AIContentGeneration.clinic_id == current_user.clinic_id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"content": content}


@router.put("/content/{content_id}")
async def update_content(
    content_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update content status, edit content, or add notes."""
    content = db.query(AIContentGeneration).filter(
        AIContentGeneration.id == content_id,
        AIContentGeneration.clinic_id == current_user.clinic_id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if "status" in data:
        content.status = data["status"]
    if "generated_content" in data:
        content.generated_content = data["generated_content"]
    if "score" in data:
        content.score = data["score"]

    content.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(content)
    return {"status": "updated", "content": content}


# ============================================================================
# 5. SCRIPT APPROVAL / SCORING
# ============================================================================

@router.post("/content/{content_id}/score")
async def score_content(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI-score a content piece using SBA approval criteria."""
    content = db.query(AIContentGeneration).filter(
        AIContentGeneration.id == content_id,
        AIContentGeneration.clinic_id == current_user.clinic_id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    result = await marketing_ai_coach.score_script(
        script_content=content.generated_content or "",
        content_type=content.content_type,
        procedure=content.procedure_category or "",
        platform="instagram"
    )

    # Update score in DB
    content.score = result.get("total_score", 0)
    if result.get("verdict") == "approved" and content.score >= 70:
        content.status = "approved"
    content.updated_at = datetime.utcnow()
    db.commit()

    return {
        "content_id": content_id,
        "scoring": result,
        "auto_status": content.status
    }


@router.post("/scripts/score")
async def score_custom_script(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Score any script text without saving it first."""
    if "script" not in data:
        raise HTTPException(status_code=400, detail="Missing: script")

    result = await marketing_ai_coach.score_script(
        script_content=data["script"],
        content_type=data.get("content_type", "video_script"),
        procedure=data.get("procedure", "general"),
        platform=data.get("platform", "instagram"),
        clinic_name=data.get("clinic_name", ""),
        doctor_name=data.get("doctor_name", "")
    )
    return {"scoring": result}


# ============================================================================
# 6. AD ANGLES GENERATOR
# ============================================================================

@router.post("/ad-angles/generate")
async def generate_ad_angles(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate fresh ad angles for a procedure."""
    if "procedure" not in data:
        raise HTTPException(status_code=400, detail="Missing: procedure")

    # Get existing angles to avoid repetition
    existing = db.query(CampaignWorkspace.ad_angles).filter(
        CampaignWorkspace.clinic_id == current_user.clinic_id,
        CampaignWorkspace.procedure_focus == data["procedure"]
    ).all()

    existing_angles = []
    for row in existing:
        if row[0]:
            for angle in row[0]:
                existing_angles.append(angle.get("angle_name", ""))

    result = await marketing_ai_coach.generate_ad_angles(
        procedure=data["procedure"],
        city=data.get("city", ""),
        doctor_name=data.get("doctor_name", ""),
        clinic_name=data.get("clinic_name", ""),
        existing_angles=existing_angles,
        target_platform=data.get("platform", "meta")
    )

    return {"angles": result.get("angles", []), "procedure": data["procedure"]}


# ============================================================================
# 7. CONTENT CALENDAR
# ============================================================================

@router.post("/calendar/generate")
async def generate_content_calendar(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a full month content calendar using AI."""
    clinic_id = current_user.clinic_id

    result = await marketing_ai_coach.generate_content_calendar(
        clinic_name=data.get("clinic_name", ""),
        procedures=data.get("procedures", []),
        doctor_name=data.get("doctor_name", ""),
        city=data.get("city", ""),
        month=data.get("month", ""),
        platforms=data.get("platforms", ["instagram", "facebook", "youtube"]),
        posts_per_week=data.get("posts_per_week", 4)
    )

    # Save calendar
    calendar = ContentCalendar(
        clinic_id=clinic_id,
        month=data.get("month", datetime.utcnow().strftime("%Y-%m")),
        theme=result.get("theme", ""),
        status="draft",
        total_posts=result.get("total_posts", 0),
        calendar_data=result.get("calendar", []),
        content_mix=result.get("content_mix", {}),
        notes=result.get("notes", ""),
        posts_pending=result.get("total_posts", 0)
    )
    db.add(calendar)
    db.commit()
    db.refresh(calendar)

    # Create individual post records from calendar
    post_count = 0
    for day_entry in result.get("calendar", []):
        for post in day_entry.get("posts", []):
            try:
                cal_post = ContentCalendarPost(
                    calendar_id=calendar.id,
                    clinic_id=clinic_id,
                    scheduled_date=datetime.fromisoformat(day_entry.get("date", datetime.utcnow().isoformat())),
                    platform=post.get("platform", "instagram"),
                    content_type=post.get("content_type", "post"),
                    title=post.get("title", ""),
                    description=post.get("description", ""),
                    procedure_focus=post.get("procedure_focus", ""),
                    funnel_stage=post.get("funnel_stage", "awareness"),
                    hashtags=post.get("hashtags", []),
                    status="planned"
                )
                db.add(cal_post)
                post_count += 1
            except Exception as e:
                logger.warning(f"Skipping calendar post: {e}")

    db.commit()

    return {
        "status": "generated",
        "calendar_id": calendar.id,
        "calendar": result,
        "posts_created": post_count
    }


@router.get("/calendar")
async def list_calendars(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all content calendars."""
    calendars = db.query(ContentCalendar).filter(
        ContentCalendar.clinic_id == current_user.clinic_id
    ).order_by(ContentCalendar.created_at.desc()).all()
    return {"calendars": calendars}


@router.get("/calendar/{calendar_id}")
async def get_calendar(
    calendar_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get calendar with all posts."""
    calendar = db.query(ContentCalendar).filter(
        ContentCalendar.id == calendar_id,
        ContentCalendar.clinic_id == current_user.clinic_id
    ).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")

    posts = db.query(ContentCalendarPost).filter(
        ContentCalendarPost.calendar_id == calendar_id
    ).order_by(ContentCalendarPost.scheduled_date.asc()).all()

    return {"calendar": calendar, "posts": posts}


@router.put("/calendar/{calendar_id}")
async def update_calendar(
    calendar_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update calendar status."""
    calendar = db.query(ContentCalendar).filter(
        ContentCalendar.id == calendar_id,
        ContentCalendar.clinic_id == current_user.clinic_id
    ).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")

    if "status" in data:
        calendar.status = data["status"]
    calendar.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calendar)
    return {"status": "updated", "calendar": calendar}


@router.put("/calendar/posts/{post_id}")
async def update_calendar_post(
    post_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a calendar post (status, content, publish info)."""
    post = db.query(ContentCalendarPost).filter(
        ContentCalendarPost.id == post_id,
        ContentCalendarPost.clinic_id == current_user.clinic_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    for field in ["status", "content_text", "published_url", "impressions", "engagement", "clicks", "title", "description"]:
        if field in data:
            setattr(post, field, data[field])

    if data.get("status") == "published" and not post.published_at:
        post.published_at = datetime.utcnow()
        # Update calendar counters
        calendar = db.query(ContentCalendar).filter(
            ContentCalendar.id == post.calendar_id
        ).first()
        if calendar:
            calendar.posts_published = (calendar.posts_published or 0) + 1
            calendar.posts_pending = max(0, (calendar.posts_pending or 0) - 1)

    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return {"status": "updated", "post": post}


# ============================================================================
# 8. MARKET RESEARCH
# ============================================================================

@router.post("/research")
async def conduct_research(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Conduct AI market research."""
    if "city" not in data:
        raise HTTPException(status_code=400, detail="Missing: city")

    result = await marketing_ai_coach.conduct_market_research(
        city=data["city"],
        procedures=data.get("procedures", []),
        competitors=data.get("competitors", []),
        budget_range=data.get("budget_range", ""),
        research_focus=data.get("research_focus", "full")
    )

    # Save research
    research = MarketResearch(
        clinic_id=current_user.clinic_id,
        city=data["city"],
        procedures=data.get("procedures", []),
        competitors=data.get("competitors", []),
        research_focus=data.get("research_focus", "full"),
        research_data=result,
        market_overview=result.get("market_overview", {}),
        competitor_analysis=result.get("competitor_analysis", []),
        patient_psychology=result.get("patient_psychology", {}),
        content_gaps=result.get("content_gaps", []),
        ad_opportunities=result.get("ad_opportunities", []),
        positioning_recommendations=result.get("positioning_recommendations", []),
        budget_allocation=result.get("budget_allocation", {})
    )
    db.add(research)
    db.commit()
    db.refresh(research)

    return {"status": "completed", "research_id": research.id, "research": result}


@router.get("/research")
async def list_research(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List past research reports."""
    reports = db.query(MarketResearch).filter(
        MarketResearch.clinic_id == current_user.clinic_id
    ).order_by(MarketResearch.created_at.desc()).all()
    return {"research_reports": reports}


@router.get("/research/{research_id}")
async def get_research(
    research_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific research report."""
    research = db.query(MarketResearch).filter(
        MarketResearch.id == research_id,
        MarketResearch.clinic_id == current_user.clinic_id
    ).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    return {"research": research}


# ============================================================================
# 9. CAMPAIGN WORKSPACES
# ============================================================================

@router.post("/campaigns")
async def create_campaign(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a campaign workspace."""
    if "name" not in data or "platform" not in data:
        raise HTTPException(status_code=400, detail="Missing: name and platform")

    campaign = CampaignWorkspace(
        clinic_id=current_user.clinic_id,
        name=data["name"],
        platform=data["platform"],
        objective=data.get("objective", "lead_generation"),
        procedure_focus=data.get("procedure_focus", ""),
        daily_budget=data.get("daily_budget", 0),
        total_budget=data.get("total_budget", 0),
        targeting=data.get("targeting", {}),
        status="draft"
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return {"status": "created", "campaign": campaign}


@router.get("/campaigns")
async def list_campaigns(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List campaign workspaces."""
    query = db.query(CampaignWorkspace).filter(
        CampaignWorkspace.clinic_id == current_user.clinic_id
    )
    if status:
        query = query.filter(CampaignWorkspace.status == status)
    if platform:
        query = query.filter(CampaignWorkspace.platform == platform)

    campaigns = query.order_by(CampaignWorkspace.created_at.desc()).all()
    return {"campaigns": campaigns}


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get campaign details."""
    campaign = db.query(CampaignWorkspace).filter(
        CampaignWorkspace.id == campaign_id,
        CampaignWorkspace.clinic_id == current_user.clinic_id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"campaign": campaign}


@router.put("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update campaign workspace."""
    campaign = db.query(CampaignWorkspace).filter(
        CampaignWorkspace.id == campaign_id,
        CampaignWorkspace.clinic_id == current_user.clinic_id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    updatable = ["name", "platform", "objective", "procedure_focus", "daily_budget",
                 "total_budget", "targeting", "ad_sets", "ad_angles", "scripts",
                 "creatives", "status", "start_date", "end_date"]
    for field in updatable:
        if field in data:
            value = data[field]
            if field in ("start_date", "end_date") and isinstance(value, str):
                value = datetime.fromisoformat(value)
            setattr(campaign, field, value)

    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    return {"status": "updated", "campaign": campaign}


@router.post("/campaigns/{campaign_id}/generate-scripts")
async def generate_campaign_scripts(
    campaign_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate ad scripts for a campaign."""
    campaign = db.query(CampaignWorkspace).filter(
        CampaignWorkspace.id == campaign_id,
        CampaignWorkspace.clinic_id == current_user.clinic_id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    content_types = data.get("content_types", ["video_script", "image_ad", "carousel"])
    scripts = []

    for ct in content_types:
        result = await marketing_ai_coach.generate_content(
            content_type=ct,
            procedure=campaign.procedure_focus or "general",
            clinic_name=data.get("clinic_name", ""),
            doctor_name=data.get("doctor_name", ""),
            city=data.get("city", ""),
            language=data.get("language", "english"),
            platform=campaign.platform,
            funnel_stage=data.get("funnel_stage", "consideration")
        )
        scripts.append({"content_type": ct, "generated": result})

    # Save scripts to campaign
    existing_scripts = campaign.scripts or []
    existing_scripts.extend(scripts)
    campaign.scripts = existing_scripts
    campaign.updated_at = datetime.utcnow()
    db.commit()

    return {"campaign_id": campaign_id, "scripts_generated": len(scripts), "scripts": scripts}


# ============================================================================
# 10. MARKETING AI COACH (Interactive Q&A)
# ============================================================================

@router.post("/coach/ask")
async def ask_marketing_coach(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask the marketing AI coach a question."""
    question = data.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="Missing: question")

    # Get or create chat session
    chat_id = data.get("chat_id")
    chat = None
    conversation_history = []

    if chat_id:
        chat = db.query(MarketingCoachChat).filter(
            MarketingCoachChat.id == chat_id,
            MarketingCoachChat.clinic_id == current_user.clinic_id
        ).first()
        if chat:
            conversation_history = chat.messages or []

    result = await marketing_ai_coach.ask_marketing_coach(
        question=question,
        context=data.get("context", {}),
        conversation_history=conversation_history
    )

    # Save to chat
    if not chat:
        chat = MarketingCoachChat(
            clinic_id=current_user.clinic_id,
            user_id=current_user.id,
            topic=question[:200],
            messages=[],
            message_count=0,
            context_type=data.get("context_type", "general"),
            context_data=data.get("context", {})
        )
        db.add(chat)

    msgs = chat.messages or []
    msgs.append({"role": "user", "content": question, "timestamp": datetime.utcnow().isoformat()})
    msgs.append({"role": "assistant", "content": result.get("answer", ""), "timestamp": datetime.utcnow().isoformat()})
    chat.messages = msgs
    chat.message_count = len(msgs)
    chat.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(chat)

    return {
        "chat_id": chat.id,
        "answer": result.get("answer", ""),
        "message_count": chat.message_count
    }


@router.get("/coach/chats")
async def list_coach_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List marketing coach chat sessions."""
    chats = db.query(MarketingCoachChat).filter(
        MarketingCoachChat.clinic_id == current_user.clinic_id
    ).order_by(MarketingCoachChat.updated_at.desc()).limit(50).all()
    return {"chats": chats}


@router.get("/coach/chats/{chat_id}")
async def get_coach_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific coach chat with full history."""
    chat = db.query(MarketingCoachChat).filter(
        MarketingCoachChat.id == chat_id,
        MarketingCoachChat.clinic_id == current_user.clinic_id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"chat": chat}


# ============================================================================
# 11. SELF-LEARNING FEEDBACK
# ============================================================================

@router.post("/feedback")
async def submit_feedback(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback on generated content. Feeds the self-learning system."""
    content_id = data.get("content_id")
    if not content_id:
        raise HTTPException(status_code=400, detail="Missing: content_id")

    content = db.query(AIContentGeneration).filter(
        AIContentGeneration.id == content_id,
        AIContentGeneration.clinic_id == current_user.clinic_id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    rating = data.get("rating", 3)
    feedback_text = data.get("feedback", "")

    # Process feedback with AI to extract learnings
    learnings = await marketing_ai_coach.learn_from_feedback(
        content_id=content_id,
        content_type=content.content_type,
        original_content=content.generated_content or "",
        feedback=feedback_text,
        rating=rating,
        performance_metrics=data.get("performance_metrics", {})
    )

    # Save feedback
    feedback = MarketingAIFeedback(
        clinic_id=current_user.clinic_id,
        content_type=content.content_type,
        original_content=content.generated_content,
        prompt_used=content.prompt_used,
        rating=rating,
        feedback_text=feedback_text,
        was_used=data.get("was_used", False),
        was_edited=data.get("was_edited", False),
        edited_version=data.get("edited_version", ""),
        performance_metrics=data.get("performance_metrics", {}),
        ai_learnings=learnings,
        learning_type=learnings.get("learning_type", "")
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return {
        "status": "feedback_recorded",
        "feedback_id": feedback.id,
        "learnings_extracted": learnings
    }


@router.get("/feedback/learnings")
async def get_learnings(
    content_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get accumulated learnings from feedback."""
    query = db.query(MarketingAIFeedback).filter(
        MarketingAIFeedback.clinic_id == current_user.clinic_id,
        MarketingAIFeedback.ai_learnings.isnot(None)
    )
    if content_type:
        query = query.filter(MarketingAIFeedback.content_type == content_type)

    feedback_records = query.order_by(MarketingAIFeedback.created_at.desc()).limit(50).all()

    learnings = []
    for fb in feedback_records:
        if fb.ai_learnings:
            learnings.append({
                "content_type": fb.content_type,
                "rating": fb.rating,
                "learning": fb.ai_learnings.get("key_learning", ""),
                "positive_patterns": fb.ai_learnings.get("positive_patterns", []),
                "negative_patterns": fb.ai_learnings.get("negative_patterns", []),
                "date": str(fb.created_at)
            })

    return {
        "total_feedback": len(feedback_records),
        "learnings": learnings,
        "avg_rating": round(sum(fb.rating or 0 for fb in feedback_records) / max(len(feedback_records), 1), 1)
    }
