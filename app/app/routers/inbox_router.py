"""
CallCoach CRM - Unified Inbox Router (v2.1 - Full Integration)
Manages conversations across WhatsApp, Email, SMS, Instagram, Facebook.
Includes contact activities, reminders, tasks, and AI-assisted replies.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity as log_platform_activity
from app.models_expanded import (
    UnifiedConversation,
    UnifiedMessage,
    ContactActivity,
    ContactReminder,
    ContactTask,
    ConversationPlatform,
)
# Aliases for backward compat
Conversation = UnifiedConversation
Message = UnifiedMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inbox", tags=["inbox"])


# ============================================================================
# 1. INBOX DASHBOARD & STATS
# ============================================================================

@router.get("/stats")
async def inbox_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Inbox analytics: unread counts, platform breakdown, response metrics."""
    clinic_id = current_user.clinic_id
    base = db.query(Conversation).filter(Conversation.clinic_id == clinic_id)

    total = base.count()
    active = base.filter(Conversation.status == "active").count()
    archived = base.filter(Conversation.status == "archived").count()

    # Unread by platform
    platforms = ["whatsapp", "email", "sms", "instagram", "facebook"]
    by_platform = {}
    total_unread = 0
    for p in platforms:
        unread = base.filter(
            Conversation.platform == p,
            Conversation.unread_count > 0
        ).count()
        total_count = base.filter(Conversation.platform == p).count()
        by_platform[p] = {"unread": unread, "total": total_count}
        total_unread += unread

    # Unassigned conversations
    unassigned = base.filter(
        Conversation.assigned_agent_id == None,
        Conversation.status == "active"
    ).count()

    # Pending tasks
    pending_tasks = db.query(func.count(ContactTask.id)).filter(
        ContactTask.clinic_id == clinic_id,
        ContactTask.status.in_(["pending", "in_progress"])
    ).scalar() or 0

    # Upcoming reminders (next 24 hours)
    from datetime import timedelta
    now = datetime.utcnow()
    upcoming_reminders = db.query(func.count(ContactReminder.id)).filter(
        ContactReminder.clinic_id == clinic_id,
        ContactReminder.is_completed == False,
        ContactReminder.due_date <= now + timedelta(hours=24)
    ).scalar() or 0

    return {
        "total_conversations": total,
        "active_conversations": active,
        "archived_conversations": archived,
        "total_unread": total_unread,
        "unassigned": unassigned,
        "pending_tasks": pending_tasks,
        "upcoming_reminders": upcoming_reminders,
        "by_platform": by_platform,
    }


# ============================================================================
# 2. CONVERSATIONS
# ============================================================================

