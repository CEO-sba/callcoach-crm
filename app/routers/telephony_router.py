"""
CallCoach CRM - Telephony Integration Router
Supports Twilio, Exotel, and Plivo providers with webhooks and call management
"""
import os
import json
import logging
import traceback
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.database import get_db, SessionLocal
from app.auth import get_current_user
from app.models import User, Clinic, Call
from app.models_telephony import TelephonyConfig, TelephonyCall
from app.schemas import CallCreate, CallOut
from app.config import APP_BASE_URL, UPLOAD_DIR
from app.services.ai_coach import analyze_call
from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telephony", tags=["telephony"])

# Try to import telephony SDKs (graceful fallback if not installed)
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio SDK not installed. Using httpx fallback for Twilio.")

try:
    import plivo
    PLIVO_AVAILABLE = True
except ImportError:
    PLIVO_AVAILABLE = False
    logger.warning("Plivo SDK not installed. Using httpx fallback for Plivo.")


# ============================================================================
# Pydantic Schemas
# ============================================================================

class TelephonyConfigCreate(BaseModel):
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


class TelephonyConfigUpdate(TelephonyConfigCreate):
    is_active: Optional[bool] = None


class TelephonyConfigOut(BaseModel):
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


class OutboundCallRequest(BaseModel):
    to_number: str
    agent_id: Optional[str] = None
    deal_id: Optional[str] = None
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None


class OutboundCallResponse(BaseModel):
    call_id: str
    provider_call_sid: Optional[str] = None
    to_number: str
    from_number: str
    status: str
    message: str


class CallStatusResponse(BaseModel):
    call_id: str
    provider: str
    status: str
    duration_seconds: int
    provider_call_sid: Optional[str] = None
    recording_url: Optional[str] = None


class ClickToCallRequest(BaseModel):
    phone_number: str
    context_type: Optional[str] = None  # "deal_id", "lead_id", "contact_id"
    context_id: Optional[str] = None


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/config", response_model=TelephonyConfigOut)
async def get_telephony_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the clinic's telephony configuration (with masked credentials)."""
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic users can access telephony config"
        )

    config = db.query(TelephonyConfig).filter(
        TelephonyConfig.clinic_id == current_user.clinic_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telephony config not found"
        )

    return config


@router.post("/config", response_model=TelephonyConfigOut)
async def save_telephony_config(
    config_data: TelephonyConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update clinic's telephony configuration."""
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic users can configure telephony"
        )

    # Validate provider
    valid_providers = {"twilio", "exotel", "plivo"}
    if config_data.provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {valid_providers}"
        )

    # Get or create config
    config = db.query(TelephonyConfig).filter(
        TelephonyConfig.clinic_id == current_user.clinic_id
    ).first()

    if not config:
        config = TelephonyConfig(clinic_id=current_user.clinic_id)
        db.add(config)

    # Update fields
    config.provider = config_data.provider
    config.enable_recording = config_data.enable_recording
    config.enable_transcription = config_data.enable_transcription
    config.enable_ai_analysis = config_data.enable_ai_analysis

    # Store provider-specific credentials
    if config_data.provider == "twilio":
        config.account_sid = config_data.account_sid
        config.auth_token = config_data.auth_token
        config.twilio_phone = config_data.twilio_phone
    elif config_data.provider == "exotel":
        config.exotel_sid = config_data.exotel_sid
        config.exotel_token = config_data.exotel_token
        config.exotel_subdomain = config_data.exotel_subdomain
        config.exotel_caller_id = config_data.exotel_caller_id
    elif config_data.provider == "plivo":
        config.plivo_auth_id = config_data.plivo_auth_id
        config.plivo_auth_token = config_data.plivo_auth_token
        config.plivo_phone = config_data.plivo_phone

    # Auto-generate webhook URLs
    clinic_id = current_user.clinic_id
    base_webhook = f"{APP_BASE_URL}/api/telephony/webhook"
    config.webhook_url = base_webhook
    config.status_callback_url = f"{base_webhook}/{config_data.provider}/status/{clinic_id}"
    config.recording_callback_url = f"{base_webhook}/{config_data.provider}/recording/{clinic_id}"

    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)

    logger.info(f"Telephony config saved for clinic {current_user.clinic_id}, provider={config_data.provider}")

    # Log activity
    await log_activity(
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        activity_type="telephony_config_updated",
        description=f"Telephony provider configured: {config_data.provider}"
    )

    return config


