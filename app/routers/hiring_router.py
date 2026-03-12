"""
CallCoach CRM - Hiring Router (v2.1 - Full AI Integration)
Complete hiring pipeline with AI candidate evaluation, interview
question generation, JD creation, and hiring coach.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    HiringPosition,
    HiringCandidate,
    HiringInterview,
)
from app.services.hiring_ai_coach import (
    evaluate_candidate as ai_evaluate,
    generate_interview_questions,
    generate_job_description,
    ask_hiring_coach,
)

from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hiring", tags=["hiring"])


# ============================================================================
# 1. DASHBOARD
# ============================================================================

@router.get("/dashboard")
async def hiring_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hiring analytics dashboard."""
    clinic_id = current_user.clinic_id

    open_positions = db.query(func.count(HiringPosition.id)).filter(
        HiringPosition.clinic_id == clinic_id,
        HiringPosition.status == "open"
    ).scalar() or 0

    total_candidates = db.query(func.count(HiringCandidate.id)).filter(
        HiringCandidate.clinic_id == clinic_id
    ).scalar() or 0

    # Pipeline breakdown
    stages = ["applied", "screening", "interview_scheduled", "interview_done", "offer_sent", "hired", "rejected"]
    pipeline = {}
    for stage in stages:
        count = db.query(func.count(HiringCandidate.id)).filter(
            HiringCandidate.clinic_id == clinic_id,
            HiringCandidate.status == stage
        ).scalar() or 0
        pipeline[stage] = count

    upcoming_interviews = db.query(HiringInterview).join(
        HiringCandidate, HiringInterview.candidate_id == HiringCandidate.id
    ).filter(
        HiringCandidate.clinic_id == clinic_id,
        HiringInterview.status == "scheduled"
    ).order_by(HiringInterview.scheduled_at.asc()).limit(10).all()

    upcoming_list = []
    for i in upcoming_interviews:
        candidate = db.query(HiringCandidate).filter(HiringCandidate.id == i.candidate_id).first()
        upcoming_list.append({
            "interview_id": i.id,
            "candidate_name": candidate.name if candidate else "Unknown",
            "scheduled_at": str(i.scheduled_at) if i.scheduled_at else None,
            "recommendation": i.recommendation,
        })

    # Hire rate
    hired = pipeline.get("hired", 0)
    hire_rate = round(hired / total_candidates * 100, 1) if total_candidates > 0 else 0

    return {
        "open_positions": open_positions,
        "total_candidates": total_candidates,
        "pipeline": pipeline,
        "hire_rate": hire_rate,
        "upcoming_interviews": upcoming_list,
    }


# ============================================================================
# 2. POSITIONS
# ============================================================================

