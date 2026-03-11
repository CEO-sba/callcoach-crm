"""
CallCoach CRM - Marketing Router
Marketing automation, ad performance tracking, and content generation.
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
    GeneratedContent
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketing", tags=["marketing"])


# ===== AD PERFORMANCE =====

@router.get("/ad-performance")
async def get_ad_performance(
    platform: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get ad performance data, filterable by platform and date range.
    Expected query params: platform (meta|google), start_date, end_date (ISO format)
    """
    query = db.query(AdPerformance).filter(
        AdPerformance.clinic_id == current_user.clinic_id
    )

    if platform:
        query = query.filter(AdPerformance.platform == platform)

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(AdPerformance.date >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(AdPerformance.date <= end)
        except ValueError:
            pass

    performance = query.order_by(
        AdPerformance.date.desc()
    ).offset(skip).limit(limit).all()

    return {
        "ad_performance": performance,
        "total": query.count()
    }


@router.post("/ad-performance/sync")
async def sync_ad_performance(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger sync from Meta and Google Ads.
    Expected data: {"platforms": ["meta", "google"]}
    """
    platforms = data.get("platforms", ["meta", "google"])

    # In production, this would call actual API integrations
    # For now, return sync initiated status
    sync_results = {}
    for platform in platforms:
        sync_results[platform] = "sync_initiated"

    return {
        "status": "sync_initiated",
        "platforms": sync_results,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ad-performance/insights")
async def get_optimization_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI optimization suggestions based on ad performance data."""
    clinic_id = current_user.clinic_id

    # Get recent performance data
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    recent_performance = db.query(AdPerformance).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= one_week_ago
    ).all()

    if not recent_performance:
        return {
            "insights": [],
            "message": "Not enough data for insights yet"
        }

    # Calculate aggregates by platform
    platform_stats = {}
    for perf in recent_performance:
        if perf.platform not in platform_stats:
            platform_stats[perf.platform] = {
                "spend": 0,
                "clicks": 0,
                "impressions": 0,
                "conversions": 0,
                "roas": 0
            }
        stats = platform_stats[perf.platform]
        stats["spend"] += perf.spend or 0
        stats["clicks"] += perf.clicks or 0
        stats["impressions"] += perf.impressions or 0
        stats["conversions"] += perf.conversions or 0

    # Generate insights
    insights = []
    for platform, stats in platform_stats.items():
        ctr = (stats["clicks"] / stats["impressions"] * 100) if stats["impressions"] > 0 else 0
        cost_per_conversion = (stats["spend"] / stats["conversions"]) if stats["conversions"] > 0 else 0

        if ctr < 1.0:
            insights.append({
                "platform": platform,
                "type": "ctr_low",
                "message": f"CTR is below 1% on {platform}. Consider refreshing ad creatives.",
                "severity": "medium"
            })

        if cost_per_conversion > 100:
            insights.append({
                "platform": platform,
                "type": "high_cpc",
                "message": f"Cost per conversion is high on {platform}. Refine targeting.",
                "severity": "high"
            })

    return {
        "insights": insights,
        "platform_stats": platform_stats,
        "period": f"Last 7 days"
    }


# ===== WEEKLY REPORTS =====

@router.get("/weekly-reports")
async def list_weekly_reports(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List weekly ad reports."""
    reports = db.query(WeeklyAdReport).filter(
        WeeklyAdReport.clinic_id == current_user.clinic_id
    ).order_by(
        WeeklyAdReport.report_date.desc()
    ).offset(skip).limit(limit).all()

    return {
        "reports": reports,
        "total": db.query(WeeklyAdReport).filter(
            WeeklyAdReport.clinic_id == current_user.clinic_id
        ).count()
    }


@router.post("/weekly-reports/generate")
async def generate_weekly_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-generate a weekly ad performance report."""
    clinic_id = current_user.clinic_id

    # Get data from past 7 days
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    performance_data = db.query(AdPerformance).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= one_week_ago
    ).all()

    # Calculate aggregates
    total_spend = sum(p.spend or 0 for p in performance_data)
    total_conversions = sum(p.conversions or 0 for p in performance_data)
    total_impressions = sum(p.impressions or 0 for p in performance_data)
    total_clicks = sum(p.clicks or 0 for p in performance_data)

    # Generate summary
    summary = f"Weekly Report: {total_spend:.2f} spend, {total_conversions} conversions"

    report = WeeklyAdReport(
        clinic_id=clinic_id,
        report_date=datetime.utcnow().date(),
        summary=summary,
        total_spend=total_spend,
        total_conversions=total_conversions,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        insights=[]
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "status": "generated",
        "report_id": report.id,
        "report": report
    }


# ===== CONTENT GENERATION =====

@router.post("/content/generate")
async def generate_content(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate AI content (scripts, ads, UGC).
    Expected data: {
        "content_type": "ad_copy|video_script|upc",
        "topic": "Description or topic",
        "style": "casual|professional|humorous",
        "platform": "instagram|tiktok|facebook"
    }
    """
    required_fields = ["content_type", "topic"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    content = GeneratedContent(
        clinic_id=current_user.clinic_id,
        content_type=data["content_type"],
        topic=data["topic"],
        style=data.get("style", "professional"),
        platform=data.get("platform", ""),
        content_text="Content generation in progress...",
        status="pending"
    )
    db.add(content)
    db.commit()
    db.refresh(content)

    return {
        "status": "generating",
        "content_id": content.id,
        "content": content
    }


@router.get("/content")
async def list_generated_content(
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List generated content with optional filters."""
    query = db.query(GeneratedContent).filter(
        GeneratedContent.clinic_id == current_user.clinic_id
    )

    if content_type:
        query = query.filter(GeneratedContent.content_type == content_type)
    if status:
        query = query.filter(GeneratedContent.status == status)

    content = query.order_by(
        GeneratedContent.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "content": content,
        "total": query.count()
    }


@router.put("/content/{content_id}")
async def update_content_status(
    content_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update content status (approve/reject).
    Expected data: {"status": "approved|rejected", "notes": "optional notes"}
    """
    content = db.query(GeneratedContent).filter(
        GeneratedContent.id == content_id,
        GeneratedContent.clinic_id == current_user.clinic_id
    ).first()

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if "status" in data:
        content.status = data["status"]
    if "notes" in data:
        content.notes = data["notes"]

    content.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(content)

    return {
        "status": "updated",
        "content_id": content.id,
        "content": content
    }


# ===== MARKETING DASHBOARD =====

@router.get("/dashboard")
async def marketing_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get marketing overview stats."""
    clinic_id = current_user.clinic_id

    # Get data from past 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # Ad performance metrics
    total_spend = db.query(func.sum(AdPerformance.spend)).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= thirty_days_ago
    ).scalar() or 0

    total_conversions = db.query(func.sum(AdPerformance.conversions)).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= thirty_days_ago
    ).scalar() or 0

    total_impressions = db.query(func.sum(AdPerformance.impressions)).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= thirty_days_ago
    ).scalar() or 0

    total_clicks = db.query(func.sum(AdPerformance.clicks)).filter(
        AdPerformance.clinic_id == clinic_id,
        AdPerformance.date >= thirty_days_ago
    ).scalar() or 0

    # Content stats
    total_content = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.clinic_id == clinic_id
    ).scalar() or 0

    approved_content = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.clinic_id == clinic_id,
        GeneratedContent.status == "approved"
    ).scalar() or 0

    # Calculate metrics
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    cost_per_conversion = (total_spend / total_conversions) if total_conversions > 0 else 0
    roas = (total_conversions / total_spend * 100) if total_spend > 0 else 0

    return {
        "ad_metrics": {
            "total_spend": float(total_spend),
            "total_conversions": int(total_conversions),
            "total_impressions": int(total_impressions),
            "total_clicks": int(total_clicks),
            "ctr_percent": round(ctr, 2),
            "cost_per_conversion": round(cost_per_conversion, 2),
            "roas_percent": round(roas, 2)
        },
        "content_metrics": {
            "total_content": total_content,
            "approved": approved_content
        },
        "period": "Last 30 days"
    }