@router.post("/test")
async def test_telephony_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test connection with configured telephony provider."""
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic users can test telephony"
        )

    config = db.query(TelephonyConfig).filter(
        TelephonyConfig.clinic_id == current_user.clinic_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telephony config not found"
        )

    if not config.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telephony configuration is not active"
        )

    try:
        success = await _test_provider_connection(config)

        config.test_status = "success" if success else "failed"
        config.test_error = None if success else "Provider API test failed"
        config.last_test_at = datetime.utcnow()
        db.commit()

        return {
            "success": success,
            "provider": config.provider,
            "message": "Connection successful" if success else "Connection failed"
        }

    except Exception as e:
        logger.error(f"Telephony test failed: {str(e)}\n{traceback.format_exc()}")
        config.test_status = "failed"
        config.test_error = str(e)
        config.last_test_at = datetime.utcnow()
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {str(e)}"
        )


@router.delete("/config")
async def disconnect_telephony(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect/delete telephony configuration."""
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic users can manage telephony"
        )

    config = db.query(TelephonyConfig).filter(
        TelephonyConfig.clinic_id == current_user.clinic_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telephony config not found"
        )

    provider = config.provider
    db.delete(config)
    db.commit()

    logger.info(f"Telephony config deleted for clinic {current_user.clinic_id}, provider was {provider}")

    await log_activity(
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        activity_type="telephony_config_deleted",
        description=f"Telephony provider disconnected: {provider}"
    )

    return {"message": "Telephony configuration removed"}


# ============================================================================
# Calling Endpoints
# ============================================================================

@router.post("/call", response_model=OutboundCallResponse)
async def initiate_outbound_call(
    call_request: OutboundCallRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate an outbound call through the configured telephony provider."""
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic users can make calls"
        )

    config = db.query(TelephonyConfig).filter(
        TelephonyConfig.clinic_id == current_user.clinic_id,
        TelephonyConfig.is_active == True
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active telephony configuration found"
        )

    # Determine agent and caller info
    agent_id = call_request.agent_id or current_user.id
    caller_name = call_request.caller_name or current_user.full_name
    caller_phone = call_request.caller_phone or config._get_from_number()

    # Create Call record in DB
    new_call = Call(
        clinic_id=current_user.clinic_id,
        agent_id=agent_id,
        deal_id=call_request.deal_id,
        caller_name=caller_name,
        caller_phone=caller_phone,
        direction="outbound",
        call_type="follow_up",
        status="in_progress"
    )
    db.add(new_call)
    db.commit()
    db.refresh(new_call)

    try:
        # Initiate call with provider
        result = await _initiate_call_with_provider(
            config=config,
            to_number=call_request.to_number,
            from_number=caller_phone,
            call_id=new_call.id
        )

        # Create TelephonyCall record
        tele_call = TelephonyCall(
            call_id=new_call.id,
            clinic_id=current_user.clinic_id,
            provider=config.provider,
            provider_call_sid=result.get("provider_call_sid"),
            to_number=call_request.to_number,
            from_number=caller_phone,
            provider_metadata=result.get("metadata", {})
        )
        db.add(tele_call)
        db.commit()

        logger.info(
            f"Outbound call initiated: {new_call.id} -> {call_request.to_number} "
            f"via {config.provider}, provider_sid={result.get('provider_call_sid')}"
        )

        # Schedule status polling
        background_tasks.add_task(
            _poll_call_status,
            clinic_id=current_user.clinic_id,
            call_id=new_call.id
        )

        return OutboundCallResponse(
            call_id=new_call.id,
            provider_call_sid=result.get("provider_call_sid"),
            to_number=call_request.to_number,
            from_number=caller_phone,
            status="in_progress",
            message="Call initiated successfully"
        )

    except Exception as e:
        logger.error(f"Failed to initiate call: {str(e)}\n{traceback.format_exc()}")
        new_call.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.get("/call/{call_id}/status", response_model=CallStatusResponse)
async def get_call_status(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current status of a call from the provider."""
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.clinic_id == current_user.clinic_id
    ).first()

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    tele_call = db.query(TelephonyCall).filter(
        TelephonyCall.call_id == call_id
    ).first()

    if not tele_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telephony call record not found"
        )

    try:
        status_info = await _get_call_status_from_provider(tele_call)
        return CallStatusResponse(
            call_id=call_id,
            provider=tele_call.provider,
            status=status_info.get("status", call.status),
            duration_seconds=call.duration_seconds,
            provider_call_sid=tele_call.provider_call_sid,
            recording_url=tele_call.recording_url
        )
    except Exception as e:
        logger.error(f"Failed to get call status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get call status: {str(e)}"
        )


