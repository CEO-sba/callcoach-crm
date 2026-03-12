"""
CallCoach CRM - Telephony Integration Models
Supports Twilio, Exotel, and Plivo providers
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class TelephonyConfig(Base):
    __tablename__ = "telephony_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), unique=True, nullable=False)

    # Provider selection
    provider = Column(String(50), nullable=False)  # "twilio", "exotel", "plivo"
    is_active = Column(Boolean, default=True)

    # Twilio fields
    account_sid = Column(String(200), nullable=True)
    auth_token = Column(String(200), nullable=True)
    twilio_phone = Column(String(50), nullable=True)  # Twilio phone number

    # Exotel fields
    exotel_sid = Column(String(200), nullable=True)
    exotel_token = Column(String(200), nullable=True)
    exotel_subdomain = Column(String(200), nullable=True)
    exotel_caller_id = Column(String(50), nullable=True)

    # Plivo fields
    plivo_auth_id = Column(String(200), nullable=True)
    plivo_auth_token = Column(String(200), nullable=True)
    plivo_phone = Column(String(50), nullable=True)

    # Webhook URLs (auto-generated)
    webhook_url = Column(String(500), nullable=True)  # Base webhook URL
    status_callback_url = Column(String(500), nullable=True)  # Call status callback
    recording_callback_url = Column(String(500), nullable=True)  # Recording ready callback

    # Configuration
    enable_recording = Column(Boolean, default=True)
    enable_transcription = Column(Boolean, default=True)
    enable_ai_analysis = Column(Boolean, default=True)

    # Metadata
    test_status = Column(String(50), nullable=True)  # "success", "failed", "pending"
    test_error = Column(Text, nullable=True)
    last_test_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", foreign_keys=[clinic_id])


class TelephonyCall(Base):
    """Extended call information for provider-initiated calls."""
    __tablename__ = "telephony_calls"

    id = Column(String, primary_key=True, default=generate_uuid)
    call_id = Column(String, ForeignKey("calls.id"), nullable=False, unique=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Provider identifiers
    provider = Column(String(50), nullable=False)  # "twilio", "exotel", "plivo"
    provider_call_sid = Column(String(200), nullable=True)  # External call ID from provider

    # Call details for provider API
    to_number = Column(String(50), nullable=False)
    from_number = Column(String(50), nullable=True)

    # Recording and transcription
    recording_sid = Column(String(200), nullable=True)  # Provider's recording ID
    recording_url = Column(String(500), nullable=True)  # Provider's recording URL
    recording_downloaded_at = Column(DateTime, nullable=True)

    # Provider-specific metadata
    provider_metadata = Column(JSON, nullable=True)  # Additional provider-specific data

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    call = relationship("Call", foreign_keys=[call_id])
    clinic = relationship("Clinic", foreign_keys=[clinic_id])
