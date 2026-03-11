"""
CallCoach CRM - Calls Router
"""
import os
import shutil
import logging
import traceback
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db, SessionLocal
from app.models import Call, CallNote, CallScore, User, PipelineDeal, DealActivity
from app.schemas import CallCreate, CallUpdate, CallOut, CallNoteCreate, CallNoteOut
from app.auth import get_current_user
from app.config import UPLOAD_DIR, ALLOWED_AUDIO_EXTENSIONS
from app.services.transcription import transcribe_audio, get_transcription_status
from app.services.ai_coach import analyze_call
from app.services.storage import upload_recording, get_recording_url, get_local_path_for_transcription
from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _process_call_recording_sync(call_id: str, recording_path: str):
    """Background task to transcribe and analyze a call recording.

    NOTE: This is intentionally synchronous because FastAPI's BackgroundTasks
    runs async functions with asyncio.run() which can conflict with the
    existing event loop. We use a sync wrapper instead.

    recording_path can be a local file path OR an 'r2://...' URI.
    """
    import asyncio

    db = SessionLocal()
    local_tmp = None  # track temp file for cleanup
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            logger.error(f"Call {call_id} not found for processing")
            return

        # Step 1: Transcribe
        call.transcription_status = "processing"
        db.commit()
        logger.info(f"Starting transcription for call {call_id}, path: {recording_path}")

        # Resolve to local file (downloads from R2 if needed)
        file_path = get_local_path_for_transcription(recording_path)
        if file_path != recording_path:
            local_tmp = file_path  # mark for cleanup

        try:
            # Run the async transcribe function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(transcribe_audio(file_path))
            finally:
                loop.close()

            transcript_text = result.get("text", "")
            logger.info(f"Transcription result for call {call_id}: {len(transcript_text)} chars")

            # Check if we got a real transcription or just a placeholder
            is_placeholder = not transcript_text or transcript_text.startswith("[")
            if not is_placeholder:
                call.transcription = transcript_text
                call.transcription_segments = result.get("segments", [])
                duration = int(result.get("duration", 0))
                if duration > 0:
                    call.duration_seconds = duration
                call.transcription_status = "completed"
                db.commit()
                logger.info(f"Transcription completed for call {call_id}")
            else:
                # No real transcription available
                call.transcription = transcript_text
                call.transcription_status = "completed"
                db.commit()
                logger.warning(f"Transcription returned placeholder for call {call_id}")

        except Exception as e:
            logger.error(f"Transcription failed for call {call_id}: {e}\n{traceback.format_exc()}")
            call.transcription_status = "failed"
            call.transcription = f"Transcription failed: {str(e)}"
            db.commit()
            # Don't return - still try AI analysis if we have any text
            if not call.transcription or len(call.transcription) < 20:
                return

        # Step 2: AI Analysis (runs if we have real transcription text)
        if call.transcription and len(call.transcription) > 20 and not call.transcription.startswith("["):
            logger.info(f"Starting AI analysis for call {call_id}")
            try:
                agent = db.query(User).filter(User.id == call.agent_id).first()

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    analysis = loop.run_until_complete(analyze_call(
                        transcript=call.transcription,
                        call_type=call.call_type,
                        direction=call.direction,
                        duration=call.duration_seconds,
                        agent_name=agent.full_name if agent else "Agent"
                    ))
                finally:
                    loop.close()

                # Update call with AI analysis
                call.ai_summary = analysis.get("summary")
                call.ai_sentiment = analysis.get("sentiment")
                call.ai_intent = analysis.get("intent")
                call.ai_key_topics = analysis.get("key_topics", [])
                call.ai_action_items = analysis.get("action_items", [])
                call.ai_objections_detected = analysis.get("objections_detected", [])
                call.ai_buying_signals = analysis.get("buying_signals", [])

                scores = analysis.get("scores", {})
                call.overall_score = scores.get("overall_score", 0)

                # Create detailed score record
                score_record = CallScore(
                    call_id=call.id,
                    greeting_score=scores.get("greeting_score", 0),
                    discovery_score=scores.get("discovery_score", 0),
                    presentation_score=scores.get("presentation_score", 0),
                    objection_handling_score=scores.get("objection_handling_score", 0),
                    closing_score=scores.get("closing_score", 0),
                    rapport_score=scores.get("rapport_score", 0),
                    active_listening_score=scores.get("active_listening_score", 0),
                    urgency_creation_score=scores.get("urgency_creation_score", 0),
                    follow_up_setup_score=scores.get("follow_up_setup_score", 0),
                    overall_score=scores.get("overall_score", 0),
                    scoring_details=analysis.get("scoring_details"),
                    improvement_tips=analysis.get("improvement_tips"),
                    what_went_well=analysis.get("what_went_well"),
                    what_to_improve=analysis.get("what_to_improve")
                )
                db.add(score_record)

                # Auto-generate AI note
                if analysis.get("micro_win"):
                    ai_note = CallNote(
                        call_id=call.id,
                        author_id=call.agent_id,
                        content=f"AI Coaching Tip: {analysis['micro_win']}",
                        note_type="ai_generated"
                    )
                    db.add(ai_note)

                db.commit()
                logger.info(f"AI analysis completed for call {call_id}, score: {call.overall_score}")

                # Log the coaching interaction
                try:
                    log_activity(db, call.clinic_id, "coaching", "call_analyzed",
                                 {"call_id": call_id, "overall_score": call.overall_score,
                                  "sentiment": call.ai_sentiment, "intent": call.ai_intent})
                except Exception:
                    pass

                # Step 3: Auto-create pipeline deal if no deal linked and we have contact info
                try:
                    if not call.deal_id:
                        contact_name = call.caller_name
                        contact_phone = call.caller_phone
                        contact_email = call.caller_email

                        # Extract contact info from AI analysis if not already present
                        extracted = analysis.get("extracted_contact", {})
                        if not contact_name and extracted.get("name"):
                            contact_name = extracted["name"]
                            call.caller_name = contact_name
                        if not contact_phone and extracted.get("phone"):
                            contact_phone = extracted["phone"]
                            call.caller_phone = contact_phone
                        if not contact_email and extracted.get("email"):
                            contact_email = extracted["email"]
                            call.caller_email = contact_email

                        deal_title = f"{call.ai_intent or 'inquiry'} - {contact_name or contact_phone or 'Unknown'}"
                        treatment = ""
                        if call.ai_key_topics:
                            treatment = call.ai_key_topics[0] if call.ai_key_topics else ""

                        # Determine initial stage based on intent
                        intent_stage_map = {
                            "booking": "consultation_booked",
                            "follow_up": "contacted",
                            "inquiry": "new_inquiry",
                            "price_check": "new_inquiry",
                            "complaint": "contacted",
                            "cancellation": "contacted",
                            "referral": "new_inquiry",
                        }
                        stage = intent_stage_map.get(call.ai_intent, "new_inquiry")

                        # Check if a deal with this contact already exists
                        existing_deal = None
                        if contact_phone:
                            existing_deal = db.query(PipelineDeal).filter(
                                PipelineDeal.clinic_id == call.clinic_id,
                                PipelineDeal.contact_phone == contact_phone,
                                PipelineDeal.status == "open"
                            ).first()
                        if not existing_deal and contact_email:
                            existing_deal = db.query(PipelineDeal).filter(
                                PipelineDeal.clinic_id == call.clinic_id,
                                PipelineDeal.contact_email == contact_email,
                                PipelineDeal.status == "open"
                            ).first()

                        if existing_deal:
                            # Link call to existing deal
                            call.deal_id = existing_deal.id
                            existing_deal.total_calls = (existing_deal.total_calls or 0) + 1
                            existing_deal.total_touchpoints = (existing_deal.total_touchpoints or 0) + 1
                            activity = DealActivity(
                                deal_id=existing_deal.id,
                                user_id=call.agent_id,
                                activity_type="call",
                                description=f"Call recorded: {call.ai_summary or 'No summary'}",
                                extra_data={"call_id": call.id, "sentiment": call.ai_sentiment}
                            )
                            db.add(activity)
                            db.commit()
                            logger.info(f"Linked call {call_id} to existing deal {existing_deal.id}")
                        else:
                            # Create new deal
                            new_deal = PipelineDeal(
                                clinic_id=call.clinic_id,
                                contact_name=contact_name or "Unknown Caller",
                                contact_phone=contact_phone or "",
                                contact_email=contact_email or "",
                                title=deal_title.title(),
                                treatment_interest=treatment,
                                deal_value=0,
                                stage=stage,
                                priority="medium",
                                source="phone",
                                total_calls=1,
                                total_touchpoints=1,
                            )
                            db.add(new_deal)
                            db.flush()

                            call.deal_id = new_deal.id

                            activity = DealActivity(
                                deal_id=new_deal.id,
                                user_id=call.agent_id,
                                activity_type="call",
                                description=f"Deal auto-created from call: {call.ai_summary or 'No summary'}",
                                extra_data={"call_id": call.id, "sentiment": call.ai_sentiment}
                            )
                            db.add(activity)
                            db.commit()
                            logger.info(f"Auto-created deal {new_deal.id} for call {call_id}")

                except Exception as e:
                    logger.error(f"Auto-deal creation failed for call {call_id}: {e}\n{traceback.format_exc()}")

            except Exception as e:
                logger.error(f"AI analysis failed for call {call_id}: {e}\n{traceback.format_exc()}")
        else:
            logger.warning(f"Skipping AI analysis for call {call_id}: insufficient transcription")

    except Exception as e:
        logger.error(f"Background processing failed for call {call_id}: {e}\n{traceback.format_exc()}")
    finally:
        # Clean up temp file downloaded from R2
        if local_tmp:
            try:
                os.unlink(local_tmp)
            except OSError:
                pass
        db.close()


