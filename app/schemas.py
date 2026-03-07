"""
CallCoach CRM - Pydantic Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ---- Auth ----
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "agent"

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    clinic_id: str
    role: str

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    clinic_id: str
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True


# ---- Clinic ----
class ClinicCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    specialty: Optional[str] = None

class ClinicOut(BaseModel):
    id: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    city: Optional[str]
    specialty: Optional[str]
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True


# ---- Call ----
class CallCreate(BaseModel):
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    caller_email: Optional[str] = None
    call_type: str = "inbound"
    direction: str = "inbound"
    duration_seconds: int = 0
    call_date: Optional[datetime] = None
    status: str = "completed"
    deal_id: Optional[str] = None

class CallUpdate(BaseModel):
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    caller_email: Optional[str] = None
    call_type: Optional[str] = None
    status: Optional[str] = None
    deal_id: Optional[str] = None

class CallNoteCreate(BaseModel):
    content: str
    note_type: str = "manual"

class CallNoteOut(BaseModel):
    id: str
    content: str
    note_type: str
    created_at: datetime
    class Config:
        from_attributes = True

class CallScoreOut(BaseModel):
    id: str
    greeting_score: float
    discovery_score: float
    presentation_score: float
    objection_handling_score: float
    closing_score: float
    rapport_score: float
    active_listening_score: float
    urgency_creation_score: float
    follow_up_setup_score: float
    overall_score: float
    scoring_details: Optional[dict] = None
    improvement_tips: Optional[list] = None
    what_went_well: Optional[list] = None
    what_to_improve: Optional[list] = None
    created_at: datetime
    class Config:
        from_attributes = True

class CallOut(BaseModel):
    id: str
    clinic_id: str
    agent_id: str
    deal_id: Optional[str]
    caller_name: Optional[str]
    caller_phone: Optional[str]
    caller_email: Optional[str]
    call_type: str
    direction: str
    duration_seconds: int
    call_date: datetime
    status: str
    recording_path: Optional[str]
    transcription: Optional[str]
    transcription_status: Optional[str] = "none"
    ai_summary: Optional[str]
    ai_sentiment: Optional[str]
    ai_intent: Optional[str]
    ai_key_topics: Optional[list]
    ai_action_items: Optional[list]
    ai_objections_detected: Optional[list]
    ai_buying_signals: Optional[list]
    overall_score: Optional[float]
    notes: List[CallNoteOut] = []
    scores: List[CallScoreOut] = []
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


# ---- Pipeline ----
class DealCreate(BaseModel):
    contact_name: str
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    title: str
    treatment_interest: Optional[str] = None
    deal_value: float = 0
    stage: str = "new_inquiry"
    priority: str = "medium"
    source: Optional[str] = None
    next_follow_up: Optional[datetime] = None
    follow_up_notes: Optional[str] = None

class DealUpdate(BaseModel):
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    title: Optional[str] = None
    treatment_interest: Optional[str] = None
    deal_value: Optional[float] = None
    stage: Optional[str] = None
    priority: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    lost_reason: Optional[str] = None
    next_follow_up: Optional[datetime] = None
    follow_up_notes: Optional[str] = None

class DealActivityOut(BaseModel):
    id: str
    activity_type: str
    description: Optional[str]
    extra_data: Optional[dict]
    created_at: datetime
    class Config:
        from_attributes = True

class DealOut(BaseModel):
    id: str
    clinic_id: str
    contact_name: str
    contact_phone: Optional[str]
    contact_email: Optional[str]
    title: str
    treatment_interest: Optional[str]
    deal_value: float
    stage: str
    priority: str
    source: Optional[str]
    status: str
    lost_reason: Optional[str]
    next_follow_up: Optional[datetime]
    follow_up_notes: Optional[str]
    total_calls: int
    total_touchpoints: int
    ghl_contact_id: Optional[str] = None
    ghl_opportunity_id: Optional[str] = None
    ai_win_probability: Optional[float]
    ai_recommended_action: Optional[str]
    ai_deal_health: Optional[str]
    activities: List[DealActivityOut] = []
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


# ---- Coaching ----
class CoachingInsightOut(BaseModel):
    id: str
    user_id: str
    call_id: Optional[str]
    insight_type: Optional[str]
    category: Optional[str]
    title: Optional[str]
    content: str
    priority: str
    is_read: bool
    metric_name: Optional[str]
    metric_before: Optional[float]
    metric_after: Optional[float]
    metric_change_pct: Optional[float]
    created_at: datetime
    class Config:
        from_attributes = True


# ---- Dashboard ----
class DashboardStats(BaseModel):
    total_calls: int
    calls_today: int
    calls_this_week: int
    avg_call_score: float
    total_deals: int
    open_deals: int
    won_deals: int
    lost_deals: int
    pipeline_value: float
    won_value: float
    conversion_rate: float
    avg_deal_value: float
    top_agent_scores: list
    score_trend: list  # last 7 days avg scores
    calls_by_type: dict
    deals_by_stage: dict


# ---- Live Coaching ----
class LiveCoachingMessage(BaseModel):
    type: str  # transcript_chunk, coaching_tip, objection_alert, closing_cue
    content: str
    confidence: Optional[float] = None
    category: Optional[str] = None
    timestamp: Optional[float] = None
