"""
CallCoach CRM - WhatsApp Router
Handles WhatsApp Cloud API webhooks, conversations, and messaging.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity
from app.models_whatsapp import (
    WhatsAppConfig, AIEmployee, WhatsAppConversation, WhatsAppMessage, Lead
)
from app.schemas_whatsapp import (
    WhatsAppConfigCreate, WhatsAppConfigOut, AIEmployeeUpdate, AIEmployeeOut,
    WhatsAppConversationOut, WhatsAppConversationDetail, WhatsAppMessageOut,
    SendMessageRequest
)
from app.services.whatsapp_service import (
    send_text_message, parse_webhook_message, normalize_phone, mark_message_read
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


# ---------------------------------------------------------------------------
# Webhook Endpoints (public - Meta sends data here)
# ---------------------------------------------------------------------------

@router.get("/webhook")
async def verify_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Meta webhook verification. Responds with hub.challenge to prove ownership."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token and challenge:
        # Find a config with this verify token
        config = db.query(WhatsAppConfig).filter(
            WhatsAppConfig.webhook_verify_token == token,
            WhatsAppConfig.is_active == True
        ).first()

        if config:
            logger.info(f"WhatsApp webhook verified for clinic {config.clinic_id}")
            return int(challenge)

    logger.warning(f"WhatsApp webhook verification failed: mode={mode}")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive incoming WhatsApp messages and status updates from Meta."""
    try:
        body = await request.json()
    except Exception:
        return {"status": "ok"}

    parsed = parse_webhook_message(body)
    if not parsed:
        return {"status": "ok"}

    # Extract phone_number_id to find the clinic
    phone_number_id = parsed.get("phone_number_id")
    if not phone_number_id:
        return {"status": "ok"}

    config = db.query(WhatsAppConfig).filter(
        WhatsAppConfig.phone_number_id == phone_number_id,
        WhatsAppConfig.is_active == True
    ).first()

    if not config:
        logger.warning(f"No active WhatsApp config for phone_number_id: {phone_number_id}")
        return {"status": "ok"}

    # Handle status updates (sent, delivered, read)
    if parsed["type"] == "status":
        _handle_status_update(db, parsed)
        return {"status": "ok"}

    # Handle incoming messages
    if parsed["type"] == "message":
        await _handle_incoming_message(db, config, parsed)

    return {"status": "ok"}


def _handle_status_update(db: Session, parsed: dict):
    """Update message status (sent -> delivered -> read)."""
    wa_msg_id = parsed.get("wa_message_id")
    new_status = parsed.get("status")

    if wa_msg_id and new_status:
        msg = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.wa_message_id == wa_msg_id
        ).first()
        if msg:
            msg.status = new_status
            db.commit()


async def _handle_incoming_message(db: Session, config: WhatsAppConfig, parsed: dict):
    """Process an incoming WhatsApp message."""
    from_phone = normalize_phone(parsed.get("from_phone", ""))
    contact_name = parsed.get("contact_name", "")
    content = parsed.get("content", "")
    message_type = parsed.get("message_type", "text")
    wa_message_id = parsed.get("wa_message_id", "")

    # Find or create conversation
    conversation = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.clinic_id == config.clinic_id,
        WhatsAppConversation.wa_phone == from_phone
    ).first()

    if not conversation:
        # Create lead first
        lead = Lead(
            clinic_id=config.clinic_id,
            name=contact_name or f"WhatsApp {from_phone}",
            phone=from_phone,
            source="whatsapp"
        )
        db.add(lead)
        db.flush()

        conversation = WhatsAppConversation(
            clinic_id=config.clinic_id,
            lead_id=lead.id,
            wa_phone=from_phone,
            contact_name=contact_name,
            is_ai_handling=True
        )
        db.add(conversation)
        db.flush()
    else:
        # Update contact name if we have a better one
        if contact_name and not conversation.contact_name:
            conversation.contact_name = contact_name

    # Save the message
    message = WhatsAppMessage(
        conversation_id=conversation.id,
        direction="inbound",
        message_type=message_type,
        content=content,
        wa_message_id=wa_message_id,
        sender_type="lead",
        status="received"
    )
    if parsed.get("media_id"):
        message.media_url = parsed["media_id"]  # store media ID for later retrieval

    db.add(message)

    # Update conversation metadata
    conversation.last_message_at = datetime.utcnow()
    conversation.last_message_preview = content[:200] if content else f"[{message_type}]"
    conversation.unread_count = (conversation.unread_count or 0) + 1

    db.commit()

    # Log incoming message
    try:
        log_activity(db, config.clinic_id, "ai_employee", "whatsapp_message_received",
                     {"phone": from_phone, "type": message_type, "content_preview": content[:80]})
    except Exception:
        pass

    # Mark as read (blue ticks)
    if wa_message_id:
        await mark_message_read(config.phone_number_id, config.access_token, wa_message_id)

    # AI auto-reply if enabled
    if conversation.is_ai_handling:
        ai_employee = db.query(AIEmployee).filter(
            AIEmployee.clinic_id == config.clinic_id
        ).first()

        if ai_employee and ai_employee.auto_reply_enabled:
            try:
                from app.services.ai_employee_service import generate_ai_reply
                ai_reply = await generate_ai_reply(db, config.clinic_id, conversation.id, content)

                if ai_reply:
                    # Send the reply via WhatsApp
                    wa_reply_id = await send_text_message(
                        config.phone_number_id,
                        config.access_token,
                        from_phone,
                        ai_reply
                    )

                    # Save outbound message
                    outbound = WhatsAppMessage(
                        conversation_id=conversation.id,
                        direction="outbound",
                        message_type="text",
                        content=ai_reply,
                        wa_message_id=wa_reply_id,
                        sender_type="ai_employee",
                        status="sent" if wa_reply_id else "failed"
                    )
                    db.add(outbound)

                    # Update AI message count and check handoff threshold
                    conversation.ai_message_count = (conversation.ai_message_count or 0) + 1
                    conversation.last_message_at = datetime.utcnow()
                    conversation.last_message_preview = ai_reply[:200]

                    if ai_employee.max_messages_before_handoff and \
                       conversation.ai_message_count >= ai_employee.max_messages_before_handoff:
                        conversation.is_ai_handling = False
                        conversation.status = "handed_off"
                        logger.info(f"Conversation {conversation.id} handed off after {conversation.ai_message_count} AI messages")
                        try:
                            log_activity(db, config.clinic_id, "ai_employee", "conversation_handed_off",
                                         {"conversation_id": conversation.id, "ai_messages": conversation.ai_message_count,
                                          "phone": from_phone})
                        except Exception:
                            pass

                    db.commit()
                    try:
                        log_activity(db, config.clinic_id, "ai_employee", "ai_reply_sent",
                                     {"conversation_id": conversation.id, "reply_preview": ai_reply[:80],
                                      "phone": from_phone})
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"AI reply failed for conversation {conversation.id}: {e}")


