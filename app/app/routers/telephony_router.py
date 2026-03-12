"""
CallCoach CRM - Telephony Router
Telephony management: phone numbers, call routing, IVR configuration, call logs, and Twilio integration.
"""
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telephony", tags=["telephony"])


# ---------------------------------------------------------------------------
# Phone Numbers
# ---------------------------------------------------------------------------

@router.get("/numbers")
def list_numbers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all phone numbers configured for this clinic."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    numbers = settings.get("telephony_numbers", [])
    return {"numbers": numbers, "total": len(numbers)}


@router.post("/numbers")
def add_number(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a phone number to the telephony system."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    numbers = list(settings.get("telephony_numbers", []))
    number = {
        "id": f"num_{len(numbers) + 1}_{int(datetime.utcnow().timestamp())}",
        "phone_number": data.get("phone_number", ""),
        "label": data.get("label", "Main Line"),
        "type": data.get("type", "local"),  # local, toll_free, mobile
        "status": "active",
        "routing_type": data.get("routing_type", "ring_all"),  # ring_all, sequential, ivr
        "routing_targets": data.get("routing_targets", []),
        "ivr_enabled": data.get("ivr_enabled", False),
        "recording_enabled": data.get("recording_enabled", True),
        "whisper_message": data.get("whisper_message", ""),
        "business_hours": data.get("business_hours", {"start": "09:00", "end": "19:00", "timezone": "Asia/Kolkata"}),
        "after_hours_action": data.get("after_hours_action", "voicemail"),
        "created_at": datetime.utcnow().isoformat()
    }
    numbers.append(number)
    settings["telephony_numbers"] = numbers
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "telephony", "number_added",
                 {"phone_number": number["phone_number"], "label": number["label"]},
                 current_user.email)
    return {"message": "Number added", "number": number}