# ============================================================================
# Click-to-Call Endpoint
# ============================================================================

@router.post("/click-to-call")
async def click_to_call(
    request: ClickToCallRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simplified call initiation from contact/deal pages."""
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic users can make calls"
        )

    config = db.query(TelephonyConfig).filter(
        TelephonyConfig.clinic_id == current_user.clinic_id,
        TelephonyConfig.is_active == True
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active telephony configuration found"
        )

    # Validate phone number format
    if not request.phone_number or len(request.phone_number) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number"
        )

    # Fetch context (deal_id, etc) if provided
    deal_id = None
    if request.context_type == "deal_id" and request.context_id:
        deal = db.query(Call).filter(Call.id == request.context_id).first()
        if deal:
            deal_id = deal.id

    call_req = OutboundCallRequest(
        to_number=request.phone_number,
        agent_id=current_user.id,
        deal_id=deal_id,
        caller_name=current_user.full_name
    )

    return await initiate_outbound_call(call_req, background_tasks, current_user, db)


# ============================================================================
# Public Webhooks (No Auth Required)
# ============================================================================

@router.post("/webhook/twilio/status/{clinic_id}")
async def twilio_status_callback(clinic_id: str, request: Request):
    """Twilio call status callback - updates call status and duration."""
    db = SessionLocal()
    try:
        body = await request.form()
        call_sid = body.get("CallSid")
        call_status = body.get("CallStatus")  # queued, ringing, in-progress, completed, busy, failed, no-answer

        if not call_sid:
            logger.warning("Twilio callback missing CallSid")
            return {"status": "error"}

        # Find TelephonyCall
        tele_call = db.query(TelephonyCall).filter(
            TelephonyCall.provider_call_sid == call_sid,
            TelephonyCall.clinic_id == clinic_id
        ).first()

        if not tele_call:
            logger.warning(f"Twilio callback: TelephonyCall not found for sid={call_sid}")
            return {"status": "ok"}

        call = tele_call.call
        if not call:
            logger.warning(f"Twilio callback: Call not found for tele_call={tele_call.id}")
            return {"status": "ok"}

        # Map Twilio status to internal status
        status_map = {
            "queued": "in_progress",
            "ringing": "in_progress",
            "in-progress": "in_progress",
            "completed": "completed",
            "busy": "missed",
            "failed": "missed",
            "no-answer": "missed"
        }

        call.status = status_map.get(call_status, call_status)

        # Extract duration if call completed
        if call_status == "completed":
            duration = body.get("CallDuration", "0")
            try:
                call.duration_seconds = int(duration)
            except (ValueError, TypeError):
                pass

        db.commit()
        logger.info(f"Twilio status callback: call={call.id}, status={call.status}, duration={call.duration_seconds}s")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Twilio status callback error: {str(e)}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.post("/webhook/twilio/recording/{clinic_id}")
async def twilio_recording_callback(clinic_id: str, request: Request, background_tasks: BackgroundTasks):
    """Twilio recording ready callback - downloads and processes recording."""
    db = SessionLocal()
    try:
        body = await request.form()
        call_sid = body.get("CallSid")
        recording_url = body.get("RecordingUrl")
        recording_sid = body.get("RecordingSid")

        if not call_sid or not recording_url:
            logger.warning("Twilio recording callback missing required fields")
            return {"status": "error"}

        # Find TelephonyCall
        tele_call = db.query(TelephonyCall).filter(
            TelephonyCall.provider_call_sid == call_sid,
            TelephonyCall.clinic_id == clinic_id
        ).first()

        if not tele_call:
            logger.warning(f"Twilio recording: TelephonyCall not found for sid={call_sid}")
            return {"status": "ok"}

        call = tele_call.call
        if not call:
            logger.warning(f"Twilio recording: Call not found for tele_call={tele_call.id}")
            return {"status": "ok"}

        # Update recording info
        tele_call.recording_sid = recording_sid
        tele_call.recording_url = recording_url
        tele_call.recording_downloaded_at = datetime.utcnow()
        db.commit()

        # Schedule async download and processing
        background_tasks.add_task(
            _process_twilio_recording,
            clinic_id=clinic_id,
            call_id=call.id,
            recording_url=recording_url,
            recording_sid=recording_sid
        )

        logger.info(f"Twilio recording callback: call={call.id}, recording_sid={recording_sid}")
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Twilio recording callback error: {str(e)}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.post("/webhook/exotel/status/{clinic_id}")
async def exotel_status_callback(clinic_id: str, request: Request):
    """Exotel call status callback - updates call status."""
    db = SessionLocal()
    try:
        body = await request.json()
        exotel_sid = body.get("CallSid")
        call_status = body.get("Status")  # completed, busy, failed, not-answered

        if not exotel_sid:
            logger.warning("Exotel callback missing CallSid")
            return {"status": "error"}

        tele_call = db.query(TelephonyCall).filter(
            TelephonyCall.provider_call_sid == exotel_sid,
            TelephonyCall.clinic_id == clinic_id
        ).first()

        if not tele_call:
            logger.warning(f"Exotel callback: TelephonyCall not found for sid={exotel_sid}")
            return {"status": "ok"}

        call = tele_call.call
        if not call:
            logger.warning(f"Exotel callback: Call not found for tele_call={tele_call.id}")
            return {"status": "ok"}

        # Map Exotel status to internal status
        status_map = {
            "completed": "completed",
            "busy": "missed",
            "failed": "missed",
            "not-answered": "missed"
        }

        call.status = status_map.get(call_status, call_status)

        # Extract duration if available
        duration = body.get("Duration", 0)
        if duration:
            try:
                call.duration_seconds = int(duration)
            except (ValueError, TypeError):
                pass

        db.commit()
        logger.info(f"Exotel status callback: call={call.id}, status={call.status}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Exotel status callback error: {str(e)}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.post("/webhook/exotel/recording/{clinic_id}")
async def exotel_recording_callback(clinic_id: str, request: Request, background_tasks: BackgroundTasks):
    """Exotel recording ready callback - downloads and processes recording."""
    db = SessionLocal()
    try:
        body = await request.json()
        call_sid = body.get("CallSid")
        recording_url = body.get("RecordingUrl")

        if not call_sid or not recording_url:
            logger.warning("Exotel recording callback missing required fields")
            return {"status": "error"}

        tele_call = db.query(TelephonyCall).filter(
            TelephonyCall.provider_call_sid == call_sid,
            TelephonyCall.clinic_id == clinic_id
        ).first()

        if not tele_call:
            logger.warning(f"Exotel recording: TelephonyCall not found for sid={call_sid}")
            return {"status": "ok"}

        call = tele_call.call
        if not call:
            logger.warning(f"Exotel recording: Call not found for tele_call={tele_call.id}")
            return {"status": "ok"}

        tele_call.recording_url = recording_url
        tele_call.recording_downloaded_at = datetime.utcnow()
        db.commit()

        background_tasks.add_task(
            _process_exotel_recording,
            clinic_id=clinic_id,
            call_id=call.id,
            recording_url=recording_url
        )

        logger.info(f"Exotel recording callback: call={call.id}")
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Exotel recording callback error: {str(e)}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


# ============================================================================
# Internal Helper Functions
# ============================================================================

async def _test_provider_connection(config: TelephonyConfig) -> bool:
    """Test connection with provider API."""
    try:
        if config.provider == "twilio":
            return await _test_twilio_connection(config)
        elif config.provider == "exotel":
            return await _test_exotel_connection(config)
        elif config.provider == "plivo":
            return await _test_plivo_connection(config)
        else:
            return False
    except Exception as e:
        logger.error(f"Provider connection test failed: {str(e)}")
        return False


async def _test_twilio_connection(config: TelephonyConfig) -> bool:
    """Test Twilio credentials."""
    if not config.account_sid or not config.auth_token:
        raise ValueError("Twilio credentials incomplete")

    if TWILIO_AVAILABLE:
        try:
            client = TwilioClient(config.account_sid, config.auth_token)
            # Try to fetch account info
            account = client.api.accounts(config.account_sid).fetch()
            return account.status == "active"
        except Exception as e:
            logger.warning(f"Twilio SDK test failed: {str(e)}, using httpx fallback")

    # Fallback: use httpx to make API call
    try:
        async with httpx.AsyncClient() as client:
            auth = (config.account_sid, config.auth_token)
            response = await client.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{config.account_sid}",
                auth=auth,
                timeout=10
            )
            return response.status_code == 200
    except Exception as e:
        raise ValueError(f"Twilio API test failed: {str(e)}")


async def _test_exotel_connection(config: TelephonyConfig) -> bool:
    """Test Exotel credentials."""
    if not config.exotel_sid or not config.exotel_token or not config.exotel_subdomain:
        raise ValueError("Exotel credentials incomplete")

    try:
        async with httpx.AsyncClient() as client:
            auth = (config.exotel_sid, config.exotel_token)
            url = f"https://{config.exotel_subdomain}.exotel.com/v1/Accounts/{config.exotel_sid}"
            response = await client.get(url, auth=auth, timeout=10)
            return response.status_code == 200
    except Exception as e:
        raise ValueError(f"Exotel API test failed: {str(e)}")


async def _test_plivo_connection(config: TelephonyConfig) -> bool:
    """Test Plivo credentials."""
    if not config.plivo_auth_id or not config.plivo_auth_token:
        raise ValueError("Plivo credentials incomplete")

    try:
        async with httpx.AsyncClient() as client:
            auth = (config.plivo_auth_id, config.plivo_auth_token)
            url = f"https://api.plivo.com/v1/Account/{config.plivo_auth_id}/"
            response = await client.get(url, auth=auth, timeout=10)
            return response.status_code == 200
    except Exception as e:
        raise ValueError(f"Plivo API test failed: {str(e)}")


async def _initiate_call_with_provider(
    config: TelephonyConfig,
    to_number: str,
    from_number: str,
    call_id: str
) -> Dict[str, Any]:
    """Initiate call with the configured provider."""
    if config.provider == "twilio":
        return await _initiate_twilio_call(config, to_number, from_number, call_id)
    elif config.provider == "exotel":
        return await _initiate_exotel_call(config, to_number, from_number, call_id)
    elif config.provider == "plivo":
        return await _initiate_plivo_call(config, to_number, from_number, call_id)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


async def _initiate_twilio_call(
    config: TelephonyConfig,
    to_number: str,
    from_number: str,
    call_id: str
) -> Dict[str, Any]:
    """Initiate call via Twilio."""
    if not config.account_sid or not config.auth_token or not config.twilio_phone:
        raise ValueError("Twilio configuration incomplete")

    callback_url = f"{APP_BASE_URL}/api/telephony/webhook/twilio/status/{config.clinic_id}"
    recording_callback = f"{APP_BASE_URL}/api/telephony/webhook/twilio/recording/{config.clinic_id}"

    if TWILIO_AVAILABLE:
        try:
            client = TwilioClient(config.account_sid, config.auth_token)
            call = client.calls.create(
                to=to_number,
                from_=config.twilio_phone,
                status_callback=callback_url,
                status_callback_method="POST",
                record=True,
                recording_status_callback=recording_callback,
                recording_status_callback_method="POST"
            )
            return {
                "provider_call_sid": call.sid,
                "metadata": {"call_sid": call.sid}
            }
        except Exception as e:
            logger.warning(f"Twilio SDK call failed: {str(e)}, using httpx fallback")

    # Fallback: use httpx
    try:
        async with httpx.AsyncClient() as client:
            auth = (config.account_sid, config.auth_token)
            data = {
                "To": to_number,
                "From": config.twilio_phone,
                "StatusCallback": callback_url,
                "StatusCallbackMethod": "POST",
                "Record": "true",
                "RecordingStatusCallback": recording_callback,
                "RecordingStatusCallbackMethod": "POST"
            }
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{config.account_sid}/Calls",
                auth=auth,
                data=data,
                timeout=10
            )

            if response.status_code not in (200, 201):
                raise ValueError(f"Twilio API error: {response.text}")

            result = response.json()
            return {
                "provider_call_sid": result.get("sid"),
                "metadata": result
            }
    except Exception as e:
        raise ValueError(f"Failed to initiate Twilio call: {str(e)}")


async def _initiate_exotel_call(
    config: TelephonyConfig,
    to_number: str,
    from_number: str,
    call_id: str
) -> Dict[str, Any]:
    """Initiate call via Exotel."""
    if not config.exotel_sid or not config.exotel_token or not config.exotel_subdomain or not config.exotel_caller_id:
        raise ValueError("Exotel configuration incomplete")

    try:
        async with httpx.AsyncClient() as client:
            auth = (config.exotel_sid, config.exotel_token)
            callback_url = f"{APP_BASE_URL}/api/telephony/webhook/exotel/status/{config.clinic_id}"

            data = {
                "From": config.exotel_caller_id,
                "To": to_number,
                "CallerId": config.exotel_caller_id,
                "StatusCallback": callback_url,
                "StatusCallbackMethod": "POST",
                "Record": "true"
            }

            url = f"https://{config.exotel_subdomain}.exotel.com/v1/Accounts/{config.exotel_sid}/Calls/connect"
            response = await client.post(url, auth=auth, data=data, timeout=10)

            if response.status_code not in (200, 201):
                raise ValueError(f"Exotel API error: {response.text}")

            result = response.json()
            return {
                "provider_call_sid": result.get("Call", {}).get("Sid"),
                "metadata": result
            }
    except Exception as e:
        raise ValueError(f"Failed to initiate Exotel call: {str(e)}")


async def _initiate_plivo_call(
    config: TelephonyConfig,
    to_number: str,
    from_number: str,
    call_id: str
) -> Dict[str, Any]:
    """Initiate call via Plivo."""
    if not config.plivo_auth_id or not config.plivo_auth_token or not config.plivo_phone:
        raise ValueError("Plivo configuration incomplete")

    try:
        async with httpx.AsyncClient() as client:
            auth = (config.plivo_auth_id, config.plivo_auth_token)
            callback_url = f"{APP_BASE_URL}/api/telephony/webhook/plivo/status/{config.clinic_id}"
            recording_callback = f"{APP_BASE_URL}/api/telephony/webhook/plivo/recording/{config.clinic_id}"

            data = {
                "to": to_number,
                "from": config.plivo_phone,
                "answer_url": callback_url,
                "answer_method": "POST",
                "record": "true",
                "recording_callback_url": recording_callback
            }

            url = f"https://api.plivo.com/v1/Account/{config.plivo_auth_id}/Call/"
            response = await client.post(url, auth=auth, data=data, timeout=10)

            if response.status_code not in (200, 201):
                raise ValueError(f"Plivo API error: {response.text}")

            result = response.json()
            return {
                "provider_call_sid": result.get("request_uuid"),
                "metadata": result
            }
    except Exception as e:
        raise ValueError(f"Failed to initiate Plivo call: {str(e)}")


async def _get_call_status_from_provider(tele_call: TelephonyCall) -> Dict[str, Any]:
    """Poll call status from provider."""
    if tele_call.provider == "twilio":
        return await _get_twilio_call_status(tele_call)
    elif tele_call.provider == "exotel":
        return await _get_exotel_call_status(tele_call)
    elif tele_call.provider == "plivo":
        return await _get_plivo_call_status(tele_call)
    else:
        return {"status": "unknown"}


async def _get_twilio_call_status(tele_call: TelephonyCall) -> Dict[str, Any]:
    """Get Twilio call status."""
    config = tele_call.call.clinic.telephony_configs[0] if hasattr(tele_call.call.clinic, 'telephony_configs') else None
    if not config or not tele_call.provider_call_sid:
        return {"status": "unknown"}

    try:
        async with httpx.AsyncClient() as client:
            auth = (config.account_sid, config.auth_token)
            url = f"https://api.twilio.com/2010-04-01/Accounts/{config.account_sid}/Calls/{tele_call.provider_call_sid}"
            response = await client.get(url, auth=auth, timeout=10)

            if response.status_code == 200:
                result = response.json()
                return {"status": result.get("status", "unknown")}
    except Exception as e:
        logger.warning(f"Failed to get Twilio call status: {str(e)}")

    return {"status": "unknown"}


async def _get_exotel_call_status(tele_call: TelephonyCall) -> Dict[str, Any]:
    """Get Exotel call status."""
    return {"status": "unknown"}  # Exotel doesn't provide a direct status polling API


async def _get_plivo_call_status(tele_call: TelephonyCall) -> Dict[str, Any]:
    """Get Plivo call status."""
    return {"status": "unknown"}  # Plivo updates via webhook


async def _process_twilio_recording(clinic_id: str, call_id: str, recording_url: str, recording_sid: str):
    """Download Twilio recording and trigger processing."""
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            logger.error(f"Call {call_id} not found for recording processing")
            return

        # Create directory for recordings
        clinic_recordings_dir = UPLOAD_DIR / "recordings" / clinic_id
        clinic_recordings_dir.mkdir(parents=True, exist_ok=True)

        # Download recording
        recording_path = clinic_recordings_dir / f"{call_id}.wav"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(recording_url, timeout=30)
                if response.status_code == 200:
                    with open(recording_path, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Downloaded Twilio recording to {recording_path}")
                else:
                    logger.error(f"Failed to download Twilio recording: {response.status_code}")
                    return
        except Exception as e:
            logger.error(f"Error downloading Twilio recording: {str(e)}")
            return

        # Update Call record
        call.recording_path = str(recording_path)
        call.transcription_status = "pending"
        db.commit()

        # Trigger transcription and AI analysis (reuse existing pipeline)
        logger.info(f"Triggering transcription for call {call_id}")

        # Import here to avoid circular imports
        from app.routers.calls_router import _process_call_recording_sync
        _process_call_recording_sync(call_id, str(recording_path))

    except Exception as e:
        logger.error(f"Error processing Twilio recording: {str(e)}\n{traceback.format_exc()}")
    finally:
        db.close()


async def _process_exotel_recording(clinic_id: str, call_id: str, recording_url: str):
    """Download Exotel recording and trigger processing."""
    db = SessionLocal()
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            logger.error(f"Call {call_id} not found for recording processing")
            return

        clinic_recordings_dir = UPLOAD_DIR / "recordings" / clinic_id
        clinic_recordings_dir.mkdir(parents=True, exist_ok=True)

        recording_path = clinic_recordings_dir / f"{call_id}.wav"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(recording_url, timeout=30)
                if response.status_code == 200:
                    with open(recording_path, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Downloaded Exotel recording to {recording_path}")
                else:
                    logger.error(f"Failed to download Exotel recording: {response.status_code}")
                    return
        except Exception as e:
            logger.error(f"Error downloading Exotel recording: {str(e)}")
            return

        call.recording_path = str(recording_path)
        call.transcription_status = "pending"
        db.commit()

        # Trigger transcription and AI analysis
        logger.info(f"Triggering transcription for call {call_id}")
        from app.routers.calls_router import _process_call_recording_sync
        _process_call_recording_sync(call_id, str(recording_path))

    except Exception as e:
        logger.error(f"Error processing Exotel recording: {str(e)}\n{traceback.format_exc()}")
    finally:
        db.close()


async def _poll_call_status(clinic_id: str, call_id: str, max_polls: int = 30, poll_interval: int = 2):
    """Poll provider for call status updates."""
    db = SessionLocal()
    try:
        tele_call = db.query(TelephonyCall).filter(
            TelephonyCall.call_id == call_id
        ).first()

        if not tele_call:
            logger.warning(f"TelephonyCall not found for polling: {call_id}")
            return

        for poll_count in range(max_polls):
            await asyncio.sleep(poll_interval)

            try:
                status_info = await _get_call_status_from_provider(tele_call)
                status = status_info.get("status")

                if status in ("completed", "busy", "failed", "no-answer"):
                    logger.info(f"Call {call_id} status changed to {status}")
                    break

            except Exception as e:
                logger.debug(f"Error polling call status: {str(e)}")

        logger.info(f"Call {call_id} polling completed after {poll_count + 1} polls")

    except Exception as e:
        logger.error(f"Error in call status polling: {str(e)}\n{traceback.format_exc()}")
    finally:
        db.close()
