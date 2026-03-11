"""
CallCoach CRM - Consultations Router (v2.1 - Full AI Integration)
Video consultation management, AI analysis, coaching, and patient summaries.
Powered by SBA Consultation AI Coach.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_expanded import (
    VideoConsultation,
    ConsultationTranscription,
    ConsultationAnalysis,
    PatientProcedureHistory,
    PatientRecord,
)
from app.services.consultation_ai_coach import (
    analyze_consultation as ai_analyze,
    ask_consultation_coach,
    generate_consultation_summary_for_patient,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consultations", tags=["consultations"])


# ============================================================================
# 1. LIST & DASHBOARD
# ============================================================================

@router.get("/dashboard")
async def consultations_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Consultation analytics dashboard."""
    clinic_id = current_user.clinic_id
    base = db.query(VideoConsultation).filter(VideoConsultation.clinic_id == clinic_id)

    total = base.count()
    scheduled = base.filter(VideoConsultation.status == "scheduled").count()
    completed = base.filter(VideoConsultation.status == "completed").count()
    cancelled = base.filter(VideoConsultation.status == "cancelled").count()
    no_show = base.filter(VideoConsultation.status == "no_show").count()

    # Average analysis scores
    analyses = db.query(ConsultationAnalysis).join(
        VideoConsultation, ConsultationAnalysis.consultation_id == VideoConsultation.id
    ).filter(VideoConsultation.clinic_id == clinic_id).all()

    avg_sentiment = 0.0
    if analyses:
        scores = [a.sentiment_score for a in analyses if a.sentiment_score is not None]
        avg_sentiment = sum(scores) / len(scores) if scores else 0.0

    # Recent consultations
    recent = base.order_by(desc(VideoConsultation.created_at)).limit(10).all()
    recent_list = []
    for c in recent:
        recent_list.append({
            "id": c.id,
            "patient_name": c.patient_name,
            "doctor_name": c.doctor_name,
            "scheduled_at": str(c.scheduled_at) if c.scheduled_at else None,
            "status": c.status,
            "duration_minutes": c.duration_minutes,
        })

    return {
        "total_consultations": total,
        "scheduled": scheduled,
        "completed": completed,
        "cancelled": cancelled,
        "no_show": no_show,
        "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
        "no_show_rate": round(no_show / total * 100, 1) if total > 0 else 0,
        "average_sentiment_score": round(avg_sentiment, 2),
        "total_analyses": len(analyses),
        "recent_consultations": recent_list,
    }


