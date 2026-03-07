"""
CallCoach CRM - Pipeline Router
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import PipelineDeal, DealActivity, Call, User
from app.schemas import DealCreate, DealUpdate, DealOut
from app.auth import get_current_user
from app.services.ai_coach import assess_deal_health

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

VALID_STAGES = [
    "new_inquiry", "contacted", "consultation_booked",
    "consultation_done", "proposal_sent", "won", "lost"
]


@router.post("", response_model=DealOut)
def create_deal(deal: DealCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """Create a new pipeline deal."""
    new_deal = PipelineDeal(
        clinic_id=current_user.clinic_id,
        contact_name=deal.contact_name,
        contact_phone=deal.contact_phone,
        contact_email=deal.contact_email,
        title=deal.title,
        treatment_interest=deal.treatment_interest,
        deal_value=deal.deal_value,
        stage=deal.stage,
        priority=deal.priority,
        source=deal.source,
        next_follow_up=deal.next_follow_up,
        follow_up_notes=deal.follow_up_notes
    )
    db.add(new_deal)
    db.flush()

    activity = DealActivity(
        deal_id=new_deal.id,
        user_id=current_user.id,
        activity_type="stage_change",
        description=f"Deal created in stage: {deal.stage}",
        extra_data={"stage": deal.stage}
    )
    db.add(activity)
    db.commit()
    db.refresh(new_deal)
    return new_deal


@router.get("", response_model=list[DealOut])
def list_deals(
    stage: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List pipeline deals with optional filters."""
    query = db.query(PipelineDeal).filter(PipelineDeal.clinic_id == current_user.clinic_id)
    if stage:
        query = query.filter(PipelineDeal.stage == stage)
    if status:
        query = query.filter(PipelineDeal.status == status)
    if priority:
        query = query.filter(PipelineDeal.priority == priority)
    return query.order_by(PipelineDeal.updated_at.desc()).offset(skip).limit(limit).all()


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: str, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    """Get a specific deal with activities."""
    deal = db.query(PipelineDeal).filter(
        PipelineDeal.id == deal_id,
        PipelineDeal.clinic_id == current_user.clinic_id
    ).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.patch("/{deal_id}", response_model=DealOut)
def update_deal(deal_id: str, updates: DealUpdate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """Update a deal (stage change, details, etc.)."""
    deal = db.query(PipelineDeal).filter(
        PipelineDeal.id == deal_id,
        PipelineDeal.clinic_id == current_user.clinic_id
    ).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    update_data = updates.model_dump(exclude_unset=True)
    old_stage = deal.stage

    for key, value in update_data.items():
        setattr(deal, key, value)

    # Track stage changes
    if "stage" in update_data and update_data["stage"] != old_stage:
        activity = DealActivity(
            deal_id=deal.id,
            user_id=current_user.id,
            activity_type="stage_change",
            description=f"Stage changed: {old_stage} -> {update_data['stage']}",
            extra_data={"from": old_stage, "to": update_data["stage"]}
        )
        db.add(activity)

        # Auto-update status for terminal stages
        if update_data["stage"] == "won":
            deal.status = "won"
            deal.actual_close_date = datetime.utcnow()
        elif update_data["stage"] == "lost":
            deal.status = "lost"
            deal.actual_close_date = datetime.utcnow()

    # Track status changes
    if "status" in update_data:
        activity = DealActivity(
            deal_id=deal.id,
            user_id=current_user.id,
            activity_type="note",
            description=f"Status changed to: {update_data['status']}",
            extra_data={"status": update_data["status"]}
        )
        db.add(activity)

    deal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(deal)
    return deal


@router.post("/{deal_id}/assess-health")
async def assess_health(deal_id: str, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """Run AI assessment on deal health."""
    deal = db.query(PipelineDeal).filter(
        PipelineDeal.id == deal_id,
        PipelineDeal.clinic_id == current_user.clinic_id
    ).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Gather call summaries for this deal
    calls = db.query(Call).filter(Call.deal_id == deal_id).order_by(Call.call_date.desc()).all()
    call_summaries = [
        {"date": c.call_date.isoformat(), "summary": c.ai_summary or "No summary", "sentiment": c.ai_sentiment}
        for c in calls
    ]

    days_in_stage = (datetime.utcnow() - deal.updated_at).days

    deal_info = {
        "title": deal.title,
        "contact_name": deal.contact_name,
        "treatment_interest": deal.treatment_interest,
        "deal_value": deal.deal_value,
        "stage": deal.stage,
        "source": deal.source,
        "total_calls": len(calls)
    }

    assessment = await assess_deal_health(
        deal_info=deal_info,
        call_summaries=call_summaries,
        touchpoint_count=deal.total_touchpoints,
        days_in_stage=days_in_stage
    )

    # Update deal with AI insights
    deal.ai_win_probability = assessment.get("win_probability")
    deal.ai_recommended_action = assessment.get("recommended_action")
    deal.ai_deal_health = assessment.get("health")
    db.commit()

    return assessment


@router.get("/stages/summary")
def get_stage_summary(db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """Get deal counts and values per pipeline stage."""
    from sqlalchemy import func
    results = db.query(
        PipelineDeal.stage,
        func.count(PipelineDeal.id).label("count"),
        func.sum(PipelineDeal.deal_value).label("total_value")
    ).filter(
        PipelineDeal.clinic_id == current_user.clinic_id,
        PipelineDeal.status == "open"
    ).group_by(PipelineDeal.stage).all()

    stages_data = []
    for stage in VALID_STAGES:
        match = next((r for r in results if r.stage == stage), None)
        stages_data.append({
            "stage": stage,
            "count": match.count if match else 0,
            "total_value": float(match.total_value or 0) if match else 0
        })

    return stages_data
