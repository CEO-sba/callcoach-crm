"""
CallCoach CRM - Live Coaching WebSocket

Real-time coaching during live calls. The agent's browser connects via WebSocket,
streams transcript chunks, and receives coaching tips in real-time.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Call, User, CoachingInsight
from app.services.ai_coach import get_live_coaching_tip
from jose import JWTError, jwt
from app.config import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)
router = APIRouter(tags=["live-coaching"])


class LiveCoachingSession:
    """Manages state for a live coaching session."""

    def __init__(self, call_id: str, user_id: str, clinic_id: str):
        self.call_id = call_id
        self.user_id = user_id
        self.clinic_id = clinic_id
        self.full_transcript = ""
        self.previous_tips = []
        self.chunk_count = 0
        self.started_at = datetime.utcnow()

    def add_chunk(self, text: str):
        self.full_transcript += " " + text
        self.chunk_count += 1

    def add_tip(self, tip: str):
        self.previous_tips.append(tip)


# Active sessions
active_sessions: dict[str, LiveCoachingSession] = {}


def authenticate_ws_token(token: str) -> dict:
    """Validate JWT token from WebSocket connection."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        clinic_id = payload.get("clinic_id")
        if not user_id:
            return None
        return {"user_id": user_id, "clinic_id": clinic_id}
    except JWTError:
        return None


@router.websocket("/ws/live-coaching/{call_id}")
async def live_coaching_ws(websocket: WebSocket, call_id: str):
    """
    WebSocket endpoint for real-time call coaching.

    Protocol:
    1. Client connects with ?token=JWT_TOKEN
    2. Client sends JSON: {"type": "transcript_chunk", "text": "...", "timestamp": 123.45}
    3. Server responds with coaching tips: {"type": "coaching_tip", "tips": [...]}
    4. Client sends {"type": "end_session"} when call ends
    5. Server sends final summary and closes

    Additional message types from client:
    - {"type": "request_tip"} - Force request a coaching tip based on current context
    - {"type": "mark_moment", "label": "objection|buying_signal|closing_opportunity"}
    """
    # Authenticate
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    auth = authenticate_ws_token(token)
    if not auth:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    await websocket.accept()

    # Create session
    session = LiveCoachingSession(
        call_id=call_id,
        user_id=auth["user_id"],
        clinic_id=auth["clinic_id"]
    )
    active_sessions[call_id] = session

    # Get clinic specialty for context
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == auth["user_id"]).first()
        clinic_specialty = "aesthetic"
        if user and user.clinic:
            clinic_specialty = user.clinic.specialty or "aesthetic"
    finally:
        db.close()

    # Send welcome message
    await websocket.send_json({
        "type": "system",
        "content": "CallCoach AI is now listening. I will provide real-time coaching tips as the call progresses.",
        "timestamp": datetime.utcnow().isoformat()
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "transcript_chunk":
                text = data.get("text", "").strip()
                if not text:
                    continue

                session.add_chunk(text)

                # Get coaching tip every 2-3 chunks or on demand
                if session.chunk_count % 2 == 0 or len(text) > 100:
                    coaching = await get_live_coaching_tip(
                        transcript_chunk=text,
                        full_context=session.full_transcript,
                        previous_tips=session.previous_tips,
                        clinic_specialty=clinic_specialty
                    )

                    tips = coaching.get("tips", [])
                    if tips:
                        for tip in tips:
                            session.add_tip(tip.get("content", ""))

                        await websocket.send_json({
                            "type": "coaching_tips",
                            "tips": tips,
                            "caller_mood": coaching.get("caller_mood", "neutral"),
                            "detected_intent": coaching.get("detected_intent", ""),
                            "timestamp": datetime.utcnow().isoformat()
                        })

            elif msg_type == "request_tip":
                # Force a coaching tip
                coaching = await get_live_coaching_tip(
                    transcript_chunk="[Agent requested a coaching tip]",
                    full_context=session.full_transcript,
                    previous_tips=session.previous_tips,
                    clinic_specialty=clinic_specialty
                )
                tips = coaching.get("tips", [])
                if tips:
                    for tip in tips:
                        session.add_tip(tip.get("content", ""))
                    await websocket.send_json({
                        "type": "coaching_tips",
                        "tips": tips,
                        "timestamp": datetime.utcnow().isoformat()
                    })

            elif msg_type == "mark_moment":
                label = data.get("label", "")
                await websocket.send_json({
                    "type": "system",
                    "content": f"Moment marked: {label}. Adjusting coaching focus.",
                    "timestamp": datetime.utcnow().isoformat()
                })

            elif msg_type == "end_session":
                # Save the full transcript to the call record
                db = SessionLocal()
                try:
                    call = db.query(Call).filter(Call.id == call_id).first()
                    if call:
                        call.transcription = session.full_transcript.strip()
                        call.transcription_status = "completed"
                        call.duration_seconds = int(
                            (datetime.utcnow() - session.started_at).total_seconds()
                        )
                        db.commit()
                finally:
                    db.close()

                await websocket.send_json({
                    "type": "session_ended",
                    "content": "Live coaching session ended. Full post-call analysis will be available shortly.",
                    "total_tips_given": len(session.previous_tips),
                    "call_duration": int((datetime.utcnow() - session.started_at).total_seconds()),
                    "timestamp": datetime.utcnow().isoformat()
                })
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call {call_id}")
    except Exception as e:
        logger.error(f"WebSocket error for call {call_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass
    finally:
        active_sessions.pop(call_id, None)


@router.get("/api/live-coaching/active-sessions")
def get_active_sessions():
    """List currently active live coaching sessions."""
    return [
        {
            "call_id": sid,
            "user_id": s.user_id,
            "started_at": s.started_at.isoformat(),
            "chunks_processed": s.chunk_count,
            "tips_given": len(s.previous_tips)
        }
        for sid, s in active_sessions.items()
    ]