@router.get("")
async def list_consultations(
    status: Optional[str] = None,
    lead_id: Optional[str] = None,
    doctor_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List consultations with filters."""
    query = db.query(VideoConsultation).filter(
        VideoConsultation.clinic_id == current_user.clinic_id
    )

    if status:
        query = query.filter(VideoConsultation.status == status)
    if lead_id:
        query = query.filter(VideoConsultation.lead_id == lead_id)
    if doctor_name:
        query = query.filter(VideoConsultation.doctor_name.ilike(f"%{doctor_name}%"))
    if date_from:
        query = query.filter(VideoConsultation.scheduled_at >= date_from)
    if date_to:
        query = query.filter(VideoConsultation.scheduled_at <= date_to)

    total = query.count()
    consultations = query.order_by(
        desc(VideoConsultation.scheduled_at)
    ).offset(skip).limit(limit).all()

    results = []
    for c in consultations:
        # Check if analysis exists
        analysis = db.query(ConsultationAnalysis).filter(
            ConsultationAnalysis.consultation_id == c.id
        ).first()

        results.append({
            "id": c.id,
            "lead_id": c.lead_id,
            "doctor_name": c.doctor_name,
            "patient_name": c.patient_name,
            "patient_phone": c.patient_phone,
            "patient_email": c.patient_email,
            "meet_link": c.meet_link,
            "scheduled_at": str(c.scheduled_at) if c.scheduled_at else None,
            "started_at": str(c.started_at) if c.started_at else None,
            "ended_at": str(c.ended_at) if c.ended_at else None,
            "duration_minutes": c.duration_minutes,
            "status": c.status,
            "recording_url": c.recording_url,
            "has_transcription": bool(c.transcription),
            "has_analysis": analysis is not None,
            "ai_summary": c.ai_summary,
            "created_at": str(c.created_at) if c.created_at else None,
        })

    return {"consultations": results, "total": total}


@router.get("/{consultation_id}")
async def get_consultation(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full consultation details with transcription and analysis."""
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    # Get transcription
    transcription = db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).first()

    # Get analysis
    analysis = db.query(ConsultationAnalysis).filter(
        ConsultationAnalysis.consultation_id == consultation_id
    ).first()

    analysis_data = None
    if analysis:
        analysis_data = {
            "id": analysis.id,
            "summary": analysis.summary,
            "key_concerns": analysis.key_concerns or [],
            "recommended_procedures": analysis.recommended_procedures or [],
            "follow_up_actions": analysis.follow_up_actions or [],
            "sentiment_score": analysis.sentiment_score,
            "ai_notes": analysis.ai_notes,
            "created_at": str(analysis.created_at) if analysis.created_at else None,
        }

    transcription_data = None
    if transcription:
        transcription_data = {
            "id": transcription.id,
            "content": transcription.content,
            "language": transcription.language,
            "duration_seconds": transcription.duration_seconds,
            "created_at": str(transcription.created_at) if transcription.created_at else None,
        }

    return {
        "consultation": {
            "id": consultation.id,
            "lead_id": consultation.lead_id,
            "doctor_name": consultation.doctor_name,
            "patient_name": consultation.patient_name,
            "patient_phone": consultation.patient_phone,
            "patient_email": consultation.patient_email,
            "meet_link": consultation.meet_link,
            "scheduled_at": str(consultation.scheduled_at) if consultation.scheduled_at else None,
            "started_at": str(consultation.started_at) if consultation.started_at else None,
            "ended_at": str(consultation.ended_at) if consultation.ended_at else None,
            "duration_minutes": consultation.duration_minutes,
            "status": consultation.status,
            "recording_url": consultation.recording_url,
            "transcription_text": consultation.transcription,
            "ai_summary": consultation.ai_summary,
            "ai_suggestions": consultation.ai_suggestions,
            "ai_key_points": consultation.ai_key_points,
            "created_at": str(consultation.created_at) if consultation.created_at else None,
        },
        "transcription": transcription_data,
        "analysis": analysis_data,
    }


# ============================================================================
# 2. SCHEDULE & MANAGE CONSULTATIONS
# ============================================================================

