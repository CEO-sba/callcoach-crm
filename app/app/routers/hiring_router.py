"""
CallCoach CRM - Hiring Router
Hiring management including job positions, candidates, and interviews.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    HiringPosition,
    HiringCandidate,
    HiringInterview
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hiring", tags=["hiring"])


@router.get("/positions")
async def list_positions(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all open positions."""
    query = db.query(HiringPosition).filter(
        HiringPosition.clinic_id == current_user.clinic_id
    )

    if status:
        query = query.filter(HiringPosition.status == status)

    positions = query.order_by(
        HiringPosition.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "positions": positions,
        "total": query.count()
    }


@router.post("/positions")
async def create_position(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new job position.
    Expected data: {
        "title": "Job Title",
        "description": "Job Description",
        "department": "Department",
        "salary_min": 50000,
        "salary_max": 80000,
        "requirements": ["Requirement 1", "Requirement 2"]
    }
    """
    required_fields = ["title", "description", "department"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    position = HiringPosition(
        clinic_id=current_user.clinic_id,
        title=data["title"],
        description=data["description"],
        department=data["department"],
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        requirements=data.get("requirements", []),
        status="open"
    )
    db.add(position)
    db.commit()
    db.refresh(position)

    return {
        "status": "created",
        "position_id": position.id,
        "position": position
    }


@router.put("/positions/{position_id}")
async def update_position(
    position_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a job position."""
    position = db.query(HiringPosition).filter(
        HiringPosition.id == position_id,
        HiringPosition.clinic_id == current_user.clinic_id
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    update_data = data
    for field, value in update_data.items():
        if hasattr(position, field):
            setattr(position, field, value)

    position.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(position)

    return {
        "status": "updated",
        "position_id": position.id,
        "position": position
    }


@router.get("/candidates")
async def list_candidates(
    position_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List candidates, filterable by position and status."""
    query = db.query(HiringCandidate).filter(
        HiringCandidate.clinic_id == current_user.clinic_id
    )

    if position_id:
        query = query.filter(HiringCandidate.position_id == position_id)
    if status:
        query = query.filter(HiringCandidate.status == status)

    candidates = query.order_by(
        HiringCandidate.created_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "candidates": candidates,
        "total": query.count()
    }


@router.post("/candidates")
async def add_candidate(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new candidate.
    Expected data: {
        "position_id": "position_id",
        "name": "Full Name",
        "email": "email@example.com",
        "phone": "phone_number",
        "resume_url": "url_to_resume",
        "notes": "Additional notes"
    }
    """
    required_fields = ["position_id", "name", "email"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    # Verify position exists
    position = db.query(HiringPosition).filter(
        HiringPosition.id == data["position_id"],
        HiringPosition.clinic_id == current_user.clinic_id
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    candidate = HiringCandidate(
        clinic_id=current_user.clinic_id,
        position_id=data["position_id"],
        name=data["name"],
        email=data["email"],
        phone=data.get("phone"),
        resume_url=data.get("resume_url"),
        notes=data.get("notes"),
        status="new"
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return {
        "status": "created",
        "candidate_id": candidate.id,
        "candidate": candidate
    }


@router.put("/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update candidate status and details."""
    candidate = db.query(HiringCandidate).filter(
        HiringCandidate.id == candidate_id,
        HiringCandidate.clinic_id == current_user.clinic_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    update_data = data
    for field, value in update_data.items():
        if hasattr(candidate, field):
            setattr(candidate, field, value)

    candidate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(candidate)

    return {
        "status": "updated",
        "candidate_id": candidate.id,
        "candidate": candidate
    }


@router.post("/candidates/{candidate_id}/interviews")
async def schedule_interview(
    candidate_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Schedule an interview for a candidate.
    Expected data: {
        "scheduled_date": "2024-03-15T10:00:00",
        "interviewer_id": "user_id",
        "interview_type": "phone|video|in_person",
        "notes": "Optional notes"
    }
    """
    candidate = db.query(HiringCandidate).filter(
        HiringCandidate.id == candidate_id,
        HiringCandidate.clinic_id == current_user.clinic_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    required_fields = ["scheduled_date", "interviewer_id", "interview_type"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    # Verify interviewer exists
    interviewer = db.query(User).filter(
        User.id == data["interviewer_id"],
        User.clinic_id == current_user.clinic_id
    ).first()

    if not interviewer:
        raise HTTPException(status_code=404, detail="Interviewer not found")

    interview = HiringInterview(
        clinic_id=current_user.clinic_id,
        candidate_id=candidate_id,
        interviewer_id=data["interviewer_id"],
        scheduled_date=data["scheduled_date"],
        interview_type=data["interview_type"],
        notes=data.get("notes"),
        status="scheduled"
    )
    db.add(interview)

    # Update candidate status
    candidate.status = "interview_scheduled"
    candidate.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(interview)

    return {
        "status": "scheduled",
        "interview_id": interview.id,
        "interview": interview
    }


@router.put("/interviews/{interview_id}")
async def update_interview(
    interview_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update interview with scores and feedback.
    Expected data: {
        "status": "completed|cancelled",
        "technical_score": 8,
        "communication_score": 9,
        "cultural_fit_score": 7,
        "overall_score": 8,
        "feedback": "Interview notes and feedback",
        "recommendation": "pass|maybe|fail"
    }
    """
    interview = db.query(HiringInterview).filter(
        HiringInterview.id == interview_id,
        HiringInterview.clinic_id == current_user.clinic_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    update_data = data
    for field, value in update_data.items():
        if hasattr(interview, field):
            setattr(interview, field, value)

    interview.completed_at = datetime.utcnow() if data.get("status") == "completed" else None
    interview.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interview)

    return {
        "status": "updated",
        "interview_id": interview.id,
        "interview": interview
    }


@router.get("/dashboard")
async def hiring_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get hiring dashboard with stats overview."""
    clinic_id = current_user.clinic_id

    # Count open positions
    open_positions = db.query(func.count(HiringPosition.id)).filter(
        HiringPosition.clinic_id == clinic_id,
        HiringPosition.status == "open"
    ).scalar() or 0

    # Pipeline counts
    total_candidates = db.query(func.count(HiringCandidate.id)).filter(
        HiringCandidate.clinic_id == clinic_id
    ).scalar() or 0

    new_candidates = db.query(func.count(HiringCandidate.id)).filter(
        HiringCandidate.clinic_id == clinic_id,
        HiringCandidate.status == "new"
    ).scalar() or 0

    interview_scheduled = db.query(func.count(HiringCandidate.id)).filter(
        HiringCandidate.clinic_id == clinic_id,
        HiringCandidate.status == "interview_scheduled"
    ).scalar() or 0

    offer_stage = db.query(func.count(HiringCandidate.id)).filter(
        HiringCandidate.clinic_id == clinic_id,
        HiringCandidate.status == "offer_extended"
    ).scalar() or 0

    hired = db.query(func.count(HiringCandidate.id)).filter(
        HiringCandidate.clinic_id == clinic_id,
        HiringCandidate.status == "hired"
    ).scalar() or 0

    rejected = db.query(func.count(HiringCandidate.id)).filter(
        HiringCandidate.clinic_id == clinic_id,
        HiringCandidate.status == "rejected"
    ).scalar() or 0

    # Upcoming interviews
    upcoming_interviews = db.query(func.count(HiringInterview.id)).filter(
        HiringInterview.clinic_id == clinic_id,
        HiringInterview.status == "scheduled"
    ).scalar() or 0

    return {
        "open_positions": open_positions,
        "total_candidates": total_candidates,
        "pipeline": {
            "new": new_candidates,
            "interview_scheduled": interview_scheduled,
            "offer_stage": offer_stage,
            "hired": hired,
            "rejected": rejected
        },
        "upcoming_interviews": upcoming_interviews
    }
