"""
CallCoach CRM - Schemas for WhatsApp, Leads, Nurture, Social Media & Meta
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------
class LeadCreate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: str = "manual"
    campaign_name: Optional[str] = None
    campaign_source: Optional[str] = None
    campaign_medium: Optional[str] = None
    procedure_interest: Optional[str] = None
    form_data: Optional[dict] = None
    tags: Optional[list] = []

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    lead_score: Optional[int] = None
    assigned_agent_id: Optional[str] = None
    procedure_interest: Optional[str] = None
    tags: Optional[list] = None
    lost_reason: Optional[str] = None

class LeadOut(BaseModel):
    id: str
    clinic_id: str
    name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    source: str
    campaign_name: Optional[str]
    campaign_source: Optional[str]
    lead_score: int
    status: str
    procedure_interest: Optional[str]
    form_data: Optional[dict]
    tags: Optional[list]
    assigned_agent_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# WhatsApp Config
# ---------------------------------------------------------------------------
class WhatsAppConfigCreate(BaseModel):
    phone_number_id: str
    waba_id: str
    access_token: str
    business_name: Optional[str] = None
    business_phone: Optional[str] = None

class WhatsAppConfigOut(BaseModel):
    id: str
    clinic_id: str
    phone_number_id: Optional[str]
    waba_id: Optional[str]
    business_name: Optional[str]
    business_phone: Optional[str]
    webhook_verify_token: str
    is_active: bool
    connected_at: Optional[datetime]
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AI Employee
# ---------------------------------------------------------------------------
class AIEmployeeUpdate(BaseModel):
    name: Optional[str] = None
    greeting_message: Optional[str] = None
    after_hours_message: Optional[str] = None
    business_hours: Optional[dict] = None
    procedures_offered: Optional[list] = None
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
    booking_link: Optional[str] = None
    doctor_name: Optional[str] = None
    tone: Optional[str] = None
    language: Optional[str] = None
    auto_reply_enabled: Optional[bool] = None
    followup_enabled: Optional[bool] = None
    max_messages_before_handoff: Optional[int] = None
    system_prompt: Optional[str] = None

class AIEmployeeOut(BaseModel):
    id: str
    clinic_id: str
    name: str
    greeting_message: Optional[str]
    after_hours_message: Optional[str]
    business_hours: Optional[dict]
    procedures_offered: Optional[list]
    clinic_address: Optional[str]
    clinic_phone: Optional[str]
    booking_link: Optional[str]
    doctor_name: Optional[str]
    tone: str
    language: str
    auto_reply_enabled: bool
    followup_enabled: bool
    max_messages_before_handoff: int
    system_prompt: Optional[str]
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# WhatsApp Conversation & Messages
# ---------------------------------------------------------------------------
class WhatsAppMessageOut(BaseModel):
    id: str
    direction: str
    message_type: str
    content: Optional[str]
    media_url: Optional[str]
    sender_type: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class WhatsAppConversationOut(BaseModel):
    id: str
    clinic_id: str
    lead_id: Optional[str]
    wa_phone: str
    contact_name: Optional[str]
    status: str
    is_ai_handling: bool
    unread_count: int
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class WhatsAppConversationDetail(WhatsAppConversationOut):
    messages: List[WhatsAppMessageOut] = []

class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str


# ---------------------------------------------------------------------------
# Nurture Sequence
# ---------------------------------------------------------------------------
class NurtureStepCreate(BaseModel):
    step_number: int
    delay_hours: int = 0
    delay_type: str = "hours"
    message_template: str
    channel: str = "whatsapp"
    step_type: str = "message"
    is_ai_generated: bool = False

class NurtureStepOut(BaseModel):
    id: str
    step_number: int
    delay_hours: int
    delay_type: str
    message_template: str
    channel: str
    step_type: str
    is_ai_generated: bool
    created_at: datetime
    class Config:
        from_attributes = True

class NurtureSequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    procedure_category: Optional[str] = None
    trigger_type: str = "manual"
    steps: List[NurtureStepCreate] = []

class NurtureSequenceOut(BaseModel):
    id: str
    clinic_id: Optional[str]
    name: str
    description: Optional[str]
    procedure_category: Optional[str]
    trigger_type: str
    is_active: bool
    is_template: bool
    total_steps: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class NurtureSequenceDetail(NurtureSequenceOut):
    steps: List[NurtureStepOut] = []

class NurtureEnrollmentCreate(BaseModel):
    lead_id: str
    sequence_id: str
    metadata: Optional[dict] = {}

class NurtureEnrollmentOut(BaseModel):
    id: str
    lead_id: str
    sequence_id: str
    clinic_id: str
    current_step: int
    status: str
    next_send_at: Optional[datetime]
    enrolled_at: datetime
    completed_at: Optional[datetime]
    metadata: Optional[dict]
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Social Media
# ---------------------------------------------------------------------------
class SocialAccountConnect(BaseModel):
    platform: str
    access_token: str
    refresh_token: Optional[str] = None
    account_name: Optional[str] = None
    account_id: Optional[str] = None
    profile_url: Optional[str] = None

class SocialAccountOut(BaseModel):
    id: str
    clinic_id: str
    platform: str
    account_name: Optional[str]
    account_id: Optional[str]
    profile_url: Optional[str]
    profile_image_url: Optional[str]
    followers_count: int
    posts_count: int
    is_active: bool
    connected_at: datetime
    class Config:
        from_attributes = True

class SocialPostCreate(BaseModel):
    content: str
    media_urls: Optional[list] = []
    media_type: Optional[str] = None
    platforms: list  # ["instagram", "facebook"]
    platform_specific: Optional[dict] = {}
    scheduled_at: Optional[datetime] = None

class SocialPostUpdate(BaseModel):
    content: Optional[str] = None
    media_urls: Optional[list] = None
    platforms: Optional[list] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None

class SocialPostOut(BaseModel):
    id: str
    clinic_id: str
    content: str
    media_urls: Optional[list]
    media_type: Optional[str]
    platforms: list
    platform_specific: Optional[dict]
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    status: str
    published_urls: Optional[dict]
    is_ai_generated: bool
    created_at: datetime
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Marketing Insight
# ---------------------------------------------------------------------------
class MarketingInsightOut(BaseModel):
    id: str
    clinic_id: str
    call_id: Optional[str]
    insight_type: Optional[str]
    category: Optional[str]
    title: Optional[str]
    content: str
    source_quote: Optional[str]
    is_used: bool
    created_at: datetime
    class Config:
        from_attributes = True

class GenerateAdAnglesRequest(BaseModel):
    procedure_category: Optional[str] = None
    num_angles: int = 5

class GenerateContentIdeasRequest(BaseModel):
    platform: str = "instagram"  # instagram, youtube, linkedin
    content_type: str = "reel"  # reel, carousel, post, video
    num_ideas: int = 5


# ---------------------------------------------------------------------------
# Meta Integration
# ---------------------------------------------------------------------------
class MetaConnectRequest(BaseModel):
    access_token: str
    page_id: str
    page_name: Optional[str] = None

class MetaConfigOut(BaseModel):
    id: str
    clinic_id: str
    page_id: Optional[str]
    page_name: Optional[str]
    connected_forms: Optional[list]
    is_active: bool
    connected_at: Optional[datetime]
    class Config:
        from_attributes = True