@router.put("/numbers/{number_id}")
def update_number(number_id: str, data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a phone number configuration."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    numbers = list(settings.get("telephony_numbers", []))
    for num in numbers:
        if num.get("id") == number_id:
            for key in ["label", "routing_type", "routing_targets", "ivr_enabled", "recording_enabled",
                        "whisper_message", "business_hours", "after_hours_action", "status"]:
                if key in data:
                    num[key] = data[key]
            num["updated_at"] = datetime.utcnow().isoformat()
            break
    else:
        raise HTTPException(status_code=404, detail="Number not found")
    settings["telephony_numbers"] = numbers
    clinic.settings = settings
    db.commit()
    return {"message": "Number updated"}


@router.delete("/numbers/{number_id}")
def delete_number(number_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove a phone number."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    numbers = list(settings.get("telephony_numbers", []))
    settings["telephony_numbers"] = [n for n in numbers if n.get("id") != number_id]
    clinic.settings = settings
    db.commit()
    return {"message": "Number removed"}


# ---------------------------------------------------------------------------
# Call Routing Rules
# ---------------------------------------------------------------------------

@router.get("/routing")
def list_routing_rules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List call routing rules."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    rules = settings.get("telephony_routing_rules", [])
    return {"rules": rules, "total": len(rules)}


@router.post("/routing")
def add_routing_rule(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a routing rule."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    rules = list(settings.get("telephony_routing_rules", []))
    rule = {
        "id": f"rule_{len(rules) + 1}_{int(datetime.utcnow().timestamp())}",
        "name": data.get("name", ""),
        "condition_type": data.get("condition_type", "all_calls"),  # all_calls, business_hours, after_hours, specific_number
        "condition_value": data.get("condition_value", ""),
        "action": data.get("action", "ring_all"),  # ring_all, sequential, voicemail, ivr, forward
        "targets": data.get("targets", []),
        "ring_timeout": data.get("ring_timeout", 30),
        "fallback_action": data.get("fallback_action", "voicemail"),
        "priority": data.get("priority", len(rules) + 1),
        "enabled": True,
        "created_at": datetime.utcnow().isoformat()
    }
    rules.append(rule)
    settings["telephony_routing_rules"] = rules
    clinic.settings = settings
    db.commit()
    return {"message": "Routing rule added", "rule": rule}


@router.delete("/routing/{rule_id}")
def delete_routing_rule(rule_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a routing rule."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    rules = list(settings.get("telephony_routing_rules", []))
    settings["telephony_routing_rules"] = [r for r in rules if r.get("id") != rule_id]
    clinic.settings = settings
    db.commit()
    return {"message": "Rule removed"}


# ---------------------------------------------------------------------------
# IVR Menu
# ---------------------------------------------------------------------------

@router.get("/ivr")
def get_ivr_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get IVR menu configuration."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    ivr = settings.get("telephony_ivr", {
        "enabled": False,
        "greeting_message": "Thank you for calling. Press 1 for appointments, 2 for enquiries, 3 to speak with a doctor.",
        "menu_options": [
            {"key": "1", "label": "Appointments", "action": "forward", "target": ""},
            {"key": "2", "label": "Enquiries", "action": "forward", "target": ""},
            {"key": "3", "label": "Doctor", "action": "forward", "target": ""},
        ],
        "timeout_action": "repeat",
        "max_retries": 3,
        "language": "en"
    })
    return ivr


@router.put("/ivr")
def update_ivr_config(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update IVR configuration."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    settings["telephony_ivr"] = data
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "telephony", "ivr_updated", {}, current_user.email)
    return {"message": "IVR configuration updated"}


# ---------------------------------------------------------------------------
# Call Logs (from Twilio or manual)
# ---------------------------------------------------------------------------

@router.get("/logs")
def get_call_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get telephony call logs (separate from coaching calls)."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    logs = settings.get("telephony_logs", [])
    # Sort by most recent
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"logs": logs[:200], "total": len(logs)}


@router.post("/logs")
def add_call_log(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manually add a call log entry."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    logs = list(settings.get("telephony_logs", []))
    log_entry = {
        "id": f"log_{len(logs) + 1}_{int(datetime.utcnow().timestamp())}",
        "caller_name": data.get("caller_name", "Unknown"),
        "caller_phone": data.get("caller_phone", ""),
        "direction": data.get("direction", "inbound"),  # inbound, outbound
        "status": data.get("status", "completed"),  # completed, missed, voicemail, busy, failed
        "duration_seconds": data.get("duration_seconds", 0),
        "answered_by": data.get("answered_by", ""),
        "number_called": data.get("number_called", ""),
        "recording_url": data.get("recording_url", ""),
        "notes": data.get("notes", ""),
        "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
        "created_at": datetime.utcnow().isoformat()
    }
    logs.append(log_entry)
    settings["telephony_logs"] = logs
    clinic.settings = settings
    db.commit()
    return {"message": "Call log added", "log": log_entry}


# ---------------------------------------------------------------------------
# Telephony Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def get_telephony_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get telephony dashboard statistics."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}

    numbers = settings.get("telephony_numbers", [])
    logs = settings.get("telephony_logs", [])

    # Calculate stats
    today = datetime.utcnow().strftime("%Y-%m-%d")
    today_logs = [l for l in logs if l.get("timestamp", "").startswith(today)]
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    week_logs = [l for l in logs if l.get("timestamp", "") >= week_ago]

    completed = [l for l in logs if l.get("status") == "completed"]
    missed = [l for l in logs if l.get("status") == "missed"]
    total_duration = sum(l.get("duration_seconds", 0) for l in completed)

    return {
        "total_numbers": len(numbers),
        "active_numbers": len([n for n in numbers if n.get("status") == "active"]),
        "total_calls_today": len(today_logs),
        "total_calls_week": len(week_logs),
        "total_calls_all": len(logs),
        "completed_calls": len(completed),
        "missed_calls": len(missed),
        "total_talk_time_seconds": total_duration,
        "avg_duration_seconds": round(total_duration / max(len(completed), 1)),
        "answer_rate": round(len(completed) / max(len(logs), 1) * 100, 1),
        "inbound_calls": len([l for l in logs if l.get("direction") == "inbound"]),
        "outbound_calls": len([l for l in logs if l.get("direction") == "outbound"]),
    }


# ---------------------------------------------------------------------------
# Twilio Integration Status
# ---------------------------------------------------------------------------

@router.get("/twilio-status")
def twilio_status(current_user: User = Depends(get_current_user)):
    """Check Twilio integration status."""
    from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
    connected = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)
    return {
        "connected": connected,
        "account_sid_set": bool(TWILIO_ACCOUNT_SID),
        "auth_token_set": bool(TWILIO_AUTH_TOKEN),
    }