@router.get("/conversations")
async def list_conversations(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    assigned_to: Optional[str] = None,
    has_unread: Optional[bool] = None,
    tag: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List conversations with filters."""
    query = db.query(Conversation).filter(
        Conversation.clinic_id == current_user.clinic_id
    )

    if platform:
        query = query.filter(Conversation.platform == platform)
    if status:
        query = query.filter(Conversation.status == status)
    else:
        query = query.filter(Conversation.status != "archived")
    if search:
        query = query.filter(
            or_(
                Conversation.contact_name.ilike(f"%{search}%"),
                Conversation.contact_phone.ilike(f"%{search}%"),
                Conversation.contact_email.ilike(f"%{search}%"),
                Conversation.last_message_preview.ilike(f"%{search}%"),
            )
        )
    if assigned_to:
        query = query.filter(Conversation.assigned_agent_id == assigned_to)
    if has_unread:
        query = query.filter(Conversation.unread_count > 0)

    total = query.count()
    conversations = query.order_by(
        desc(Conversation.last_message_at)
    ).offset(skip).limit(limit).all()

    results = []
    for c in conversations:
        results.append({
            "id": c.id,
            "lead_id": c.lead_id,
            "contact_name": c.contact_name,
            "contact_phone": c.contact_phone,
            "contact_email": c.contact_email,
            "platform": c.platform,
            "status": c.status,
            "unread_count": c.unread_count or 0,
            "last_message_at": str(c.last_message_at) if c.last_message_at else None,
            "last_message_preview": c.last_message_preview,
            "assigned_agent_id": c.assigned_agent_id,
            "tags": c.tags or [],
            "created_at": str(c.created_at) if c.created_at else None,
        })

    return {"conversations": results, "total": total}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation with all messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()

    msg_list = []
    for m in messages:
        msg_list.append({
            "id": m.id,
            "direction": m.direction,
            "content": m.content,
            "media_url": m.media_url,
            "media_type": m.media_type,
            "sender_type": m.sender_type,
            "sender_id": m.sender_id,
            "platform_message_id": m.platform_message_id,
            "status": m.status,
            "created_at": str(m.created_at) if m.created_at else None,
        })

    # Mark as read
    conversation.unread_count = 0
    db.commit()

    return {
        "conversation": {
            "id": conversation.id,
            "lead_id": conversation.lead_id,
            "contact_name": conversation.contact_name,
            "contact_phone": conversation.contact_phone,
            "contact_email": conversation.contact_email,
            "platform": conversation.platform,
            "status": conversation.status,
            "assigned_agent_id": conversation.assigned_agent_id,
            "tags": conversation.tags or [],
        },
        "messages": msg_list,
        "message_count": len(msg_list),
    }


@router.post("/conversations")
async def create_conversation(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new conversation.
    Required: contact_name, platform
    Optional: lead_id, contact_phone, contact_email, initial_message
    """
    if "contact_name" not in data or "platform" not in data:
        raise HTTPException(status_code=400, detail="contact_name and platform required")

    conversation = Conversation(
        clinic_id=current_user.clinic_id,
        lead_id=data.get("lead_id"),
        contact_name=data["contact_name"],
        contact_phone=data.get("contact_phone"),
        contact_email=data.get("contact_email"),
        platform=data["platform"],
        status="active",
        assigned_agent_id=current_user.id,
        last_message_at=datetime.utcnow(),
    )
    db.add(conversation)
    db.flush()

    # If initial message provided, create it
    if data.get("initial_message"):
        msg = Message(
            conversation_id=conversation.id,
            direction="outbound",
            content=data["initial_message"],
            sender_type="agent",
            sender_id=current_user.id,
            status="sent",
        )
        db.add(msg)
        conversation.last_message_preview = data["initial_message"][:300]

    db.commit()
    db.refresh(conversation)
    log_platform_activity(db, current_user.clinic_id, "lead", "inbox_conversation_created",
                          {"contact": data["contact_name"], "platform": data["platform"]},
                          current_user.email)

    return {"status": "created", "conversation_id": conversation.id}


# ============================================================================
# 3. MESSAGES
# ============================================================================

@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message in a conversation.
    Required: content
    Optional: media_url, media_type
    Saves message and updates conversation preview.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    content = data.get("content") or data.get("message", "")
    if not content and not data.get("media_url"):
        raise HTTPException(status_code=400, detail="content or media_url required")

    message = Message(
        conversation_id=conversation_id,
        direction="outbound",
        content=content,
        media_url=data.get("media_url"),
        media_type=data.get("media_type"),
        sender_type="agent",
        sender_id=current_user.id,
        status="sent",
    )
    db.add(message)

    # Update conversation
    conversation.last_message_at = datetime.utcnow()
    conversation.last_message_preview = (content or "[Media]")[:300]
    if conversation.status == "archived":
        conversation.status = "active"

    # Log activity if lead is linked
    if conversation.lead_id:
        activity = ContactActivity(
            clinic_id=current_user.clinic_id,
            lead_id=conversation.lead_id,
            activity_type="message",
            description=f"Outbound {conversation.platform} message sent",
            source_platform=conversation.platform,
            extra_data={"message_preview": content[:100] if content else "[Media]"},
        )
        db.add(activity)

    db.commit()
    db.refresh(message)
    log_platform_activity(db, current_user.clinic_id, "lead", "inbox_message_sent",
                          {"conversation_id": conversation_id, "platform": conversation.platform,
                           "content_preview": (content or "[Media]")[:80]}, current_user.email)

    return {
        "status": "sent",
        "message_id": message.id,
        "platform": conversation.platform,
    }


@router.post("/conversations/{conversation_id}/ai-reply")
async def generate_ai_reply(
    conversation_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an AI-suggested reply based on conversation context.
    Optional: tone (professional, friendly, warm), language (en, hi, hinglish)
    Does NOT send the reply. Returns suggestion for agent to review.
    """
    from app.services.consultation_ai_coach import ask_consultation_coach

    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get last 20 messages for context
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(desc(Message.created_at)).limit(20).all()

    messages.reverse()
    conversation_text = ""
    for m in messages:
        role = "Patient" if m.direction == "inbound" else "Agent"
        conversation_text += f"{role}: {m.content or '[Media]'}\n"

    tone = data.get("tone", "professional")
    language = data.get("language", "english")

    question = f"""Based on this {conversation.platform} conversation, suggest a reply.
Tone: {tone}. Language: {language}.
The patient's name is {conversation.contact_name or 'the patient'}.
What would be the best response to move this conversation forward and build trust?"""

    result = await ask_consultation_coach(
        question=question,
        transcript=conversation_text,
        analysis_summary="",
        context={"platform": conversation.platform, "tone": tone, "language": language},
    )

    log_platform_activity(db, current_user.clinic_id, "ai_employee", "inbox_ai_reply_generated",
                          {"conversation_id": conversation_id, "platform": conversation.platform,
                           "tone": tone, "language": language}, current_user.email)
    return {
        "conversation_id": conversation_id,
        "suggested_reply": result.get("answer", ""),
        "tone": tone,
        "language": language,
    }


# ============================================================================
# 4. CONVERSATION MANAGEMENT
# ============================================================================

@router.put("/conversations/{conversation_id}/assign")
async def assign_conversation(
    conversation_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign conversation to an agent."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    agent_id = data.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id required")

    agent = db.query(User).filter(
        User.id == agent_id, User.clinic_id == current_user.clinic_id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    conversation.assigned_agent_id = agent_id
    db.commit()
    log_platform_activity(db, current_user.clinic_id, "lead", "inbox_conversation_assigned",
                          {"conversation_id": conversation_id, "agent_id": agent_id,
                           "agent_name": agent.full_name}, current_user.email)

    return {"status": "assigned", "conversation_id": conversation.id, "agent_id": agent_id}


@router.put("/conversations/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation status (active, archived, closed, spam)."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_status = data.get("status")
    valid = ["active", "archived", "closed", "spam"]
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {valid}")

    conversation.status = new_status
    if new_status == "archived":
        conversation.is_archived = True
    elif new_status == "active":
        conversation.is_archived = False
    db.commit()

    return {"status": "updated", "new_status": new_status}


@router.put("/conversations/{conversation_id}/tags")
async def update_conversation_tags(
    conversation_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation tags. data: { "tags": ["hot_lead", "follow_up"] }"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.tags = data.get("tags", [])
    db.commit()

    return {"status": "updated", "tags": conversation.tags}


@router.put("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archive a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.status = "archived"
    conversation.is_archived = True
    db.commit()

    return {"status": "archived", "conversation_id": conversation.id}


# ============================================================================
# 5. CONTACT ACTIVITY TIMELINE
# ============================================================================

@router.get("/activities/{lead_id}")
async def get_contact_activities(
    lead_id: str,
    activity_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get activity timeline for a contact/lead."""
    query = db.query(ContactActivity).filter(
        ContactActivity.clinic_id == current_user.clinic_id,
        ContactActivity.lead_id == lead_id
    )

    if activity_type:
        query = query.filter(ContactActivity.activity_type == activity_type)

    total = query.count()
    activities = query.order_by(
        desc(ContactActivity.created_at)
    ).offset(skip).limit(limit).all()

    results = []
    for a in activities:
        results.append({
            "id": a.id,
            "activity_type": a.activity_type,
            "description": a.description,
            "source_platform": a.source_platform,
            "source_url": a.source_url,
            "extra_data": a.extra_data,
            "created_at": str(a.created_at) if a.created_at else None,
        })

    return {"activities": results, "total": total}


@router.post("/activities")
async def log_activity(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually log a contact activity."""
    if "lead_id" not in data or "activity_type" not in data:
        raise HTTPException(status_code=400, detail="lead_id and activity_type required")

    activity = ContactActivity(
        clinic_id=current_user.clinic_id,
        lead_id=data["lead_id"],
        activity_type=data["activity_type"],
        description=data.get("description", ""),
        source_platform=data.get("source_platform"),
        source_url=data.get("source_url"),
        extra_data=data.get("extra_data", {}),
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    return {"status": "logged", "activity_id": activity.id}


# ============================================================================
# 6. REMINDERS
# ============================================================================

@router.get("/reminders")
async def list_reminders(
    lead_id: Optional[str] = None,
    is_completed: Optional[bool] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List reminders for the current user or clinic."""
    query = db.query(ContactReminder).filter(
        ContactReminder.clinic_id == current_user.clinic_id
    )

    if lead_id:
        query = query.filter(ContactReminder.lead_id == lead_id)
    if is_completed is not None:
        query = query.filter(ContactReminder.is_completed == is_completed)
    if priority:
        query = query.filter(ContactReminder.priority == priority)

    total = query.count()
    reminders = query.order_by(ContactReminder.due_date.asc()).offset(skip).limit(limit).all()

    results = []
    for r in reminders:
        results.append({
            "id": r.id,
            "lead_id": r.lead_id,
            "user_id": r.user_id,
            "title": r.title,
            "description": r.description,
            "due_date": str(r.due_date) if r.due_date else None,
            "is_completed": r.is_completed,
            "priority": r.priority,
            "reminder_type": r.reminder_type,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return {"reminders": results, "total": total}


@router.post("/reminders")
async def create_reminder(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new reminder."""
    required = ["lead_id", "title", "due_date"]
    for f in required:
        if f not in data:
            raise HTTPException(status_code=400, detail=f"Missing: {f}")

    reminder = ContactReminder(
        clinic_id=current_user.clinic_id,
        lead_id=data["lead_id"],
        user_id=data.get("user_id", current_user.id),
        title=data["title"],
        description=data.get("description"),
        due_date=data["due_date"],
        priority=data.get("priority", "medium"),
        reminder_type=data.get("reminder_type", "follow_up"),
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    log_platform_activity(db, current_user.clinic_id, "lead", "reminder_created",
                          {"lead_id": data["lead_id"], "title": data["title"], "priority": data.get("priority", "medium")},
                          current_user.email)

    return {"status": "created", "reminder_id": reminder.id}


@router.put("/reminders/{reminder_id}/complete")
async def complete_reminder(
    reminder_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a reminder as completed."""
    reminder = db.query(ContactReminder).filter(
        ContactReminder.id == reminder_id,
        ContactReminder.clinic_id == current_user.clinic_id
    ).first()

    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.is_completed = True
    reminder.completed_at = datetime.utcnow()
    db.commit()

    return {"status": "completed", "reminder_id": reminder.id}


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a reminder."""
    reminder = db.query(ContactReminder).filter(
        ContactReminder.id == reminder_id,
        ContactReminder.clinic_id == current_user.clinic_id
    ).first()

    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    db.delete(reminder)
    db.commit()

    return {"status": "deleted"}


# ============================================================================
# 7. TASKS
# ============================================================================

@router.get("/tasks")
async def list_tasks(
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List tasks with filters."""
    query = db.query(ContactTask).filter(
        ContactTask.clinic_id == current_user.clinic_id
    )

    if lead_id:
        query = query.filter(ContactTask.lead_id == lead_id)
    if status:
        query = query.filter(ContactTask.status == status)
    if priority:
        query = query.filter(ContactTask.priority == priority)
    if assigned_to:
        query = query.filter(ContactTask.assigned_to_id == assigned_to)
    if category:
        query = query.filter(ContactTask.category == category)

    total = query.count()
    tasks = query.order_by(ContactTask.due_date.asc()).offset(skip).limit(limit).all()

    results = []
    for t in tasks:
        results.append({
            "id": t.id,
            "lead_id": t.lead_id,
            "assigned_to_id": t.assigned_to_id,
            "title": t.title,
            "description": t.description,
            "due_date": str(t.due_date) if t.due_date else None,
            "status": t.status,
            "priority": t.priority,
            "category": t.category,
            "created_at": str(t.created_at) if t.created_at else None,
            "completed_at": str(t.completed_at) if t.completed_at else None,
        })

    return {"tasks": results, "total": total}


@router.post("/tasks")
async def create_task(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new task."""
    if "title" not in data:
        raise HTTPException(status_code=400, detail="title required")

    task = ContactTask(
        clinic_id=current_user.clinic_id,
        lead_id=data.get("lead_id"),
        assigned_to_id=data.get("assigned_to_id", current_user.id),
        title=data["title"],
        description=data.get("description"),
        due_date=data.get("due_date"),
        priority=data.get("priority", "medium"),
        category=data.get("category", "sales"),
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    log_platform_activity(db, current_user.clinic_id, "lead", "task_created",
                          {"title": data["title"], "category": data.get("category", "sales"),
                           "priority": data.get("priority", "medium")}, current_user.email)

    return {"status": "created", "task_id": task.id}


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a task."""
    task = db.query(ContactTask).filter(
        ContactTask.id == task_id,
        ContactTask.clinic_id == current_user.clinic_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    allowed = ["title", "description", "due_date", "priority", "category", "status", "assigned_to_id"]
    for field, value in data.items():
        if field in allowed:
            setattr(task, field, value)

    if data.get("status") == "completed" and not task.completed_at:
        task.completed_at = datetime.utcnow()

    db.commit()

    return {"status": "updated", "task_id": task.id}


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a task."""
    task = db.query(ContactTask).filter(
        ContactTask.id == task_id,
        ContactTask.clinic_id == current_user.clinic_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    return {"status": "deleted"}
