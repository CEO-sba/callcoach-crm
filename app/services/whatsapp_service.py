"""
CallCoach CRM - WhatsApp Cloud API Service
Handles sending/receiving messages via Meta's WhatsApp Business Cloud API.
"""
import logging
import httpx
from typing import Optional
from app.config import WHATSAPP_API_BASE

logger = logging.getLogger(__name__)


async def send_text_message(phone_number_id: str, access_token: str, to_phone: str, message: str) -> Optional[str]:
    """Send a text message via WhatsApp Cloud API. Returns wa_message_id or None."""
    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": message}
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            data = resp.json()

            if resp.status_code == 200 and "messages" in data:
                wa_msg_id = data["messages"][0]["id"]
                logger.info(f"WhatsApp message sent to {to_phone}: {wa_msg_id}")
                return wa_msg_id
            else:
                logger.error(f"WhatsApp API error: {resp.status_code} - {data}")
                return None
    except Exception as e:
        logger.error(f"WhatsApp send failed to {to_phone}: {e}")
        return None


async def send_template_message(
    phone_number_id: str, access_token: str, to_phone: str,
    template_name: str, language_code: str = "en",
    components: Optional[list] = None
) -> Optional[str]:
    """Send a template message (for initiating conversations after 24hr window)."""
    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    template_obj = {
        "name": template_name,
        "language": {"code": language_code}
    }
    if components:
        template_obj["components"] = components

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "template",
        "template": template_obj
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            data = resp.json()

            if resp.status_code == 200 and "messages" in data:
                wa_msg_id = data["messages"][0]["id"]
                logger.info(f"WhatsApp template sent to {to_phone}: {wa_msg_id}")
                return wa_msg_id
            else:
                logger.error(f"WhatsApp template API error: {resp.status_code} - {data}")
                return None
    except Exception as e:
        logger.error(f"WhatsApp template send failed to {to_phone}: {e}")
        return None


async def mark_message_read(phone_number_id: str, access_token: str, wa_message_id: str) -> bool:
    """Mark a message as read (blue ticks)."""
    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": wa_message_id
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload, headers=headers)
            return resp.status_code == 200
    except Exception:
        return False


def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format (digits only, with country code)."""
    digits = "".join(c for c in phone if c.isdigit())
    # If starts with 0, assume India (+91)
    if digits.startswith("0"):
        digits = "91" + digits[1:]
    # If 10 digits, assume India
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def parse_webhook_message(body: dict) -> Optional[dict]:
    """Parse incoming WhatsApp webhook payload. Returns message data or None."""
    try:
        entry = body.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})

        # Check for status updates
        statuses = value.get("statuses", [])
        if statuses:
            status = statuses[0]
            return {
                "type": "status",
                "wa_message_id": status.get("id"),
                "status": status.get("status"),  # sent, delivered, read
                "recipient": status.get("recipient_id"),
                "phone_number_id": value.get("metadata", {}).get("phone_number_id")
            }

        # Check for incoming messages
        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}

        result = {
            "type": "message",
            "wa_message_id": msg.get("id"),
            "from_phone": msg.get("from"),
            "contact_name": contact.get("profile", {}).get("name", ""),
            "timestamp": msg.get("timestamp"),
            "message_type": msg.get("type", "text"),
            "phone_number_id": value.get("metadata", {}).get("phone_number_id")
        }

        # Extract content based on type
        msg_type = msg.get("type", "text")
        if msg_type == "text":
            result["content"] = msg.get("text", {}).get("body", "")
        elif msg_type == "image":
            result["content"] = msg.get("image", {}).get("caption", "")
            result["media_id"] = msg.get("image", {}).get("id")
        elif msg_type == "document":
            result["content"] = msg.get("document", {}).get("caption", "")
            result["media_id"] = msg.get("document", {}).get("id")
        elif msg_type == "audio":
            result["content"] = "[Audio message]"
            result["media_id"] = msg.get("audio", {}).get("id")
        elif msg_type == "video":
            result["content"] = msg.get("video", {}).get("caption", "")
            result["media_id"] = msg.get("video", {}).get("id")
        elif msg_type == "location":
            loc = msg.get("location", {})
            result["content"] = f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"
        elif msg_type == "button":
            result["content"] = msg.get("button", {}).get("text", "")
        elif msg_type == "interactive":
            interactive = msg.get("interactive", {})
            if "button_reply" in interactive:
                result["content"] = interactive["button_reply"].get("title", "")
            elif "list_reply" in interactive:
                result["content"] = interactive["list_reply"].get("title", "")
        else:
            result["content"] = f"[{msg_type} message]"

        return result

    except Exception as e:
        logger.error(f"Error parsing WhatsApp webhook: {e}")
        return None