@router.post("")
async def schedule_consultation(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Schedule a new consultation.
    Required: patient_name, scheduled_at
    Optional: lead_id, doctor_name, patient_phone, patient_email, meet_link, notes
    """
    if "patient_name" not in data or "scheduled_at" not in data:
        raise HTTPException(
            status_code=400,
            detail="patient_name and scheduled_at are required"
        )

    consultation = VideoConsultation(
        clinic_id=current_user.clinic_id,
        lead_id=data.get("lead_id"),
        doctor_name=data.get("doctor_name", "Doctor"),
        patient_name=data["patient_name"],
        patient_phone=data.get("patient_phone"),
        patient_email=data.get("patient_email"),
        meet_link=data.get("meet_link", ""),
        scheduled_at=data["scheduled_at"],
        status="scheduled",
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    return {
        "status": "scheduled",
        "consultation_id": consultation.id,
        "meet_link": consultation.meet_link,
        "scheduled_at": str(consultation.scheduled_at),
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

    allowed_fields = [
        "lead_id", "doctor_name", "patient_name", "patient_phone",
        "patient_email", "meet_link", "scheduled_at", "started_at",
        "ended_at", "duration_minutes", "status", "recording_url",
    ]
    for field, value in data.items():
        if field in allowed_fields and hasattr(consultation, field):
            setattr(consultation, field, value)

    db.commit()
    db.refresh(consultation)

    return {"status": "updated", "consultation_id": consultation.id}


@router.put("/{consultation_id}/status")
async def update_status(
    consultation_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update consultation status (scheduled, in_progress, completed, cancelled, no_show)."""
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    new_status = data.get("status")
    valid_statuses = ["scheduled", "in_progress", "completed", "cancelled", "no_show"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {valid_statuses}")

    consultation.status = new_status
    if new_status == "in_progress" and not consultation.started_at:
        consultation.started_at = datetime.utcnow()
    elif new_status == "completed" and not consultation.ended_at:
        consultation.ended_at = datetime.utcnow()
        if consultation.started_at:
            delta = consultation.ended_at - consultation.started_at
            consultation.duration_minutes = int(delta.total_seconds() / 60)

    db.commit()
    return {"status": "updated", "new_status": new_status}


@router.delete("/{consultation_id}")
async def delete_consultation(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a consultation and associated records."""
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    # Delete associated transcriptions and analyses
    db.query(ConsultationAnalysis).filter(
        ConsultationAnalysis.consultation_id == consultation_id
    ).delete()
    db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).delete()
    db.delete(consultation)
    db.commit()

    return {"status": "deleted", "consultation_id": consultation_id}


# ============================================================================
# 3. TRANSCRIPTION
# ============================================================================

@router.post("/{consultation_id}/transcribe")
async def add_transcription(
    consultation_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add or update transcription for a consultation.
    Required: content (the transcript text)
    Optional: duration_seconds, language
    Also stores a copy in the VideoConsultation.transcription field.
    """
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    transcript_text = data.get("content") or data.get("transcript")
    if not transcript_text:
        raise HTTPException(status_code=400, detail="content (transcript text) is required")

    # Check if transcription already exists, update if so
    existing = db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).first()

    if existing:
        existing.content = transcript_text
        existing.duration_seconds = data.get("duration_seconds", existing.duration_seconds)
        existing.language = data.get("language", existing.language)
        transcription = existing
    else:
        transcription = ConsultationTranscription(
            consultation_id=consultation_id,
            content=transcript_text,
            duration_seconds=data.get("duration_seconds"),
            language=data.get("language", "en"),
        )
        db.add(transcription)

    # Also store transcript directly on consultation for quick access
    consultation.transcription = transcript_text
    if data.get("duration_seconds"):
        consultation.duration_minutes = int(data["duration_seconds"] / 60)
    consultation.status = "completed"

    db.commit()
    db.refresh(transcription)

    return {
        "status": "transcribed",
        "transcription_id": transcription.id,
        "consultation_id": consultation_id,
        "word_count": len(transcript_text.split()),
    }


# ============================================================================
# 4. AI ANALYSIS (Real Claude Integration)
# ============================================================================

@router.post("/{consultation_id}/analyze")
async def analyze_consultation_endpoint(
    consultation_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run AI analysis on a consultation transcript using SBA Consultation Framework.
    Requires transcription to exist. Set force=true to re-analyze.
    """
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    # Get transcript text (from transcription record or consultation field)
    transcription = db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).first()

    transcript_text = None
    if transcription:
        transcript_text = transcription.content
    elif consultation.transcription:
        transcript_text = consultation.transcription

    if not transcript_text:
        raise HTTPException(
            status_code=400,
            detail="No transcription found. Add transcription first."
        )

    # Check existing analysis
    existing = db.query(ConsultationAnalysis).filter(
        ConsultationAnalysis.consultation_id == consultation_id
    ).first()

    if existing and not force:
        return {
            "status": "exists",
            "analysis_id": existing.id,
            "analysis": {
                "summary": existing.summary,
                "key_concerns": existing.key_concerns,
                "recommended_procedures": existing.recommended_procedures,
                "follow_up_actions": existing.follow_up_actions,
                "sentiment_score": existing.sentiment_score,
                "ai_notes": existing.ai_notes,
            },
            "message": "Analysis already exists. Use force=true to re-analyze."
        }

    # Run real AI analysis
    try:
        ai_result = await ai_analyze(
            transcript=transcript_text,
            doctor_name=consultation.doctor_name or "Doctor",
            patient_name=consultation.patient_name or "Patient",
            duration_minutes=consultation.duration_minutes or 0,
        )

        # Extract data from AI result
        summary = ai_result.get("summary", "Analysis completed.")
        key_concerns = ai_result.get("patient_concerns", [])
        procedures = ai_result.get("procedures_discussed", [])
        follow_ups = ai_result.get("follow_up_actions", [])
        sentiment = ai_result.get("sentiment", "neutral")

        # Calculate overall sentiment score from AI scores
        scores = ai_result.get("scores", {})
        overall_score = scores.get("overall", 0)
        sentiment_score = overall_score / 100.0 if overall_score else 0.5

        # Build detailed AI notes from the full analysis
        ai_notes_parts = []

        # Scoring details
        scoring = ai_result.get("scoring_details", {})
        if scoring:
            ai_notes_parts.append("SCORING BREAKDOWN:")
            for dim, explanation in scoring.items():
                score_val = scores.get(dim, 0)
                ai_notes_parts.append(f"  {dim}: {score_val}/100 - {explanation}")

        # What went well
        went_well = ai_result.get("what_went_well", [])
        if went_well:
            ai_notes_parts.append("\nWHAT WENT WELL:")
            for item in went_well:
                ai_notes_parts.append(f"  + {item}")

        # Improvements
        improvements = ai_result.get("improvements", [])
        if improvements:
            ai_notes_parts.append("\nIMPROVEMENTS:")
            for imp in improvements:
                if isinstance(imp, dict):
                    ai_notes_parts.append(f"  Area: {imp.get('area', '')}")
                    ai_notes_parts.append(f"  Current: {imp.get('current', '')}")
                    ai_notes_parts.append(f"  Suggested: {imp.get('suggested', '')}")
                    ai_notes_parts.append(f"  Example: \"{imp.get('example_phrase', '')}\"")
                    ai_notes_parts.append("")
                else:
                    ai_notes_parts.append(f"  - {imp}")

        # Buying signals
        buying = ai_result.get("buying_signals", [])
        if buying:
            ai_notes_parts.append("BUYING SIGNALS:")
            for sig in buying:
                if isinstance(sig, dict):
                    ai_notes_parts.append(f"  [{sig.get('strength', '')}] {sig.get('signal', '')}")
                else:
                    ai_notes_parts.append(f"  - {sig}")

        # Objections
        objections = ai_result.get("objections_raised", [])
        if objections:
            ai_notes_parts.append("\nOBJECTIONS:")
            for obj in objections:
                if isinstance(obj, dict):
                    handled = "Handled" if obj.get("handled") else "Missed"
                    quality = obj.get("handling_quality", "")
                    ai_notes_parts.append(f"  [{handled}/{quality}] {obj.get('objection', '')}")
                else:
                    ai_notes_parts.append(f"  - {obj}")

        # Patient readiness
        readiness = ai_result.get("patient_readiness", {})
        if readiness:
            ai_notes_parts.append(f"\nPATIENT READINESS: {readiness.get('level', 'unknown')}")
            ai_notes_parts.append(f"  Next best action: {readiness.get('next_best_action', '')}")

        ai_notes = "\n".join(ai_notes_parts)

        # Create or update analysis record
        if existing:
            existing.summary = summary
            existing.key_concerns = key_concerns
            existing.recommended_procedures = procedures
            existing.follow_up_actions = follow_ups
            existing.sentiment_score = sentiment_score
            existing.ai_notes = ai_notes
            existing.created_at = datetime.utcnow()
            analysis = existing
        else:
            analysis = ConsultationAnalysis(
                consultation_id=consultation_id,
                summary=summary,
                key_concerns=key_concerns,
                recommended_procedures=procedures,
                follow_up_actions=follow_ups,
                sentiment_score=sentiment_score,
                ai_notes=ai_notes,
            )
            db.add(analysis)

        # Update consultation with quick-access AI fields
        consultation.ai_summary = summary
        consultation.ai_suggestions = {
            "scores": scores,
            "improvements": improvements,
            "patient_readiness": readiness,
        }
        consultation.ai_key_points = ai_result.get("key_topics", [])

        db.commit()
        db.refresh(analysis)

        return {
            "status": "analyzed",
            "analysis_id": analysis.id,
            "analysis": {
                "summary": summary,
                "key_concerns": key_concerns,
                "recommended_procedures": procedures,
                "follow_up_actions": follow_ups,
                "sentiment_score": sentiment_score,
                "scores": scores,
                "what_went_well": went_well,
                "improvements": improvements,
                "buying_signals": buying,
                "objections_raised": objections,
                "patient_readiness": readiness,
                "recommended_treatment": ai_result.get("recommended_treatment", ""),
            },
        }

    except Exception as e:
        logger.error(f"Consultation AI analysis failed: {e}")
        # Still create a basic record so we don't lose the attempt
        if not existing:
            analysis = ConsultationAnalysis(
                consultation_id=consultation_id,
                summary="AI analysis encountered an error. Manual review recommended.",
                key_concerns=[],
                recommended_procedures=[],
                follow_up_actions=["Review consultation manually", "Retry AI analysis"],
                sentiment_score=0.5,
                ai_notes=f"Error: {str(e)}",
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)

        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(e)}"
        )


# ============================================================================
# 5. AI COACH Q&A
# ============================================================================

@router.post("/{consultation_id}/coach/ask")
async def ask_coach(
    consultation_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ask the AI Consultation Coach a question about a specific consultation.
    Required: question
    Uses transcript and analysis as context.
    """
    question = data.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    # Gather context
    transcript = ""
    transcription = db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).first()
    if transcription:
        transcript = transcription.content or ""
    elif consultation.transcription:
        transcript = consultation.transcription

    analysis = db.query(ConsultationAnalysis).filter(
        ConsultationAnalysis.consultation_id == consultation_id
    ).first()

    analysis_summary = ""
    if analysis:
        analysis_summary = f"Summary: {analysis.summary}. Concerns: {analysis.key_concerns}. Procedures: {analysis.recommended_procedures}."

    context = {
        "doctor_name": consultation.doctor_name,
        "patient_name": consultation.patient_name,
        "duration_minutes": consultation.duration_minutes,
        "status": consultation.status,
    }

    result = await ask_consultation_coach(
        question=question,
        transcript=transcript,
        analysis_summary=analysis_summary,
        context=context,
    )

    return {
        "consultation_id": consultation_id,
        "question": question,
        "answer": result.get("answer", "Unable to respond."),
    }


@router.post("/coach/general")
async def ask_general_coach(
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Ask the AI Consultation Coach a general question (not tied to a specific consultation).
    Good for: best practices, how to handle objections, consultation structure tips.
    """
    question = data.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    result = await ask_consultation_coach(
        question=question,
        transcript="",
        analysis_summary="",
        context={"type": "general_question"},
    )

    return {
        "question": question,
        "answer": result.get("answer", "Unable to respond."),
    }


# ============================================================================
# 6. PATIENT SUMMARY GENERATION
# ============================================================================

@router.post("/{consultation_id}/patient-summary")
async def generate_patient_summary(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a patient-friendly summary that can be sent after the consultation.
    Warm, clear, no jargon. Includes next steps and preparation notes.
    """
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    # Get transcript
    transcript = ""
    transcription = db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).first()
    if transcription:
        transcript = transcription.content or ""
    elif consultation.transcription:
        transcript = consultation.transcription

    if not transcript:
        raise HTTPException(status_code=400, detail="No transcription available to summarize")

    # Get procedures from analysis if available
    analysis = db.query(ConsultationAnalysis).filter(
        ConsultationAnalysis.consultation_id == consultation_id
    ).first()
    procedures = []
    if analysis and analysis.recommended_procedures:
        procedures = analysis.recommended_procedures

    result = await generate_consultation_summary_for_patient(
        transcript=transcript,
        procedures_discussed=procedures,
        doctor_name=consultation.doctor_name or "Your Doctor",
    )

    return {
        "consultation_id": consultation_id,
        "patient_name": consultation.patient_name,
        "patient_summary": result.get("patient_summary", ""),
        "procedures_explained": result.get("procedures_explained", []),
        "next_steps": result.get("next_steps", []),
        "pre_procedure_notes": result.get("pre_procedure_notes", ""),
    }


# ============================================================================
# 7. CONSULTATION SUMMARY VIEW
# ============================================================================

@router.get("/{consultation_id}/summary")
async def get_summary(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the complete AI summary of a consultation."""
    consultation = db.query(VideoConsultation).filter(
        VideoConsultation.id == consultation_id,
        VideoConsultation.clinic_id == current_user.clinic_id
    ).first()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    transcription = db.query(ConsultationTranscription).filter(
        ConsultationTranscription.consultation_id == consultation_id
    ).first()

    analysis = db.query(ConsultationAnalysis).filter(
        ConsultationAnalysis.consultation_id == consultation_id
    ).first()

    return {
        "consultation_id": consultation_id,
        "patient_name": consultation.patient_name,
        "doctor_name": consultation.doctor_name,
        "scheduled_at": str(consultation.scheduled_at) if consultation.scheduled_at else None,
        "duration_minutes": consultation.duration_minutes,
        "status": consultation.status,
        "has_transcription": transcription is not None or bool(consultation.transcription),
        "has_analysis": analysis is not None,
        "summary": {
            "text": analysis.summary if analysis else consultation.ai_summary or "No analysis available",
            "key_concerns": analysis.key_concerns if analysis else [],
            "recommended_procedures": analysis.recommended_procedures if analysis else [],
            "follow_up_actions": analysis.follow_up_actions if analysis else [],
            "sentiment_score": analysis.sentiment_score if analysis else None,
            "ai_notes": analysis.ai_notes if analysis else None,
        },
        "quick_insights": {
            "ai_summary": consultation.ai_summary,
            "ai_suggestions": consultation.ai_suggestions,
            "ai_key_points": consultation.ai_key_points,
        },
    }


# ============================================================================
# 8. BULK OPERATIONS
# ============================================================================

@router.post("/bulk-analyze")
async def bulk_analyze(
    data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze multiple consultations at once.
    data: { "consultation_ids": ["id1", "id2", ...] }
    """
    ids = data.get("consultation_ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="consultation_ids list is required")

    results = []
    for cid in ids:
        consultation = db.query(VideoConsultation).filter(
            VideoConsultation.id == cid,
            VideoConsultation.clinic_id == current_user.clinic_id
        ).first()

        if not consultation:
            results.append({"id": cid, "status": "not_found"})
            continue

        transcript = consultation.transcription
        if not transcript:
            trans_rec = db.query(ConsultationTranscription).filter(
                ConsultationTranscription.consultation_id == cid
            ).first()
            if trans_rec:
                transcript = trans_rec.content

        if not transcript:
            results.append({"id": cid, "status": "no_transcription"})
            continue

        try:
            ai_result = await ai_analyze(
                transcript=transcript,
                doctor_name=consultation.doctor_name or "Doctor",
                patient_name=consultation.patient_name or "Patient",
                duration_minutes=consultation.duration_minutes or 0,
            )

            scores = ai_result.get("scores", {})
            overall = scores.get("overall", 0)

            analysis = ConsultationAnalysis(
                consultation_id=cid,
                summary=ai_result.get("summary", ""),
                key_concerns=ai_result.get("patient_concerns", []),
                recommended_procedures=ai_result.get("procedures_discussed", []),
                follow_up_actions=ai_result.get("follow_up_actions", []),
                sentiment_score=overall / 100.0 if overall else 0.5,
                ai_notes=f"Bulk analyzed. Overall score: {overall}/100",
            )
            db.add(analysis)
            consultation.ai_summary = ai_result.get("summary", "")
            consultation.ai_key_points = ai_result.get("key_topics", [])

            results.append({"id": cid, "status": "analyzed", "overall_score": overall})

        except Exception as e:
            logger.error(f"Bulk analysis failed for {cid}: {e}")
            results.append({"id": cid, "status": "error", "error": str(e)})

    db.commit()

    analyzed = sum(1 for r in results if r["status"] == "analyzed")
    return {
        "total": len(ids),
        "analyzed": analyzed,
        "failed": len(ids) - analyzed,
        "results": results,
    }


# ============================================================================
# 9. PATIENT PROCEDURE HISTORY
# ============================================================================

@router.get("/patients/{patient_id}/history")
async def get_patient_procedure_history(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get procedure history for a patient."""
    history = db.query(PatientProcedureHistory).filter(
        PatientProcedureHistory.patient_id == patient_id,
        PatientProcedureHistory.clinic_id == current_user.clinic_id
    ).order_by(desc(PatientProcedureHistory.procedure_date)).all()

    results = []
    for h in history:
        results.append({
            "id": h.id,
            "procedure_name": h.procedure_name,
            "procedure_date": str(h.procedure_date) if h.procedure_date else None,
            "doctor_name": h.doctor_name,
            "notes": h.notes,
            "cost": h.cost,
            "outcome": h.outcome,
            "before_photos": h.before_photos,
            "after_photos": h.after_photos,
        })

    return {"patient_id": patient_id, "procedures": results, "total": len(results)}


@router.post("/patients/{patient_id}/history")
async def add_procedure_to_history(
    patient_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a procedure to patient history."""
    if "procedure_name" not in data or "procedure_date" not in data:
        raise HTTPException(status_code=400, detail="procedure_name and procedure_date required")

    record = PatientProcedureHistory(
        patient_id=patient_id,
        clinic_id=current_user.clinic_id,
        procedure_name=data["procedure_name"],
        procedure_date=data["procedure_date"],
        doctor_name=data.get("doctor_name"),
        notes=data.get("notes"),
        cost=data.get("cost"),
        outcome=data.get("outcome", "successful"),
        before_photos=data.get("before_photos", []),
        after_photos=data.get("after_photos", []),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"status": "added", "id": record.id}