# ---------------------------------------------------------------------------
# WhatsApp Config (authenticated endpoints)
# ---------------------------------------------------------------------------

@router.get("/config", response_model=Optional[WhatsAppConfigOut])
def get_whatsapp_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get WhatsApp configuration for the current clinic."""
    config = db.query(WhatsAppConfig).filter(
        WhatsAppConfig.clinic_id == current_user.clinic_id
    ).first()
    return config


@router.post("/config", response_model=WhatsAppConfigOut)
def save_whatsapp_config(
    data: WhatsAppConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update WhatsApp Cloud API credentials."""
    config = db.query(WhatsAppConfig).filter(
        WhatsAppConfig.clinic_id == current_user.clinic_id
    ).first()

    if config:
        config.phone_number_id = data.phone_number_id
        config.waba_id = data.waba_id
        config.access_token = data.access_token
        config.business_name = data.business_name
        config.business_phone = data.business_phone
        config.is_active = True
        config.connected_at = datetime.utcnow()
    else:
        config = WhatsAppConfig(
            clinic_id=current_user.clinic_id,
            phone_number_id=data.phone_number_id,
            waba_id=data.waba_id,
            access_token=data.access_token,
            business_name=data.business_name,
            business_phone=data.business_phone,
            is_active=True,
            connected_at=datetime.utcnow()
        )
        db.add(config)

    db.commit()
    db.refresh(config)
    log_activity(db, current_user.clinic_id, "ai_employee", "whatsapp_config_saved",
                 {"business_name": data.business_name, "phone": data.business_phone}, current_user.email)

    # Auto-create AI Employee if not exists
    ai_emp = db.query(AIEmployee).filter(
        AIEmployee.clinic_id == current_user.clinic_id
    ).first()
    if not ai_emp:
        ai_emp = AIEmployee(clinic_id=current_user.clinic_id)
        db.add(ai_emp)
        db.commit()

    return config


@router.delete("/config")
def disconnect_whatsapp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect WhatsApp (deactivate, keep data)."""
    config = db.query(WhatsAppConfig).filter(
        WhatsAppConfig.clinic_id == current_user.clinic_id
    ).first()
    if config:
        config.is_active = False
        db.commit()
        log_activity(db, current_user.clinic_id, "ai_employee", "whatsapp_disconnected",
                     {}, current_user.email)
    return {"status": "disconnected"}


# ---------------------------------------------------------------------------
# AI Employee Config
# ---------------------------------------------------------------------------

@router.get("/ai-employee", response_model=Optional[AIEmployeeOut])
def get_ai_employee(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI Employee configuration."""
    ai = db.query(AIEmployee).filter(
        AIEmployee.clinic_id == current_user.clinic_id
    ).first()
    return ai


