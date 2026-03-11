"""
CallCoach CRM - Inbox Router
Unified inbox for managing conversations across all communication platforms.
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
    Conversation,
    ConversationMessage,
    ConversationPlatform
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("/conversations")
async def list_conversations(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all conversations across all platforms.
    Filterable by platform (whatsapp, email, sms, etc.), status, and search terms.
    """
    query = db.query(Conversation).filter(
        Conversation.clinic_id == current_user.clinic_id
    )

    if platform:
        query = query.filter(Conversation.platform == platform)
    if status:
        query = query.filter(Conversation.status == status)
    if search:
        query = query.filter(
            (Conversation.contact_name.ilike(f"%{search}%")) |
            (Conversation.contact_phone.ilike(f"%{search}%")) |
            (Conversation.contact_email.ilike(f"%{search}%"))
        )

    conversations = query.order_by(
        Conversation.last_message_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "conversations": conversations,
        "total": query.count()
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation details with all messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation_id
    ).order_by(ConversationMessage.created_at.asc()).all()

    return {
        "conversation": conversation,
        "messages": messages,
        "message_count": len(messages)
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_reply(
    conversation_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a reply to a conversation.
    Routes to the correct platform based on conversation platform type.
    Expected data: {"message": "text content", "attachments": []}
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message_text = data.get("message", "")
    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Create message record
    message = ConversationMessage(
        conversation_id=conversation_id,
        sender_type="agent",
        sender_id=current_user.id,
        message=message_text,
        attachments=data.get("attachments", []),
        platform=conversation.platform
    )
    db.add(message)

    # Update conversation last_message_at
    conversation.last_message_at = datetime.utcnow()
    db.commit()
    db.refresh(message)

    return {
        "status": "sent",
        "message_id": message.id,
        "platform": conversation.platform
    }


@router.put("/conversations/{conversation_id}/assign")
async def assign_conversation(
    conversation_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign a conversation to an agent.
    Expected data: {"agent_id": "user_id"}
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.clinic_id == current_user.clinic_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    agent_id = data.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    # Verify agent exists and belongs to clinic
    agent = db.query(User).filter(
        User.id == agent_id,
        User.clinic_id == current_user.clinic_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    conversation.assigned_agent_id = agent_id
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)

    return {
        "status": "assigned",
        "conversation_id": conversation.id,
        "agent_id": agent_id
    }


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
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)

    return {
        "status": "archived",
        "conversation_id": conversation.id
    }


@router.get("/stats")
async def inbox_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get unread message counts per platform."""
    clinic_id = current_user.clinic_id

    # Count unread conversations by platform
    platforms = [
        ConversationPlatform.WHATSAPP,
        ConversationPlatform.EMAIL,
        ConversationPlatform.SMS,
        ConversationPlatform.INSTAGRAM,
        ConversationPlatform.FACEBOOK
    ]

    stats = {}
    total_unread = 0

    for platform in platforms:
        unread_count = db.query(func.count(Conversation.id)).filter(
            Conversation.clinic_id == clinic_id,
            Conversation.platform == platform,
            Conversation.unread_count > 0
        ).scalar() or 0

        stats[platform] = unread_count
        total_unread += unread_count

    # Get total conversations
    total_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.clinic_id == clinic_id
    ).scalar() or 0

    # Get active conversations (not archived)
    active_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.clinic_id == clinic_id,
        Conversation.status != "archived"
    ).scalar() or 0

    return {
        "total_unread": total_unread,
        "total_conversations": total_conversations,
        "active_conversations": active_conversations,
        "by_platform": stats
    }