@router.get("/transcription-status")
def check_transcription_status():
    """Check if transcription service is available."""
    return get_transcription_status()


# ---- Audio file serving endpoint ----
@router.get("/{call_id}/audio")
def get_call_audio(
    call_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Serve the audio recording file for a call.

    Accepts auth via either:
    - Authorization header (Bearer token)
    - Query parameter: ?token=xxx (for <audio> tag which can't send headers)
    """
    from jose import JWTError, jwt as jose_jwt
    from app.config import SECRET_KEY, ALGORITHM

    # Try to get user from token query param (for audio tag)
    if token:
        try:
            payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            clinic_id = payload.get("clinic_id")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        raise HTTPException(status_code=401, detail="Token required")

    call = db.query(Call).filter(
        Call.id == call_id,
        Call.clinic_id == clinic_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.recording_path:
        raise HTTPException(status_code=404, detail="No recording for this call")

    # If stored in R2, redirect to presigned URL
    r2_url = get_recording_url(call.recording_path)
    if r2_url:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=r2_url)

    # Otherwise serve from local disk
    file_path = Path(call.recording_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Recording file not found on disk")

    ext = file_path.suffix.lower()
    media_types = {
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".mp4": "audio/mp4",
    }
    media_type = media_types.get(ext, "audio/webm")

    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=f"call-{call_id}{ext}"
    )


@router.post("/record", response_model=CallOut)
async def record_call(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    caller_name: str = Form(""),
    caller_phone: str = Form(""),
    call_type: str = Form("inbound"),
    direction: str = Form("inbound"),
    duration_seconds: int = Form(0),
    deal_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record a call: upload audio, create call entry, auto-transcribe and analyze."""
    ext = Path(file.filename).suffix.lower() if file.filename else ".webm"
    if ext not in ALLOWED_AUDIO_EXTENSIONS and ext not in {".webm", ".ogg"}:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")

    # Create call record
    call = Call(
        clinic_id=current_user.clinic_id,
        agent_id=current_user.id,
        caller_name=caller_name or None,
        caller_phone=caller_phone or None,
        call_type=call_type,
        direction=direction,
        duration_seconds=duration_seconds,
        call_date=datetime.utcnow(),
        status="completed"
    )
    if deal_id:
        call.deal_id = deal_id
    db.add(call)
    db.commit()
    db.refresh(call)

    # Save audio file (R2 cloud if configured, else local disk)
    content = await file.read()
    logger.info(f"Received audio file: {len(content)} bytes, ext: {ext}, filename: {file.filename}")

    media_types = {
        ".webm": "audio/webm", ".ogg": "audio/ogg", ".mp3": "audio/mpeg",
        ".wav": "audio/wav", ".m4a": "audio/mp4", ".flac": "audio/flac",
        ".aac": "audio/aac", ".mp4": "audio/mp4",
    }
    recording_path = upload_recording(
        file_content=content,
        clinic_id=current_user.clinic_id,
        call_id=call.id,
        extension=ext,
        content_type=media_types.get(ext, "audio/webm"),
    )

    call.recording_path = recording_path
    call.transcription_status = "pending"
    db.commit()

    # Process in background (transcribe + AI analyze) - use SYNC version
    background_tasks.add_task(_process_call_recording_sync, call.id, recording_path)

    log_activity(db, current_user.clinic_id, "coaching", "call_recorded",
                 {"call_id": call.id, "caller_name": caller_name, "call_type": call_type, "direction": direction},
                 current_user.email)

    db.refresh(call)
    return call


@router.post("", response_model=CallOut)
def create_call(
    call_data: CallCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new call log entry."""
    call = Call(
        clinic_id=current_user.clinic_id,
        agent_id=current_user.id,
        caller_name=call_data.caller_name,
        caller_phone=call_data.caller_phone,
        caller_email=call_data.caller_email,
        call_type=call_data.call_type,
        direction=call_data.direction,
        duration_seconds=call_data.duration_seconds,
        call_date=call_data.call_date or datetime.utcnow(),
        status=call_data.status,
        deal_id=call_data.deal_id
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@router.post("/{call_id}/upload", response_model=CallOut)
async def upload_recording(
    call_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a call recording and trigger transcription + AI analysis."""
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.clinic_id == current_user.clinic_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
        )

    # Save file (R2 cloud if configured, else local disk)
    content = await file.read()
    media_types = {
        ".webm": "audio/webm", ".ogg": "audio/ogg", ".mp3": "audio/mpeg",
        ".wav": "audio/wav", ".m4a": "audio/mp4", ".flac": "audio/flac",
        ".aac": "audio/aac", ".mp4": "audio/mp4",
    }
    recording_path = upload_recording(
        file_content=content,
        clinic_id=current_user.clinic_id,
        call_id=call_id,
        extension=ext,
        content_type=media_types.get(ext, "audio/webm"),
    )

    call.recording_path = recording_path
    call.transcription_status = "pending"
    db.commit()

    # Process in background - use SYNC version
    background_tasks.add_task(_process_call_recording_sync, call_id, recording_path)

    db.refresh(call)
    return call


@router.post("/{call_id}/transcription", response_model=CallOut)
async def submit_transcription(
    call_id: str,
    transcription: str = Form(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually submit a transcription for AI analysis."""
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.clinic_id == current_user.clinic_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    call.transcription = transcription
    call.transcription_status = "completed"
    db.commit()

    # Run AI analysis
    agent = db.query(User).filter(User.id == call.agent_id).first()
    analysis = await analyze_call(
        transcript=transcription,
        call_type=call.call_type,
        direction=call.direction,
        duration=call.duration_seconds,
        agent_name=agent.full_name if agent else "Agent"
    )

    call.ai_summary = analysis.get("summary")
    call.ai_sentiment = analysis.get("sentiment")
    call.ai_intent = analysis.get("intent")
    call.ai_key_topics = analysis.get("key_topics", [])
    call.ai_action_items = analysis.get("action_items", [])
    call.ai_objections_detected = analysis.get("objections_detected", [])
    call.ai_buying_signals = analysis.get("buying_signals", [])

    scores = analysis.get("scores", {})
    call.overall_score = scores.get("overall_score", 0)

    score_record = CallScore(
        call_id=call.id,
        greeting_score=scores.get("greeting_score", 0),
        discovery_score=scores.get("discovery_score", 0),
        presentation_score=scores.get("presentation_score", 0),
        objection_handling_score=scores.get("objection_handling_score", 0),
        closing_score=scores.get("closing_score", 0),
        rapport_score=scores.get("rapport_score", 0),
        active_listening_score=scores.get("active_listening_score", 0),
        urgency_creation_score=scores.get("urgency_creation_score", 0),
        follow_up_setup_score=scores.get("follow_up_setup_score", 0),
        overall_score=scores.get("overall_score", 0),
        scoring_details=analysis.get("scoring_details"),
        improvement_tips=analysis.get("improvement_tips"),
        what_went_well=analysis.get("what_went_well"),
        what_to_improve=analysis.get("what_to_improve")
    )
    db.add(score_record)
    db.commit()
    db.refresh(call)
    return call


@router.get("", response_model=list[CallOut])
def list_calls(
    skip: int = 0,
    limit: int = 50,
    call_type: Optional[str] = None,
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all calls for the clinic with optional filters."""
    query = db.query(Call).filter(Call.clinic_id == current_user.clinic_id)
    if call_type:
        query = query.filter(Call.call_type == call_type)
    if status:
        query = query.filter(Call.status == status)
    if agent_id:
        query = query.filter(Call.agent_id == agent_id)
    return query.order_by(Call.call_date.desc()).offset(skip).limit(limit).all()


@router.get("/{call_id}", response_model=CallOut)
def get_call(call_id: str, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    """Get a specific call with all details."""
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.clinic_id == current_user.clinic_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.post("/{call_id}/notes", response_model=CallNoteOut)
def add_note(call_id: str, note: CallNoteCreate, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    """Add a note to a call."""
    call = db.query(Call).filter(Call.id == call_id, Call.clinic_id == current_user.clinic_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    new_note = CallNote(
        call_id=call_id,
        author_id=current_user.id,
        content=note.content,
        note_type=note.note_type
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note


@router.post("/{call_id}/reanalyze", response_model=CallOut)
async def reanalyze_call(call_id: str, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """Re-run AI analysis on an existing call."""
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.clinic_id == current_user.clinic_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.transcription:
        raise HTTPException(status_code=400, detail="No transcription available")

    agent = db.query(User).filter(User.id == call.agent_id).first()
    analysis = await analyze_call(
        transcript=call.transcription,
        call_type=call.call_type,
        direction=call.direction,
        duration=call.duration_seconds,
        agent_name=agent.full_name if agent else "Agent"
    )

    call.ai_summary = analysis.get("summary")
    call.ai_sentiment = analysis.get("sentiment")
    call.ai_intent = analysis.get("intent")
    call.ai_key_topics = analysis.get("key_topics", [])
    call.ai_action_items = analysis.get("action_items", [])
    call.ai_objections_detected = analysis.get("objections_detected", [])
    call.ai_buying_signals = analysis.get("buying_signals", [])
    scores = analysis.get("scores", {})
    call.overall_score = scores.get("overall_score", 0)

    # Update contact info from AI extraction
    extracted = analysis.get("extracted_contact", {})
    if not call.caller_name and extracted.get("name"):
        call.caller_name = extracted["name"]
    if not call.caller_phone and extracted.get("phone"):
        call.caller_phone = extracted["phone"]
    if not call.caller_email and extracted.get("email"):
        call.caller_email = extracted["email"]

    # Create/update score record
    existing_scores = db.query(CallScore).filter(CallScore.call_id == call.id).all()
    for s in existing_scores:
        db.delete(s)

    score_record = CallScore(
        call_id=call.id,
        greeting_score=scores.get("greeting_score", 0),
        discovery_score=scores.get("discovery_score", 0),
        presentation_score=scores.get("presentation_score", 0),
        objection_handling_score=scores.get("objection_handling_score", 0),
        closing_score=scores.get("closing_score", 0),
        rapport_score=scores.get("rapport_score", 0),
        active_listening_score=scores.get("active_listening_score", 0),
        urgency_creation_score=scores.get("urgency_creation_score", 0),
        follow_up_setup_score=scores.get("follow_up_setup_score", 0),
        overall_score=scores.get("overall_score", 0),
        scoring_details=analysis.get("scoring_details"),
        improvement_tips=analysis.get("improvement_tips"),
        what_went_well=analysis.get("what_went_well"),
        what_to_improve=analysis.get("what_to_improve")
    )
    db.add(score_record)

    # Auto-create pipeline deal if no deal linked
    if not call.deal_id:
        contact_name = call.caller_name
        contact_phone = call.caller_phone
        contact_email = call.caller_email

        deal_title = f"{call.ai_intent or 'inquiry'} - {contact_name or contact_phone or 'Unknown'}"
        treatment = call.ai_key_topics[0] if call.ai_key_topics else ""

        intent_stage_map = {
            "booking": "consultation_booked",
            "follow_up": "contacted",
            "inquiry": "new_inquiry",
            "price_check": "new_inquiry",
            "complaint": "contacted",
            "cancellation": "contacted",
            "referral": "new_inquiry",
        }
        stage = intent_stage_map.get(call.ai_intent, "new_inquiry")

        existing_deal = None
        if contact_phone:
            existing_deal = db.query(PipelineDeal).filter(
                PipelineDeal.clinic_id == call.clinic_id,
                PipelineDeal.contact_phone == contact_phone,
                PipelineDeal.status == "open"
            ).first()
        if not existing_deal and contact_email:
            existing_deal = db.query(PipelineDeal).filter(
                PipelineDeal.clinic_id == call.clinic_id,
                PipelineDeal.contact_email == contact_email,
                PipelineDeal.status == "open"
            ).first()

        if existing_deal:
            call.deal_id = existing_deal.id
            existing_deal.total_calls = (existing_deal.total_calls or 0) + 1
            existing_deal.total_touchpoints = (existing_deal.total_touchpoints or 0) + 1
        else:
            new_deal = PipelineDeal(
                clinic_id=call.clinic_id,
                contact_name=contact_name or "Unknown Caller",
                contact_phone=contact_phone or "",
                contact_email=contact_email or "",
                title=deal_title.title(),
                treatment_interest=treatment,
                deal_value=0,
                stage=stage,
                priority="medium",
                source="phone",
                total_calls=1,
                total_touchpoints=1,
            )
            db.add(new_deal)
            db.flush()
            call.deal_id = new_deal.id

    db.commit()
    db.refresh(call)
    return call


class CoachQuestion(BaseModel):
    question: str


@router.post("/{call_id}/ask-coach")
async def ask_coach(
    call_id: str,
    body: CoachQuestion,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ask the AI coach a question about a specific call."""
    from app.services.ai_coach import ask_coach_about_call

    call = db.query(Call).filter(
        Call.id == call_id,
        Call.clinic_id == current_user.clinic_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    scores_detail = {}
    if call.scores:
        s = call.scores[0]
        scores_detail = {
            "greeting": s.greeting_score,
            "discovery": s.discovery_score,
            "presentation": s.presentation_score,
            "objection_handling": s.objection_handling_score,
            "closing": s.closing_score,
            "rapport": s.rapport_score,
            "active_listening": s.active_listening_score,
            "urgency_creation": s.urgency_creation_score,
            "follow_up_setup": s.follow_up_setup_score,
        }

    result = await ask_coach_about_call(
        question=body.question,
        transcript=call.transcription or "",
        ai_summary=call.ai_summary or "",
        ai_sentiment=call.ai_sentiment or "",
        overall_score=call.overall_score or 0,
        scores_detail=scores_detail,
        what_went_well=call.ai_key_topics or [],
        what_to_improve=call.ai_action_items or [],
        call_type=call.call_type or "inbound",
    )
    log_activity(db, current_user.clinic_id, "coaching", "ask_coach_question",
                 {"call_id": call_id, "question": body.question[:200]},
                 current_user.email)
    return result
