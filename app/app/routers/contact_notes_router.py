"""
CallCoach CRM - Contact Notes & Reminders Router
Notes, follow-up reminders, and contact activity tracking.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contact-notes", tags=["contact-notes"])


# ---------------------------------------------------------------------------
# Contact Notes
# ---------------------------------------------------------------------------

@router.get("/{contact_phone}")
def get_notes(contact_phone: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all notes for a contact."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    all_notes = settings.get("contact_notes", {})
    notes = all_notes.get(contact_phone, [])
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"notes": notes, "total": len(notes)}


@router.post("/{contact_phone}")
def add_note(contact_phone: str, data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a note to a contact."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    all_notes = dict(settings.get("contact_notes", {}))
    notes = list(all_notes.get(contact_phone, []))
    note = {
        "id": f"note_{len(notes) + 1}_{int(datetime.utcnow().timestamp())}",
        "content": data.get("content", ""),
        "type": data.get("type", "general"),  # general, call_summary, follow_up, treatment, complaint
        "author": current_user.email,
        "created_at": datetime.utcnow().isoformat()
    }
    notes.append(note)
    all_notes[contact_phone] = notes
    settings["contact_notes"] = all_notes
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "contacts", "note_added",
                 {"contact_phone": contact_phone, "type": note["type"]},
                 current_user.email)
    return {"message": "Note added", "note": note}


@router.delete("/{contact_phone}/{note_id}")
def delete_note(contact_phone: str, note_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a note."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    all_notes = dict(settings.get("contact_notes", {}))
    notes = list(all_notes.get(contact_phone, []))
    all_notes[contact_phone] = [n for n in notes if n.get("id") != note_id]
    settings["contact_notes"] = all_notes
    clinic.settings = settings
    db.commit()
    return {"message": "Note deleted"}


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

@router.get("/reminders/all")
def get_all_reminders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all reminders across all contacts."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    all_reminders = settings.get("contact_reminders", {})
    flat = []
    for phone, rems in all_reminders.items():
        for r in rems:
            flat.append({**r, "contact_phone": phone})
    flat.sort(key=lambda x: x.get("due_date", ""))
    return {"reminders": flat, "total": len(flat)}


@router.get("/reminders/{contact_phone}")
def get_reminders(contact_phone: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get reminders for a specific contact."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    all_reminders = settings.get("contact_reminders", {})
    reminders = all_reminders.get(contact_phone, [])
    reminders.sort(key=lambda x: x.get("due_date", ""))
    return {"reminders": reminders, "total": len(reminders)}


@router.post("/reminders/{contact_phone}")
def add_reminder(contact_phone: str, data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a follow-up reminder for a contact."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    all_reminders = dict(settings.get("contact_reminders", {}))
    reminders = list(all_reminders.get(contact_phone, []))
    reminder = {
        "id": f"rem_{len(reminders) + 1}_{int(datetime.utcnow().timestamp())}",
        "title": data.get("title", "Follow up"),
        "description": data.get("description", ""),
        "due_date": data.get("due_date", ""),
        "type": data.get("type", "follow_up"),  # follow_up, appointment, callback, treatment_review
        "status": "pending",  # pending, completed, dismissed
        "author": current_user.email,
        "created_at": datetime.utcnow().isoformat()
    }
    reminders.append(reminder)
    all_reminders[contact_phone] = reminders
    settings["contact_reminders"] = all_reminders
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "contacts", "reminder_added",
                 {"contact_phone": contact_phone, "title": reminder["title"], "due_date": reminder["due_date"]},
                 current_user.email)
    return {"message": "Reminder added", "reminder": reminder}


@router.put("/reminders/{contact_phone}/{reminder_id}")
def update_reminder(contact_phone: str, reminder_id: str, data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a reminder (mark complete, reschedule, etc.)."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    all_reminders = dict(settings.get("contact_reminders", {}))
    reminders = list(all_reminders.get(contact_phone, []))
    for rem in reminders:
        if rem.get("id") == reminder_id:
            for key in ["title", "description", "due_date", "type", "status"]:
                if key in data:
                    rem[key] = data[key]
            rem["updated_at"] = datetime.utcnow().isoformat()
            break
    else:
        raise HTTPException(status_code=404, detail="Reminder not found")
    all_reminders[contact_phone] = reminders
    settings["contact_reminders"] = all_reminders
    clinic.settings = settings
    db.commit()
    return {"message": "Reminder updated"}


@router.delete("/reminders/{contact_phone}/{reminder_id}")
def delete_reminder(contact_phone: str, reminder_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a reminder."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    all_reminders = dict(settings.get("contact_reminders", {}))
    reminders = list(all_reminders.get(contact_phone, []))
    all_reminders[contact_phone] = [r for r in reminders if r.get("id") != reminder_id]
    settings["contact_reminders"] = all_reminders
    clinic.settings = settings
    db.commit()
    return {"message": "Reminder deleted"}
