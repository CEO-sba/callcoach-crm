"""
CallCoach CRM - Notes, Reminders, and Call History Router
Provides CRUD endpoints for contact notes, reminders, and call history with pagination
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, date, timedelta
from typing import Optional, List
from pydantic import BaseModel

from app.models import User, Call
from app.models_expanded import ContactActivity, ContactReminder
from app.models_whatsapp import Lead
from app.models_telephony import TelephonyCall
from app.database import get_db
from app.auth import get_current_user


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class NoteCreate(BaseModel):
    """Request schema for creating a note"""
    lead_id: str
    content: str
    note_type: Optional[str] = "manual"

    class Config:
        json_schema_extra = {
            "example": {
                "lead_id": "lead-123",
                "content": "Patient interested in hair transplant, callback needed",
                "note_type": "manual"
            }
        }


class NoteResponse(BaseModel):
    """Response schema for a note"""
    id: str
    lead_id: str
    activity_type: str
    description: str
    created_at: datetime
    created_by_id: Optional[str] = None
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReminderCreate(BaseModel):
    """Request schema for creating a reminder"""
    lead_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: datetime
    priority: Optional[str] = "medium"
    reminder_type: Optional[str] = "follow_up"

    class Config:
        json_schema_extra = {
            "example": {
                "lead_id": "lead-123",
                "title": "Follow up with patient",
                "description": "Call patient to discuss treatment plan",
                "due_date": "2026-03-15T14:30:00",
                "priority": "high",
                "reminder_type": "callback"
            }
        }


class ReminderUpdate(BaseModel):
    """Request schema for updating a reminder"""
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    reminder_type: Optional[str] = None
    is_completed: Optional[bool] = None


class ReminderResponse(BaseModel):
    """Response schema for a reminder"""
    id: str
    lead_id: Optional[str]
    user_id: str
    title: str
    description: Optional[str]
    due_date: datetime
    is_completed: bool
    completed_at: Optional[datetime]
    priority: str
    reminder_type: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CallHistoryResponse(BaseModel):
    """Response schema for call history"""
    id: str
    call_id: str
    clinic_id: str
    agent_id: str
    agent_name: Optional[str] = None
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    call_type: str
    direction: str
    duration_seconds: int
    call_date: datetime
    status: str
    recording_path: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_sentiment: Optional[str] = None
    overall_score: Optional[float] = None
    # Telephony info
    provider: Optional[str] = None
    provider_call_sid: Optional[str] = None
    recording_url: Optional[str] = None
    to_number: Optional[str] = None
    from_number: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedCallHistoryResponse(BaseModel):
    """Response schema for paginated call history"""
    items: List[CallHistoryResponse]
    total: int
    page: int
    limit: int
    pages: int


# ============================================================================
# ROUTER SETUP
# ============================================================================

router = APIRouter(prefix="/api", tags=["notes-reminders-calls"])


# ============================================================================
# NOTES ENDPOINTS
# ============================================================================

@router.post("/notes", response_model=NoteResponse, status_code=201)
def create_note(
    body: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Create a note for a lead.

    Notes are stored as ContactActivity records with activity_type='note'.
    """
    # Verify lead exists and belongs to same clinic
    lead = db.query(Lead).filter(
        Lead.id == body.lead_id,
        Lead.clinic_id == user.clinic_id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Create contact activity note
    note = ContactActivity(
        clinic_id=user.clinic_id,
        lead_id=body.lead_id,
        activity_type="note",
        description=body.content,
        source_platform="internal",
        extra_data={
            "note_type": body.note_type,
            "created_by_id": user.id,
            "created_by_name": user.full_name,
            "created_by_email": user.email
        }
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return NoteResponse(
        id=note.id,
        lead_id=note.lead_id,
        activity_type=note.activity_type,
        description=note.description,
        created_at=note.created_at,
        created_by_id=user.id,
        created_by_name=user.full_name
    )


@router.get("/notes/{lead_id}", response_model=List[NoteResponse])
def get_notes(
    lead_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get all notes for a lead, sorted by created_at descending.
    """
    # Verify lead exists and belongs to same clinic
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.clinic_id == user.clinic_id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get all notes (ContactActivity with activity_type='note') for this lead
    notes = db.query(ContactActivity).filter(
        ContactActivity.lead_id == lead_id,
        ContactActivity.clinic_id == user.clinic_id,
        ContactActivity.activity_type == "note"
    ).order_by(desc(ContactActivity.created_at)).all()

    result = []
    for note in notes:
        created_by_id = None
        created_by_name = None

        if note.extra_data:
            created_by_id = note.extra_data.get("created_by_id")
            created_by_name = note.extra_data.get("created_by_name")

        result.append(NoteResponse(
            id=note.id,
            lead_id=note.lead_id,
            activity_type=note.activity_type,
            description=note.description,
            created_at=note.created_at,
            created_by_id=created_by_id,
            created_by_name=created_by_name
        ))

    return result


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Delete a note by ID.
    Only the creator or an admin can delete a note.
    """
    note = db.query(ContactActivity).filter(
        ContactActivity.id == note_id,
        ContactActivity.clinic_id == user.clinic_id,
        ContactActivity.activity_type == "note"
    ).first()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Check if user is creator or admin
    if user.role != "admin":
        created_by_id = note.extra_data.get("created_by_id") if note.extra_data else None
        if created_by_id != user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

    db.delete(note)
    db.commit()


# ============================================================================
# REMINDERS ENDPOINTS
# ============================================================================

@router.post("/reminders", response_model=ReminderResponse, status_code=201)
def create_reminder(
    body: ReminderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Create a reminder for a user (optionally linked to a lead).
    """
    # If lead_id provided, verify it exists and belongs to same clinic
    if body.lead_id:
        lead = db.query(Lead).filter(
            Lead.id == body.lead_id,
            Lead.clinic_id == user.clinic_id
        ).first()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

    reminder = ContactReminder(
        clinic_id=user.clinic_id,
        lead_id=body.lead_id,
        user_id=user.id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        priority=body.priority or "medium",
        reminder_type=body.reminder_type or "follow_up",
        is_completed=False
    )

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return ReminderResponse.from_orm(reminder)


@router.get("/reminders", response_model=List[ReminderResponse])
def get_reminders(
    status: Optional[str] = Query(None, description="Filter by status: pending|completed"),
    date: Optional[str] = Query(None, description="Filter by date: today|week|month"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get reminders for current user with optional filters.

    - Agents see only their own reminders
    - Admins can optionally see all clinic reminders (add ?clinic=true to query)
    - status: pending (not completed) or completed
    - date: today, week, month
    """
    query = db.query(ContactReminder).filter(
        ContactReminder.clinic_id == user.clinic_id
    )

    # Filter by user (agents only see their own reminders)
    if user.role == "agent":
        query = query.filter(ContactReminder.user_id == user.id)
    # Admins see all clinic reminders by default

    # Apply status filter
    if status == "pending":
        query = query.filter(ContactReminder.is_completed == False)
    elif status == "completed":
        query = query.filter(ContactReminder.is_completed == True)

    # Apply date filter
    if date == "today":
        today = datetime.utcnow().date()
        query = query.filter(
            and_(
                ContactReminder.due_date >= datetime.combine(today, datetime.min.time()),
                ContactReminder.due_date < datetime.combine(today + timedelta(days=1), datetime.min.time())
            )
        )
    elif date == "week":
        today = datetime.utcnow().date()
        week_end = today + timedelta(days=7)
        query = query.filter(
            and_(
                ContactReminder.due_date >= datetime.combine(today, datetime.min.time()),
                ContactReminder.due_date < datetime.combine(week_end, datetime.min.time())
            )
        )
    elif date == "month":
        today = datetime.utcnow().date()
        month_end = today + timedelta(days=30)
        query = query.filter(
            and_(
                ContactReminder.due_date >= datetime.combine(today, datetime.min.time()),
                ContactReminder.due_date < datetime.combine(month_end, datetime.min.time())
            )
        )

    # Sort by due date ascending (earliest first)
    reminders = query.order_by(ContactReminder.due_date).all()

    return [ReminderResponse.from_orm(r) for r in reminders]


@router.get("/reminders/today", response_model=List[ReminderResponse])
def get_today_reminders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get today's reminders for current user.
    Used for dashboard widget showing pending tasks.
    """
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

    query = db.query(ContactReminder).filter(
        ContactReminder.clinic_id == user.clinic_id,
        ContactReminder.is_completed == False,
        and_(
            ContactReminder.due_date >= today_start,
            ContactReminder.due_date < today_end
        )
    )

    # Agents see only their own reminders
    if user.role == "agent":
        query = query.filter(ContactReminder.user_id == user.id)

    reminders = query.order_by(ContactReminder.due_date).all()

    return [ReminderResponse.from_orm(r) for r in reminders]


@router.get("/reminders/{lead_id}", response_model=List[ReminderResponse])
def get_lead_reminders(
    lead_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get all reminders for a specific lead.
    """
    # Verify lead exists and belongs to same clinic
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.clinic_id == user.clinic_id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    reminders = db.query(ContactReminder).filter(
        ContactReminder.lead_id == lead_id,
        ContactReminder.clinic_id == user.clinic_id
    ).order_by(ContactReminder.due_date).all()

    return [ReminderResponse.from_orm(r) for r in reminders]


@router.put("/reminders/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: str,
    body: ReminderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Update a reminder (mark as complete, change due date, etc.).
    """
    reminder = db.query(ContactReminder).filter(
        ContactReminder.id == reminder_id,
        ContactReminder.clinic_id == user.clinic_id
    ).first()

    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    # Check permissions (owner or admin can update)
    if user.role != "admin" and reminder.user_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Update fields
    if body.title is not None:
        reminder.title = body.title
    if body.description is not None:
        reminder.description = body.description
    if body.due_date is not None:
        reminder.due_date = body.due_date
    if body.priority is not None:
        reminder.priority = body.priority
    if body.reminder_type is not None:
        reminder.reminder_type = body.reminder_type

    # Handle completion
    if body.is_completed is not None:
        reminder.is_completed = body.is_completed
        if body.is_completed:
            reminder.completed_at = datetime.utcnow()
        else:
            reminder.completed_at = None

    reminder.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reminder)

    return ReminderResponse.from_orm(reminder)


@router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Delete a reminder.
    Only the owner or an admin can delete a reminder.
    """
    reminder = db.query(ContactReminder).filter(
        ContactReminder.id == reminder_id,
        ContactReminder.clinic_id == user.clinic_id
    ).first()

    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    # Check permissions
    if user.role != "admin" and reminder.user_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    db.delete(reminder)
    db.commit()


# ============================================================================
# CALL HISTORY ENDPOINTS
# ============================================================================

@router.get("/call-history", response_model=PaginatedCallHistoryResponse)
def get_call_history(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by caller name or phone"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get call history for the clinic with optional filters and pagination.

    Supports:
    - Pagination: page, limit
    - Search by caller name or phone
    - Filter by status (completed, missed, voicemail, in_progress)
    - Filter by date range (YYYY-MM-DD format)

    Agents see only their own calls; admins see all clinic calls.
    """
    # Base query
    query = db.query(Call).filter(Call.clinic_id == user.clinic_id)

    # Filter by agent (agents see only their own calls)
    if user.role == "agent":
        query = query.filter(Call.agent_id == user.id)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Call.caller_name.ilike(search_term),
                Call.caller_phone.ilike(search_term)
            )
        )

    # Apply status filter
    if status:
        query = query.filter(Call.status == status)

    # Apply date range filter
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Call.call_date >= from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format, use YYYY-MM-DD")

    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            # Add 1 day to include all records on date_to
            to_date = to_date + timedelta(days=1)
            query = query.filter(Call.call_date < to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format, use YYYY-MM-DD")

    # Count total matching records
    total = query.count()

    # Apply pagination
    offset = (page - 1) * limit
    calls = query.order_by(desc(Call.call_date)).offset(offset).limit(limit).all()

    # Build response with telephony info
    items = []
    for call in calls:
        # Get agent name
        agent = db.query(User).filter(User.id == call.agent_id).first()
        agent_name = agent.full_name if agent else None

        # Get telephony info if available
        telephony = db.query(TelephonyCall).filter(
            TelephonyCall.call_id == call.id
        ).first()

        item = CallHistoryResponse(
            id=call.id,
            call_id=call.id,
            clinic_id=call.clinic_id,
            agent_id=call.agent_id,
            agent_name=agent_name,
            caller_name=call.caller_name,
            caller_phone=call.caller_phone,
            call_type=call.call_type,
            direction=call.direction,
            duration_seconds=call.duration_seconds,
            call_date=call.call_date,
            status=call.status,
            recording_path=call.recording_path,
            ai_summary=call.ai_summary,
            ai_sentiment=call.ai_sentiment,
            overall_score=call.overall_score,
            provider=telephony.provider if telephony else None,
            provider_call_sid=telephony.provider_call_sid if telephony else None,
            recording_url=telephony.recording_url if telephony else None,
            to_number=telephony.to_number if telephony else None,
            from_number=telephony.from_number if telephony else None
        )
        items.append(item)

    # Calculate pagination info
    pages = (total + limit - 1) // limit  # Ceiling division

    return PaginatedCallHistoryResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages
    )
