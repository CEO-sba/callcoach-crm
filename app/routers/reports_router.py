"""
CallCoach CRM - Reports Router

Endpoints for managing weekly and historical reports.
All endpoints require authentication.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import User, WeeklyReport
from app.auth import get_current_user
from app.services.weekly_report import generate_weekly_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/weekly")
async def get_current_week_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get or generate the current week's report.

    Returns the current week's report if it exists, otherwise generates it.
    Only managers and admins can view reports for their clinic.
    """
    # Permission check
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Calculate current week start (Monday)
    today = datetime.utcnow()
    week_start = today - timedelta(days=today.weekday())

    # Try to fetch existing report
    existing_report = db.query(WeeklyReport).filter(
        WeeklyReport.clinic_id == current_user.clinic_id,
        WeeklyReport.week_start == week_start.date()
    ).first()

    if existing_report:
        return {
            "id": existing_report.id,
            "clinic_id": existing_report.clinic_id,
            "week_start": existing_report.week_start.isoformat(),
            "week_end": existing_report.week_end.isoformat(),
            "total_calls": existing_report.total_calls,
            "avg_score": existing_report.avg_score,
            "conversion_rate": existing_report.conversion_rate,
            "top_agent_name": existing_report.top_agent_name,
            "calls_by_day": existing_report.calls_by_day,
            "sentiment_distribution": existing_report.sentiment_distribution,
            "ai_summary": existing_report.ai_summary,
            "ai_recommendations": existing_report.ai_recommendations,
            "revenue_impact": existing_report.revenue_impact,
            "created_at": existing_report.created_at.isoformat()
        }

    # No report exists yet for this week - return null (user must click Generate)
    return None

    # Save to database
    new_report = WeeklyReport(
        clinic_id=current_user.clinic_id,
        week_start=week_start.date(),
        week_end=(week_start + timedelta(days=7)).date(),
        total_calls=report_data["total_calls"],
        avg_score=report_data["avg_score"],
        conversion_rate=report_data["conversion_rate"],
        top_agent_id=None,
        top_agent_name=report_data.get("best_agent_name", "N/A"),
        calls_by_day=report_data.get("calls_by_day", {}),
        sentiment_distribution=report_data.get("sentiment_distribution", {}),
        ai_summary=report_data.get("ai_summary", ""),
        ai_recommendations=report_data.get("ai_recommendations", []),
        revenue_impact=report_data.get("revenue_impact", {})
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return {
        "id": new_report.id,
        "clinic_id": new_report.clinic_id,
        "week_start": new_report.week_start.isoformat(),
        "week_end": new_report.week_end.isoformat(),
        "total_calls": new_report.total_calls,
        "avg_score": new_report.avg_score,
        "conversion_rate": new_report.conversion_rate,
        "top_agent_name": new_report.top_agent_name,
        "calls_by_day": new_report.calls_by_day,
        "sentiment_distribution": new_report.sentiment_distribution,
        "ai_summary": new_report.ai_summary,
        "ai_recommendations": new_report.ai_recommendations,
        "revenue_impact": new_report.revenue_impact,
        "created_at": new_report.created_at.isoformat()
    }


@router.get("/weekly/history")
def get_weekly_reports_history(
    limit: int = 12,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical weekly reports for the clinic.

    Returns up to `limit` past weekly reports, ordered by most recent first.
    Only managers and admins can view reports.
    """
    # Permission check
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    reports = db.query(WeeklyReport).filter(
        WeeklyReport.clinic_id == current_user.clinic_id
    ).order_by(desc(WeeklyReport.week_start)).offset(offset).limit(limit).all()

    total = db.query(WeeklyReport).filter(
        WeeklyReport.clinic_id == current_user.clinic_id
    ).count()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "reports": [
            {
                "id": r.id,
                "week_start": r.week_start.isoformat(),
                "week_end": r.week_end.isoformat(),
                "total_calls": r.total_calls,
                "avg_score": r.avg_score,
                "conversion_rate": r.conversion_rate,
                "top_agent_name": r.top_agent_name,
                "created_at": r.created_at.isoformat()
            }
            for r in reports
        ]
    }


@router.post("/weekly/generate")
async def manually_generate_report(
    week_start: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger the generation of a weekly report.

    Generates a new report for the specified week (or current week if not specified).
    Overwrites any existing report for that week.
    Only managers and admins can generate reports.

    Args:
        week_start: ISO format date string for week start (e.g., "2026-03-02")
    """
    # Permission check
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Parse week start date
    if week_start:
        try:
            parsed_week_start = datetime.fromisoformat(week_start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid week_start format. Use ISO format (YYYY-MM-DD)")
    else:
        today = datetime.utcnow()
        parsed_week_start = today - timedelta(days=today.weekday())

    # Generate report
    report_data = generate_weekly_report(db, current_user.clinic_id, parsed_week_start)

    # Check for existing report and update or create
    existing = db.query(WeeklyReport).filter(
        WeeklyReport.clinic_id == current_user.clinic_id,
        WeeklyReport.week_start == parsed_week_start.date()
    ).first()

    if existing:
        # Update existing report
        existing.total_calls = report_data["total_calls"]
        existing.avg_score = report_data["avg_score"]
        existing.conversion_rate = report_data["conversion_rate"]
        existing.top_agent_name = report_data["best_agent_name"]
        existing.calls_by_day = report_data["calls_by_day"]
        existing.sentiment_distribution = report_data["sentiment_distribution"]
        existing.ai_summary = report_data["ai_summary"]
        existing.ai_recommendations = report_data["ai_recommendations"]
        existing.revenue_impact = report_data["revenue_impact"]
        db.commit()
        db.refresh(existing)
        created = False
        report_record = existing
    else:
        # Create new report
        new_report = WeeklyReport(
            clinic_id=current_user.clinic_id,
            week_start=parsed_week_start.date(),
            week_end=(parsed_week_start + timedelta(days=7)).date(),
            total_calls=report_data["total_calls"],
            avg_score=report_data["avg_score"],
            conversion_rate=report_data["conversion_rate"],
            top_agent_id=None,
            top_agent_name=report_data["best_agent_name"],
            calls_by_day=report_data["calls_by_day"],
            sentiment_distribution=report_data["sentiment_distribution"],
            ai_summary=report_data["ai_summary"],
            ai_recommendations=report_data["ai_recommendations"],
            revenue_impact=report_data["revenue_impact"]
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        created = True
        report_record = new_report

    return {
        "id": report_record.id,
        "clinic_id": report_record.clinic_id,
        "week_start": report_record.week_start.isoformat(),
        "week_end": report_record.week_end.isoformat(),
        "total_calls": report_record.total_calls,
        "avg_score": report_record.avg_score,
        "conversion_rate": report_record.conversion_rate,
        "top_agent_name": report_record.top_agent_name,
        "best_agent_name": report_data.get("best_agent_name", "N/A"),
        "best_agent_score": report_data.get("best_agent_score", 0),
        "calls_by_day": report_record.calls_by_day,
        "sentiment_distribution": report_record.sentiment_distribution,
        "ai_summary": report_record.ai_summary,
        "ai_recommendations": report_record.ai_recommendations,
        "revenue_impact": report_record.revenue_impact,
        "score_breakdown": report_data.get("score_breakdown", {}),
        "agent_performance": report_data.get("agent_performance", {}),
        "created_at": report_record.created_at.isoformat(),
        "status": "created" if created else "updated"
    }


@router.get("/weekly/{report_id}")
def get_report_detail(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific weekly report.

    Only users from the same clinic can view reports.
    """
    report = db.query(WeeklyReport).filter(WeeklyReport.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.clinic_id != current_user.clinic_id:
        raise HTTPException(status_code=403, detail="You cannot access reports from other clinics")

    return {
        "id": report.id,
        "clinic_id": report.clinic_id,
        "week_start": report.week_start.isoformat(),
        "week_end": report.week_end.isoformat(),
        "total_calls": report.total_calls,
        "avg_score": report.avg_score,
        "conversion_rate": report.conversion_rate,
        "top_agent_id": report.top_agent_id,
        "top_agent_name": report.top_agent_name,
        "calls_by_day": report.calls_by_day,
        "sentiment_distribution": report.sentiment_distribution,
        "ai_summary": report.ai_summary,
        "ai_recommendations": report.ai_recommendations,
        "revenue_impact": report.revenue_impact,
        "created_at": report.created_at.isoformat()
    }
