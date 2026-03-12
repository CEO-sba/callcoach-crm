"""
CallCoach CRM - Telephony Pydantic Schemas
For use in API documentation and frontend integration
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ============================================================================
# Configuration Schemas
# ============================================================================

class TelephonyConfigCreate(BaseModel):
    """Schema for creating/updating telephony configuration."""
    provider: str  # "twilio", "exotel", "plivo"
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    twilio_phone: Optional[str] = None
    exotel_sid: Optional[str] = None
    exotel_token: Optional[str] = None
    exotel_subdomain: Optional[str] = None
    exotel_caller_id: Optional[str] = None
    plivo_auth_id: Optional[str] = None
    plivo_auth_token: Optional[str] = None
    plivo_phone: Optional[str] = None
    enable_recording: bool = True
    enable_transcription: bool = True
    enable_ai_analysis: bool = True


class TelephonyConfigUpdate(BaseModel):
    """Schema for updating telephony configuration (partial)."""
    provider: Optional[str] = None
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    twilio_phone: Optional[str] = None
    exotel_sid: Optional[str] = None
    exotel_token: Optional[str] = None
    exotel_subdomain: Optional[str] = None
    exotel_caller_id: Optional[str] = None
    plivo_auth_id: Optional[str] = None
    plivo_auth_token: Optional[str] = None
    plivo_phone: Optional[str] = None
    enable_recording: Optional[bool] = None
    enable_transcription: Optional[bool] = None
    enable_ai_analysis: Optional[bool] = None
    is_active: Optional[bool] = None


class TelephonyConfigOut(BaseModel):
    """Schema for retrieving telephony configuration."""
    id: str
    clinic_id: str
    provider: str
    is_active: bool
    twilio_phone: Optional[str] = None
    exotel_caller_id: Optional[str] = None
    plivo_phone: Optional[str] = None
    enable_recording: bool
    enable_transcription: bool
    enable_ai_analysis: bool
    webhook_url: Optional[str] = None
    status_callback_url: Optional[str] = None
    recording_callback_url: Optional[str] = None
    test_status: Optional[str] = None
    last_test_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Call Schemas
# ============================================================================

class OutboundCallRequest(BaseModel):
    """Schema for initiating outbound call."""
    to_number: str
    agent_id: Optional[str] = None
    deal_id: Optional[str] = None
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None


class OutboundCallResponse(BaseModel):
    """Schema for outbound call response."""
    call_id: str
    provider_call_sid: Optional[str] = None
    to_number: str
    from_number: str
    status: str
    message: str


class CallStatusResponse(BaseModel):
    """Schema for call status response."""
    call_id: str
    provider: str
    status: str
    duration_seconds: int
    provider_call_sid: Optional[str] = None
    recording_url: Optional[str] = None


class ClickToCallRequest(BaseModel):
    """Schema for click-to-call functionality."""
    phone_number: str
    context_type: Optional[str] = None  # "deal_id", "lead_id", "contact_id"
    context_id: Optional[str] = None


# ============================================================================
# Connection Test Schemas
# ============================================================================

class ConnectionTestResponse(BaseModel):
    """Schema for connection test response."""
    success: bool
    provider: str
    message: str


class DisconnectResponse(BaseModel):
    """Schema for disconnect response."""
    message: str


# ============================================================================
# Webhook Event Schemas
# ============================================================================

class TwilioStatusCallback(BaseModel):
    """Twilio status callback event."""
    CallSid: str
    CallStatus: str  # queued, ringing, in-progress, completed, busy, failed, no-answer
    CallDuration: Optional[str] = None
    AccountSid: Optional[str] = None
    From: Optional[str] = None
    To: Optional[str] = None


class TwilioRecordingCallback(BaseModel):
    """Twilio recording callback event."""
    CallSid: str
    RecordingSid: str
    RecordingUrl: str
    RecordingDuration: Optional[str] = None
    AccountSid: Optional[str] = None


class ExotelStatusCallback(BaseModel):
    """Exotel status callback event."""
    CallSid: str
    Status: str  # completed, busy, failed, not-answered
    Duration: Optional[int] = None


class ExotelRecordingCallback(BaseModel):
    """Exotel recording callback event."""
    CallSid: str
    RecordingUrl: str


class PlivoStatusCallback(BaseModel):
    """Plivo status callback event."""
    call_uuid: str
    status: str  # completed, busy, failed, no-answer
    duration: Optional[int] = None


class PlivoRecordingCallback(BaseModel):
    """Plivo recording callback event."""
    call_uuid: str
    recording_url: str
    duration: Optional[int] = None


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    status_code: int
    detail: str
    timestamp: datetime


class ValidationError(BaseModel):
    """Schema for validation errors."""
    field: str
    message: str
    value: Optional[str] = None