@router.get("/positions")
async def list_positions(
    status: Optional[str] = None,
    department: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List job positions with filters."""
    query = db.query(HiringPosition).filter(
        HiringPosition.clinic_id == current_user.clinic_id
    )

    if status:
        query = query.filter(HiringPosition.status == status)
    if department:
        query = query.filter(HiringPosition.department == department)

    total = query.count()
    positions = query.order_by(desc(HiringPosition.created_at)).offset(skip).limit(limit).all()

    results = []
    for p in positions:
        candidate_count = db.query(func.count(HiringCandidate.id)).filter(
            HiringCandidate.position_id == p.id
        ).scalar() or 0

        results.append({
            "id": p.id,
            "title": p.title,
            "department": p.department,
            "description": p.description,
            "requirements": p.requirements or [],
            "salary_range": p.salary_range,
            "status": p.status,
            "candidate_count": candidate_count,
            "created_at": str(p.created_at) if p.created_at else None,
        })

    return {"positions": results, "total": total}


@router.post("/positions")
async def create_position(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job position."""
    if "title" not in data or "department" not in data:
        raise HTTPException(status_code=400, detail="title and department required")

    position = HiringPosition(
        clinic_id=current_user.clinic_id,
        title=data["title"],
        department=data["department"],
        description=data.get("description", ""),
        requirements=data.get("requirements", []),
        salary_range=data.get("salary_range", ""),
        status="open",
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    log_activity(db, current_user.clinic_id, "hr", "position_created",
                 {"title": data["title"], "department": data["department"],
                  "salary_range": data.get("salary_range")},
                 current_user.email, related_id=position.id, related_type="position")

    return {"status": "created", "position_id": position.id}


@router.put("/positions/{position_id}")
async def update_position(
    position_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a position."""
    position = db.query(HiringPosition).filter(
        HiringPosition.id == position_id,
        HiringPosition.clinic_id == current_user.clinic_id
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    allowed = ["title", "department", "description", "requirements", "salary_range", "status"]
    for field, value in data.items():
        if field in allowed:
            setattr(position, field, value)

    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "position_updated",
                 {"position_id": position_id, "fields_updated": list(data.keys())},
                 current_user.email, related_id=position_id, related_type="position")
    return {"status": "updated", "position_id": position.id}


@router.delete("/positions/{position_id}")
async def delete_position(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a position and its candidates."""
    position = db.query(HiringPosition).filter(
        HiringPosition.id == position_id,
        HiringPosition.clinic_id == current_user.clinic_id
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    title = position.title
    db.delete(position)  # cascade deletes candidates and interviews
    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "position_deleted",
                 {"position_id": position_id, "title": title},
                 current_user.email)

    return {"status": "deleted"}


# ============================================================================
# 3. AI JOB DESCRIPTION GENERATOR
# ============================================================================

@router.post("/positions/{position_id}/generate-jd")
async def generate_jd(
    position_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an AI-powered job description for a position."""
    position = db.query(HiringPosition).filter(
        HiringPosition.id == position_id,
        HiringPosition.clinic_id == current_user.clinic_id
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    data = data or {}
    result = await generate_job_description(
        position_title=position.title,
        department=position.department,
        requirements=position.requirements or [],
        salary_range=position.salary_range or "",
        additional_context=data.get("context", ""),
    )

    log_activity(db, current_user.clinic_id, "hr", "job_description_generated",
                 {"position_id": position_id, "title": position.title,
                  "department": position.department},
                 current_user.email, related_id=position_id, related_type="position")
    return {
        "position_id": position_id,
        "job_description": result,
    }


# ============================================================================
# 4. CANDIDATES
# ============================================================================

@router.get("/candidates")
async def list_candidates(
    position_id: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[float] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List candidates with filters."""
    query = db.query(HiringCandidate).filter(
        HiringCandidate.clinic_id == current_user.clinic_id
    )

    if position_id:
        query = query.filter(HiringCandidate.position_id == position_id)
    if status:
        query = query.filter(HiringCandidate.status == status)
    if source:
        query = query.filter(HiringCandidate.source == source)
    if min_score is not None:
        query = query.filter(HiringCandidate.score >= min_score)

    total = query.count()
    candidates = query.order_by(desc(HiringCandidate.created_at)).offset(skip).limit(limit).all()

    results = []
    for c in candidates:
        position = db.query(HiringPosition).filter(HiringPosition.id == c.position_id).first()
        interview_count = db.query(func.count(HiringInterview.id)).filter(
            HiringInterview.candidate_id == c.id
        ).scalar() or 0

        results.append({
            "id": c.id,
            "position_id": c.position_id,
            "position_title": position.title if position else "Unknown",
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "resume_url": c.resume_url,
            "status": c.status,
            "score": c.score,
            "source": c.source,
            "interview_count": interview_count,
            "applied_at": str(c.applied_at) if c.applied_at else None,
            "created_at": str(c.created_at) if c.created_at else None,
        })

    return {"candidates": results, "total": total}


@router.post("/candidates")
async def add_candidate(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new candidate."""
    if "position_id" not in data or "name" not in data:
        raise HTTPException(status_code=400, detail="position_id and name required")

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
        email=data.get("email"),
        phone=data.get("phone"),
        resume_url=data.get("resume_url"),
        cover_letter=data.get("cover_letter"),
        source=data.get("source", "direct"),
        status="applied",
        score=0,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    log_activity(db, current_user.clinic_id, "hr", "candidate_added",
                 {"name": data["name"], "position_id": data["position_id"],
                  "source": data.get("source", "direct")},
                 current_user.email, related_id=candidate.id, related_type="candidate")

    return {"status": "created", "candidate_id": candidate.id}


@router.get("/candidates/{candidate_id}")
async def get_candidate(
    candidate_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full candidate details with interviews."""
    candidate = db.query(HiringCandidate).filter(
        HiringCandidate.id == candidate_id,
        HiringCandidate.clinic_id == current_user.clinic_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    position = db.query(HiringPosition).filter(HiringPosition.id == candidate.position_id).first()

    interviews = db.query(HiringInterview).filter(
        HiringInterview.candidate_id == candidate_id
    ).order_by(desc(HiringInterview.scheduled_at)).all()

    interview_list = []
    for i in interviews:
        interviewer = db.query(User).filter(User.id == i.interviewer_id).first()
        interview_list.append({
            "id": i.id,
            "interviewer_name": interviewer.name if interviewer else "Unknown",
            "scheduled_at": str(i.scheduled_at) if i.scheduled_at else None,
            "completed_at": str(i.completed_at) if i.completed_at else None,
            "status": i.status,
            "score_card": i.score_card or {},
            "notes": i.notes,
            "recommendation": i.recommendation,
        })

    return {
        "candidate": {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "resume_url": candidate.resume_url,
            "cover_letter": candidate.cover_letter,
            "status": candidate.status,
            "score": candidate.score,
            "source": candidate.source,
            "interview_notes": candidate.interview_notes,
            "applied_at": str(candidate.applied_at) if candidate.applied_at else None,
        },
        "position": {
            "id": position.id if position else None,
            "title": position.title if position else "Unknown",
            "department": position.department if position else "",
        },
        "interviews": interview_list,
    }


@router.put("/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update candidate details and status."""
    candidate = db.query(HiringCandidate).filter(
        HiringCandidate.id == candidate_id,
        HiringCandidate.clinic_id == current_user.clinic_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    allowed = ["name", "email", "phone", "resume_url", "cover_letter", "status", "score", "source", "interview_notes"]
    for field, value in data.items():
        if field in allowed:
            setattr(candidate, field, value)

    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "candidate_updated",
                 {"candidate_id": candidate_id, "fields_updated": list(data.keys()),
                  "new_status": data.get("status")},
                 current_user.email, related_id=candidate_id, related_type="candidate")
    return {"status": "updated", "candidate_id": candidate.id}


# ============================================================================
# 5. AI CANDIDATE EVALUATION
# ============================================================================

@router.post("/candidates/{candidate_id}/ai-evaluate")
async def ai_evaluate_candidate(
    candidate_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run AI evaluation on a candidate using interview notes and resume."""
    candidate = db.query(HiringCandidate).filter(
        HiringCandidate.id == candidate_id,
        HiringCandidate.clinic_id == current_user.clinic_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    position = db.query(HiringPosition).filter(HiringPosition.id == candidate.position_id).first()

    # Gather interview notes
    interviews = db.query(HiringInterview).filter(
        HiringInterview.candidate_id == candidate_id
    ).all()

    interview_text = ""
    for i in interviews:
        interviewer = db.query(User).filter(User.id == i.interviewer_id).first()
        interview_text += f"\nInterview by {interviewer.name if interviewer else 'Unknown'}:\n"
        interview_text += f"Notes: {i.notes or 'No notes'}\n"
        interview_text += f"Score Card: {i.score_card or 'Not scored'}\n"
        interview_text += f"Recommendation: {i.recommendation or 'Not given'}\n"

    data = data or {}
    result = await ai_evaluate(
        candidate_name=candidate.name,
        position_title=position.title if position else "Unknown",
        department=position.department if position else "",
        interview_notes=interview_text or data.get("interview_notes", "No interview data available"),
        resume_summary=data.get("resume_summary", ""),
        additional_context=data.get("context", ""),
    )

    # Update candidate score
    overall = result.get("overall_score", 0)
    if overall > 0:
        candidate.score = overall
        candidate.interview_notes = candidate.interview_notes or {}
        candidate.interview_notes["ai_evaluation"] = result
        db.commit()

    log_activity(db, current_user.clinic_id, "hr", "candidate_ai_evaluated",
                 {"candidate_id": candidate_id, "candidate_name": candidate.name,
                  "position": position.title if position else "Unknown",
                  "overall_score": result.get("overall_score", 0)},
                 current_user.email, related_id=candidate_id, related_type="candidate")
    return {
        "candidate_id": candidate_id,
        "evaluation": result,
    }


# ============================================================================
# 6. INTERVIEWS
# ============================================================================

@router.post("/candidates/{candidate_id}/interviews")
async def schedule_interview(
    candidate_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule an interview for a candidate."""
    candidate = db.query(HiringCandidate).filter(
        HiringCandidate.id == candidate_id,
        HiringCandidate.clinic_id == current_user.clinic_id
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if "scheduled_at" not in data or "interviewer_id" not in data:
        raise HTTPException(status_code=400, detail="scheduled_at and interviewer_id required")

    interviewer = db.query(User).filter(
        User.id == data["interviewer_id"],
        User.clinic_id == current_user.clinic_id
    ).first()
    if not interviewer:
        raise HTTPException(status_code=404, detail="Interviewer not found")

    interview = HiringInterview(
        candidate_id=candidate_id,
        interviewer_id=data["interviewer_id"],
        scheduled_at=data["scheduled_at"],
        notes=data.get("notes"),
        status="scheduled",
    )
    db.add(interview)

    candidate.status = "interview_scheduled"
    db.commit()
    db.refresh(interview)
    log_activity(db, current_user.clinic_id, "hr", "interview_scheduled",
                 {"candidate_id": candidate_id, "candidate_name": candidate.name,
                  "scheduled_at": data["scheduled_at"]},
                 current_user.email, related_id=interview.id, related_type="interview")

    return {"status": "scheduled", "interview_id": interview.id}


@router.put("/interviews/{interview_id}")
async def update_interview(
    interview_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update interview with scores, notes, and recommendation."""
    interview = db.query(HiringInterview).filter(
        HiringInterview.id == interview_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Verify access through candidate
    candidate = db.query(HiringCandidate).filter(
        HiringCandidate.id == interview.candidate_id,
        HiringCandidate.clinic_id == current_user.clinic_id
    ).first()
    if not candidate:
        raise HTTPException(status_code=403, detail="Access denied")

    allowed = ["status", "score_card", "notes", "recommendation", "scheduled_at"]
    for field, value in data.items():
        if field in allowed:
            setattr(interview, field, value)

    if data.get("status") == "completed":
        interview.completed_at = datetime.utcnow()
        candidate.status = "interview_done"

    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "interview_updated",
                 {"interview_id": interview_id, "candidate_id": interview.candidate_id,
                  "status": data.get("status"), "has_recommendation": bool(data.get("recommendation"))},
                 current_user.email, related_id=interview_id, related_type="interview")
    return {"status": "updated", "interview_id": interview.id}


# ============================================================================
# 7. AI INTERVIEW QUESTION GENERATOR
# ============================================================================

@router.post("/positions/{position_id}/generate-questions")
async def generate_questions(
    position_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-tailored interview questions for a position."""
    position = db.query(HiringPosition).filter(
        HiringPosition.id == position_id,
        HiringPosition.clinic_id == current_user.clinic_id
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    data = data or {}
    result = await generate_interview_questions(
        position_title=position.title,
        department=position.department,
        requirements=position.requirements,
        interview_round=data.get("round", "screening"),
        candidate_resume=data.get("candidate_resume", ""),
    )

    log_activity(db, current_user.clinic_id, "hr", "interview_questions_generated",
                 {"position_id": position_id, "title": position.title,
                  "round": data.get("round", "screening")},
                 current_user.email, related_id=position_id, related_type="position")
    return {
        "position_id": position_id,
        "position_title": position.title,
        "interview_round": data.get("round", "screening"),
        "questions": result,
    }


# ============================================================================
# 8. HIRING AI COACH
# ============================================================================

@router.post("/coach/ask")
async def ask_coach(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask the Hiring AI Coach a question about hiring, HR, or team building."""
    question = data.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="question required")

    result = await ask_hiring_coach(
        question=question,
        context=data.get("context", {}),
    )

    log_activity(db, current_user.clinic_id, "coaching", "hiring_coach_asked",
                 {"question": question[:100]},
                 current_user.email)
    return {"question": question, "answer": result.get("answer", "")}