@router.put("/ai-employee", response_model=AIEmployeeOut)
def update_ai_employee(
    data: AIEmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update AI Employee settings."""
    ai = db.query(AIEmployee).filter(
        AIEmployee.clinic_id == current_user.clinic_id
    ).first()

    if not ai:
        ai = AIEmployee(clinic_id=current_user.clinic_id)
        db.add(ai)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ai, field, value)

    db.commit()
    db.refresh(ai)
    log_activity(db, current_user.clinic_id, "ai_employee", "ai_employee_config_updated",
                 {"fields_updated": list(update_data.keys())}, current_user.email)
    return ai


@router.post("/test-ai")
def test_ai_employee(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test AI Employee with a sample message and get the AI reply."""
    message = data.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    ai = db.query(AIEmployee).filter(
        AIEmployee.clinic_id == current_user.clinic_id
    ).first()
    if not ai:
        raise HTTPException(status_code=404, detail="AI Employee not configured. Save your configuration first.")

    try:
        from app.services.ai_employee_service import generate_ai_reply
        reply = generate_ai_reply(db, ai, message, conversation_history=[])
        return {"reply": reply}
    except Exception as e:
        logger.error(f"Test AI error: {e}")
        return {"reply": f"Error generating reply: {str(e)}. Make sure the Anthropic API key is configured."}


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

@router.get("/conversations", response_model=list[WhatsAppConversationOut])
def list_conversations(
    status: Optional[str] = None,
    is_ai: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List WhatsApp conversations for the clinic."""
    query = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.clinic_id == current_user.clinic_id
    )

    if status:
        query = query.filter(WhatsAppConversation.status == status)
    if is_ai is not None:
        query = query.filter(WhatsAppConversation.is_ai_handling == is_ai)

    conversations = query.order_by(
        WhatsAppConversation.last_message_at.desc().nullslast()
    ).offset(skip).limit(limit).all()

    return conversations


@router.get("/conversations/{conversation_id}", response_model=WhatsAppConversationDetail)
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation with all messages."""
    convo = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conversation_id,
        WhatsAppConversation.clinic_id == current_user.clinic_id
    ).first()

    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Reset unread count when opened
    convo.unread_count = 0
    db.commit()

    return convo


@router.post("/conversations/{conversation_id}/send")
async def send_message(
    conversation_id: str,
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message in a conversation (manual agent reply)."""
    convo = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conversation_id,
        WhatsAppConversation.clinic_id == current_user.clinic_id
    ).first()

    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    config = db.query(WhatsAppConfig).filter(
        WhatsAppConfig.clinic_id == current_user.clinic_id,
        WhatsAppConfig.is_active == True
    ).first()

    if not config:
        raise HTTPException(status_code=400, detail="WhatsApp not connected")

    # Send via WhatsApp API
    wa_msg_id = await send_text_message(
        config.phone_number_id,
        config.access_token,
        convo.wa_phone,
        data.content
    )

    # Save message
    message = WhatsAppMessage(
        conversation_id=conversation_id,
        direction="outbound",
        message_type="text",
        content=data.content,
        wa_message_id=wa_msg_id,
        sender_type="agent",
        status="sent" if wa_msg_id else "failed"
    )
    db.add(message)

    # Update conversation
    convo.last_message_at = datetime.utcnow()
    convo.last_message_preview = data.content[:200]
    convo.is_ai_handling = False  # Agent took over

    db.commit()
    db.refresh(message)
    log_activity(db, current_user.clinic_id, "ai_employee", "agent_message_sent",
                 {"conversation_id": conversation_id, "phone": convo.wa_phone,
                  "content_preview": data.content[:80]}, current_user.email)

    return {"status": "sent" if wa_msg_id else "failed", "message_id": message.id, "wa_message_id": wa_msg_id}


@router.post("/conversations/{conversation_id}/toggle-ai")
def toggle_ai_handling(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle AI handling on/off for a conversation."""
    convo = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conversation_id,
        WhatsAppConversation.clinic_id == current_user.clinic_id
    ).first()

    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    convo.is_ai_handling = not convo.is_ai_handling
    if convo.is_ai_handling:
        convo.status = "active"
        convo.ai_message_count = 0  # Reset count when re-enabling
    else:
        convo.status = "handed_off"

    db.commit()
    log_activity(db, current_user.clinic_id, "ai_employee", "ai_handling_toggled",
                 {"conversation_id": conversation_id, "is_ai_handling": convo.is_ai_handling},
                 current_user.email)

    return {"is_ai_handling": convo.is_ai_handling, "status": convo.status}


@router.post("/conversations/{conversation_id}/close")
def close_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Close a conversation."""
    convo = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conversation_id,
        WhatsAppConversation.clinic_id == current_user.clinic_id
    ).first()

    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    convo.status = "closed"
    convo.is_ai_handling = False
    db.commit()
    log_activity(db, current_user.clinic_id, "ai_employee", "conversation_closed",
                 {"conversation_id": conversation_id}, current_user.email)

    return {"status": "closed"}
