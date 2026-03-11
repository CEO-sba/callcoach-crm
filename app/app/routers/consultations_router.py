"""
CallCoach CRM - Consultations Router
Video consultation management and AI analysis.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    VideoConsultation,
    ConsultationTranscription,
    ConsultationAnalysis
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consultations", tags=["consultations"])


@router.get("")
async def list_consultations(
    status: Optional[str] = None,
    contact_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all consultations."""
    query = db.query(VideoConsultation).filter(
        VideoConsultation.clinic_id == current_user.clinic_id
    )

    if status:
        query = query.filter(VideoConsultation.status == status)
    if contact_id:
        query = query.filter(VideoConsultation.contact_id == contact_id)

    consultations = query.order_by(
        VideoConsultation.scheduled_date.desc()
    ).offset(skip).limit(limit).all()

    return {
        "consultations": consultations,
        "total": query.count()
    }


@router.post("")
async def schedule_consultation(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Schedule a new video consultation.
    Generates a Google Meet link placeholder.
    Expected data: {
        "contact_id": "contact_id",
        "contact_name": "Name",
        "contact_email": "email@example.com",
        "scheduled_date": "2024-03-15T10:00:00",
        "title": "Consultation Title",
        "notes": "Optional notes"
    }
    """
    required_fields = ["contact_id", "contact_name", "contact_email", "scheduled_date"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    # Generate Google Meet link placeholder
    import uuid
    meet_link = f"https://meet.google.com/{uuid.uuid4().hex[:12]}"

    consultation = VideoConsultation(
        clinic_id=current_user.clinic_id,
        contact_id=data["contact_id"],
        contact_name=data["contact_name"],
        contact_email=data["contact_email"],
        scheduled_date=data["scheduled_date"],
        title=data.get("title", "Consultation"),
        notes=data.get("notes"),
        meet_link=meet_link,
        status="scheduled"
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    return {
        "status": "scheduled",
        "consultation_id": consultation.id,
        "meet_link": meet_link,
        "consultation": consultation
    }


@router.put("/{consultation_id}")
async def update_consultation(
    consultation_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update consultation details."""
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    update_data = data
    for field, value in update_data.items():
        if hasattr(consultation, field):
            setattr(consultation, field, value)

    consultation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(consultation)

    return {
        "status": "updated",
        "consultation_id": consultation.id,
        "consultation": consultation
    }


@router.post("/{consultation_id}/transcribe")
async def add_transcription(
    consultation_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add transcription to a consultation.
    Expected data: {
        "transcript": "Full transcription text",
        "duration_seconds": 3600,
        "language": "en"
    }
    """
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if "transcript" not in data:
        raise HTTPException(status_code=400, detail="transcript is required")

    transcription = ConsultationTranscription(
        consultation_id=consultation_id,
        transcript=data["transcript"],
        duration_seconds=data.get("duration_seconds"),
        language=data.get("language", "en")
    )
    db.add(transcription)

    # Update consultation status
    consultation.status = "completed"
    consultation.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(transcription)

    return {
        "status": "transcribed",
        "transcription_id": transcription.id,
        "transcription": transcription
    }


@router.post("/{consultation_id}/analyze")
async def analyze_consultation(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform AI analysis of consultation transcription.
    Requires transcription to exist first.
    """
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    # Check for existing transcription
    transcription = db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).first()

    if not transcription:
        raise HTTPException(
            status_code=400,
            detail="No transcription found. Add transcription first."
        )

    # Check if analysis already exists
    existing_analysis = db.query(ConsultationAnalysis).filter(
        ConsultationAnalysis.consultation_id == consultation_id
    ).first()

    if existing_analysis:
        return {
            "status": "exists",
            "analysis_id": existing_analysis.id,
            "analysis": existing_analysis
        }

    # Create new analysis record
    analysis = ConsultationAnalysis(
        consultation_id=consultation_id,
        transcript_id=transcription.id,
        key_topics=[],
        sentiment="neutral",
        summary="Analysis pending",
        recommendations=[]
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "status": "analyzing",
        "analysis_id": analysis.id,
        "analysis": analysis
    }


@router.get("/{consultation_id}/summary")
async def get_summary(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI summary of a consultation."""
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    # Get associated transcription
    transcription = db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).first()

    if not transcription:
        raise HTTPException(
            status_code=404,
            detail="No transcription found for this consultation"
        )

    # Get associated analysis
    analysis = db.query(ConsultationAnalysis).filter(
        ConsultationAnalysis.consultation_id == consultation_id
    ).first()

    return {
        "consultation_id": consultation_id,
        "consultation": consultation,
        "transcription": transcription,
        "analysis": analysis,
        "summary": {
            "key_topics": analysis.key_topics if analysis else [],
            "sentiment": analysis.sentiment if analysis else "unknown",
            "summary": analysis.summary if analysis else "No analysis available",
            "recommendations": analysis.recommendations if analysis else []
        }
    }
