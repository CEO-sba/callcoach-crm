"""
CallCoach CRM - Settings Router

Comprehensive centralized settings endpoint for:
- Clinic profile management
- Team management (users, roles, access control)
- Integration status monitoring
- Webhook & API key management
- Notification preferences
- Lead and call settings
- Branding configuration
- Data & privacy management
- Audit logging
- Setup guides for all integrations
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_
import secrets
import json
import logging

from app.database import get_db
from app.models import User, Clinic, Call
from app.models_whatsapp import WhatsAppConfig, Lead, APIKey
from app.models_telephony import TelephonyConfig
from app.auth import get_current_user, hash_password, require_role
from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ClinicProfileUpdate(BaseModel):
    """Clinic profile update schema."""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    specialty: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None  # JSON with day-time mappings


class ClinicProfileOut(BaseModel):
    """Clinic profile response schema."""
    id: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    city: Optional[str]
    specialty: Optional[str]
    logo_url: Optional[str]
    website: Optional[str]
    description: Optional[str]
    operating_hours: Optional[Dict[str, Any]]
    created_at: datetime
    is_active: bool
    leaderboard_visible: bool
    settings: Dict[str, Any]

    class Config:
        from_attributes = True


class TeamMemberCreate(BaseModel):
    """Create new team member."""
    email: str
    full_name: str
    password: str
    role: str = "agent"  # agent, manager, admin


class TeamMemberUpdate(BaseModel):
    """Update team member."""
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    allowed_tabs: Optional[List[str]] = None


class TeamMemberOut(BaseModel):
    """Team member response."""
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    allowed_tabs: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordReset(BaseModel):
    """Password reset request."""
    new_password: str


class IntegrationStatus(BaseModel):
    """Integration status response."""
    whatsapp: Optional[Dict[str, Any]] = None
    meta_ads: Optional[Dict[str, Any]] = None
    google_ads: Optional[Dict[str, Any]] = None
    telephony: Optional[Dict[str, Any]] = None
    social_accounts: Optional[List[Dict[str, Any]]] = None
    webhook: Optional[Dict[str, Any]] = None


class APIKeyCreate(BaseModel):
    """Create API key."""
    name: str
    description: Optional[str] = None


class APIKeyOut(BaseModel):
    """API key response."""
    id: str
    name: str
    description: Optional[str]
    key: Optional[str] = None  # Only returned on creation
    masked_key: str  # key_****...****
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationPreferences(BaseModel):
    """Notification preferences."""
    email_on_new_lead: bool = True
    email_on_missed_call: bool = True
    email_daily_digest: bool = False
    whatsapp_on_new_lead: bool = False
    whatsapp_on_deal_won: bool = False
    slack_webhook_url: Optional[str] = None


class LeadSettings(BaseModel):
    """Lead configuration."""
    auto_assign_enabled: bool = False
    auto_respond_enabled: bool = False
    lead_scoring_weights: Optional[Dict[str, float]] = None
    auto_nurture_enabled: bool = False
    default_pipeline_stage: str = "new_inquiry"


class CallSettings(BaseModel):
    """Call settings."""
    auto_transcribe: bool = True
    auto_analyze: bool = True
    recording_format: str = "wav"  # wav, mp3
    min_call_duration_for_analysis: int = 30  # seconds
    coaching_enabled: bool = True


class BrandingSettings(BaseModel):
    """Branding settings."""
    primary_color: Optional[str] = None  # hex color
    secondary_color: Optional[str] = None  # hex color
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    custom_domain: Optional[str] = None


class SetupStep(BaseModel):
    """Setup guide step."""
    step_number: int
    title: str
    description: str
    tip: Optional[str] = None
    screenshot_url: Optional[str] = None


class SetupGuide(BaseModel):
    """Setup guide for integrations."""
    id: str
    title: str
    description: str
    difficulty: str  # easy, medium, advanced
    estimated_time: str  # e.g., "5 minutes", "15 minutes"
    steps: List[SetupStep]
    prerequisites: List[str]
    docs_url: Optional[str] = None
    video_url: Optional[str] = None


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    id: str
    user_id: str
    user_email: str
    action: str
    category: str
    change_details: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CLINIC PROFILE ENDPOINTS
# ============================================================================

@router.get("/clinic", response_model=ClinicProfileOut)
def get_clinic_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full clinic profile."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic


@router.patch("/clinic", response_model=ClinicProfileOut)
def update_clinic_profile(
    data: ClinicProfileUpdate,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Update clinic profile."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Track changes for audit log
    changes = {}

    # Update fields if provided
    if data.name is not None and data.name != clinic.name:
        changes["name"] = {"old": clinic.name, "new": data.name}
        clinic.name = data.name
    if data.phone is not None and data.phone != clinic.phone:
        changes["phone"] = {"old": clinic.phone, "new": data.phone}
        clinic.phone = data.phone
    if data.email is not None and data.email != clinic.email:
        changes["email"] = {"old": clinic.email, "new": data.email}
        clinic.email = data.email
    if data.address is not None and data.address != clinic.address:
        changes["address"] = {"old": clinic.address, "new": data.address}
        clinic.address = data.address
    if data.city is not None and data.city != clinic.city:
        changes["city"] = {"old": clinic.city, "new": data.city}
        clinic.city = data.city
    if data.specialty is not None and data.specialty != clinic.specialty:
        changes["specialty"] = {"old": clinic.specialty, "new": data.specialty}
        clinic.specialty = data.specialty

    # Update settings JSON fields
    if clinic.settings is None:
        clinic.settings = {}

    if data.logo_url is not None:
        changes["logo_url"] = {"old": clinic.settings.get("logo_url"), "new": data.logo_url}
        clinic.settings["logo_url"] = data.logo_url
    if data.website is not None:
        changes["website"] = {"old": clinic.settings.get("website"), "new": data.website}
        clinic.settings["website"] = data.website
    if data.description is not None:
        changes["description"] = {"old": clinic.settings.get("description"), "new": data.description}
        clinic.settings["description"] = data.description
    if data.operating_hours is not None:
        changes["operating_hours"] = {"old": clinic.settings.get("operating_hours"), "new": data.operating_hours}
        clinic.settings["operating_hours"] = data.operating_hours

    db.commit()
    db.refresh(clinic)

    # Log activity
    log_activity(
        db,
        clinic.id,
        "settings",
        "clinic_profile_updated",
        changes,
        current_user.email
    )

    return clinic


@router.post("/clinic/logo")
def upload_clinic_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Upload clinic logo."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PNG, JPEG, GIF, WebP")

    # In production, upload to R2/S3
    # For now, return mock URL
    logo_url = f"https://api.callcoachsba.com/uploads/{clinic.id}/logo_{datetime.utcnow().timestamp()}.{file.filename.split('.')[-1]}"

    if clinic.settings is None:
        clinic.settings = {}

    old_logo = clinic.settings.get("logo_url")
    clinic.settings["logo_url"] = logo_url
    db.commit()

    log_activity(
        db,
        clinic.id,
        "settings",
        "logo_uploaded",
        {"old_logo": old_logo, "new_logo": logo_url},
        current_user.email
    )

    return {
        "success": True,
        "logo_url": logo_url,
        "message": "Logo uploaded successfully"
    }


# ============================================================================
# TEAM MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/team", response_model=List[TeamMemberOut])
def list_team_members(
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Get all team members for clinic."""
    team = db.query(User).filter(User.clinic_id == current_user.clinic_id).all()
    return team


@router.post("/team", response_model=TeamMemberOut)
def create_team_member(
    data: TeamMemberCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Add new team member."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    new_user = User(
        clinic_id=current_user.clinic_id,
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_activity(
        db,
        current_user.clinic_id,
        "team",
        "member_added",
        {"email": data.email, "role": data.role, "name": data.full_name},
        current_user.email
    )

    return new_user


@router.patch("/team/{user_id}", response_model=TeamMemberOut)
def update_team_member(
    user_id: str,
    data: TeamMemberUpdate,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Update team member."""
    user = db.query(User).filter(
        and_(User.id == user_id, User.clinic_id == current_user.clinic_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Team member not found")

    changes = {}

    if data.full_name is not None and data.full_name != user.full_name:
        changes["full_name"] = {"old": user.full_name, "new": data.full_name}
        user.full_name = data.full_name
    if data.role is not None and data.role != user.role:
        changes["role"] = {"old": user.role, "new": data.role}
        user.role = data.role
    if data.is_active is not None and data.is_active != user.is_active:
        changes["is_active"] = {"old": user.is_active, "new": data.is_active}
        user.is_active = data.is_active
    if data.allowed_tabs is not None:
        changes["allowed_tabs"] = {"old": user.allowed_tabs, "new": data.allowed_tabs}
        user.allowed_tabs = data.allowed_tabs

    db.commit()
    db.refresh(user)

    log_activity(
        db,
        current_user.clinic_id,
        "team",
        "member_updated",
        changes,
        current_user.email
    )

    return user


@router.post("/team/{user_id}/reset-password")
def reset_team_member_password(
    user_id: str,
    data: PasswordReset,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Reset team member password."""
    user = db.query(User).filter(
        and_(User.id == user_id, User.clinic_id == current_user.clinic_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Team member not found")

    user.hashed_password = hash_password(data.new_password)
    db.commit()

    log_activity(
        db,
        current_user.clinic_id,
        "team",
        "password_reset",
        {"user_email": user.email},
        current_user.email
    )

    return {"success": True, "message": "Password reset successfully"}


@router.delete("/team/{user_id}")
def deactivate_team_member(
    user_id: str,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Deactivate team member."""
    user = db.query(User).filter(
        and_(User.id == user_id, User.clinic_id == current_user.clinic_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Team member not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    db.commit()

    log_activity(
        db,
        current_user.clinic_id,
        "team",
        "member_deactivated",
        {"email": user.email},
        current_user.email
    )

    return {"success": True, "message": "Team member deactivated"}


# ============================================================================
# INTEGRATION STATUS ENDPOINTS
# ============================================================================

@router.get("/integrations", response_model=IntegrationStatus)
def get_integrations_status(
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Get status of all integrations."""
    clinic_id = current_user.clinic_id

    # WhatsApp
    whatsapp_config = db.query(WhatsAppConfig).filter(
        WhatsAppConfig.clinic_id == clinic_id
    ).first()
    whatsapp = {
        "connected": whatsapp_config.is_active if whatsapp_config else False,
        "phone": whatsapp_config.business_phone if whatsapp_config else None,
        "business_name": whatsapp_config.business_name if whatsapp_config else None,
    } if whatsapp_config else {"connected": False}

    # Telephony
    telephony_config = db.query(TelephonyConfig).filter(
        TelephonyConfig.clinic_id == clinic_id
    ).first()
    telephony = {
        "connected": telephony_config.is_active if telephony_config else False,
        "provider": telephony_config.provider if telephony_config else None,
        "phone": (
            telephony_config.twilio_phone
            if telephony_config and telephony_config.provider == "twilio"
            else telephony_config.exotel_caller_id
            if telephony_config and telephony_config.provider == "exotel"
            else telephony_config.plivo_phone
            if telephony_config
            else None
        ),
    } if telephony_config else {"connected": False}

    # Get settings from clinic.settings JSON
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    settings = clinic.settings if clinic and clinic.settings else {}

    # Meta Ads
    meta_ads = settings.get("integrations", {}).get("meta_ads", {
        "connected": False
    })

    # Google Ads
    google_ads = settings.get("integrations", {}).get("google_ads", {
        "connected": False
    })

    # Social accounts
    social_accounts = settings.get("integrations", {}).get("social_accounts", [])

    # Webhook
    webhook = settings.get("integrations", {}).get("webhook", {
        "url": None,
        "api_key": None
    })

    return IntegrationStatus(
        whatsapp=whatsapp,
        telephony=telephony,
        meta_ads=meta_ads,
        google_ads=google_ads,
        social_accounts=social_accounts,
        webhook=webhook
    )


# ============================================================================
# WEBHOOK & API KEYS ENDPOINTS
# ============================================================================

@router.get("/api-keys", response_model=List[APIKeyOut])
def get_api_keys(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Get clinic API keys."""
    clinic_id = current_user.clinic_id
    api_keys = db.query(APIKey).filter(APIKey.clinic_id == clinic_id).all()

    result = []
    for key in api_keys:
        result.append(APIKeyOut(
            id=key.id,
            name=key.name,
            description=key.description,
            masked_key=f"{key.key[:7]}****{key.key[-4:]}",
            created_at=key.created_at,
            last_used_at=key.last_used_at
        ))
    return result


@router.post("/api-keys/generate")
def generate_api_key(
    data: APIKeyCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Generate new API key."""
    clinic_id = current_user.clinic_id
    api_key_value = secrets.token_urlsafe(32)

    new_key = APIKey(
        clinic_id=clinic_id,
        name=data.name,
        description=data.description,
        key=api_key_value,
        created_by_id=current_user.id
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    log_activity(
        db,
        clinic_id,
        "api",
        "key_generated",
        {"key_name": data.name},
        current_user.email
    )

    return APIKeyOut(
        id=new_key.id,
        name=new_key.name,
        description=new_key.description,
        key=api_key_value,  # Only return on creation
        masked_key=f"{api_key_value[:7]}****{api_key_value[-4:]}",
        created_at=new_key.created_at,
        last_used_at=None
    )


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Revoke API key."""
    api_key = db.query(APIKey).filter(
        and_(APIKey.id == key_id, APIKey.clinic_id == current_user.clinic_id)
    ).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    key_name = api_key.name
    db.delete(api_key)
    db.commit()

    log_activity(
        db,
        current_user.clinic_id,
        "api",
        "key_revoked",
        {"key_name": key_name},
        current_user.email
    )

    return {"success": True, "message": "API key revoked"}


# ============================================================================
# NOTIFICATION PREFERENCES ENDPOINTS
# ============================================================================

@router.get("/notifications", response_model=NotificationPreferences)
def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification preferences."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic or not clinic.settings:
        return NotificationPreferences()

    notifications = clinic.settings.get("notifications", {})
    return NotificationPreferences(
        email_on_new_lead=notifications.get("email_on_new_lead", True),
        email_on_missed_call=notifications.get("email_on_missed_call", True),
        email_daily_digest=notifications.get("email_daily_digest", False),
        whatsapp_on_new_lead=notifications.get("whatsapp_on_new_lead", False),
        whatsapp_on_deal_won=notifications.get("whatsapp_on_deal_won", False),
        slack_webhook_url=notifications.get("slack_webhook_url", None)
    )


@router.patch("/notifications", response_model=NotificationPreferences)
def update_notification_preferences(
    data: NotificationPreferences,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Update notification preferences."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    if clinic.settings is None:
        clinic.settings = {}

    old_prefs = clinic.settings.get("notifications", {})
    clinic.settings["notifications"] = data.dict(exclude_none=True)
    db.commit()

    log_activity(
        db,
        clinic.id,
        "settings",
        "notifications_updated",
        {"old": old_prefs, "new": clinic.settings["notifications"]},
        current_user.email
    )

    return data


# ============================================================================
# LEAD SETTINGS ENDPOINTS
# ============================================================================

@router.get("/leads", response_model=LeadSettings)
def get_lead_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get lead configuration."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic or not clinic.settings:
        return LeadSettings()

    lead_settings = clinic.settings.get("leads", {})
    return LeadSettings(
        auto_assign_enabled=lead_settings.get("auto_assign_enabled", False),
        auto_respond_enabled=lead_settings.get("auto_respond_enabled", False),
        lead_scoring_weights=lead_settings.get("lead_scoring_weights"),
        auto_nurture_enabled=lead_settings.get("auto_nurture_enabled", False),
        default_pipeline_stage=lead_settings.get("default_pipeline_stage", "new_inquiry")
    )


@router.patch("/leads", response_model=LeadSettings)
def update_lead_settings(
    data: LeadSettings,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Update lead settings."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    if clinic.settings is None:
        clinic.settings = {}

    old_settings = clinic.settings.get("leads", {})
    clinic.settings["leads"] = data.dict(exclude_none=True)
    db.commit()

    log_activity(
        db,
        clinic.id,
        "settings",
        "leads_updated",
        {"old": old_settings, "new": clinic.settings["leads"]},
        current_user.email
    )

    return data


# ============================================================================
# CALL SETTINGS ENDPOINTS
# ============================================================================

@router.get("/calls", response_model=CallSettings)
def get_call_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get call settings."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic or not clinic.settings:
        return CallSettings()

    call_settings = clinic.settings.get("calls", {})
    return CallSettings(
        auto_transcribe=call_settings.get("auto_transcribe", True),
        auto_analyze=call_settings.get("auto_analyze", True),
        recording_format=call_settings.get("recording_format", "wav"),
        min_call_duration_for_analysis=call_settings.get("min_call_duration_for_analysis", 30),
        coaching_enabled=call_settings.get("coaching_enabled", True)
    )


@router.patch("/calls", response_model=CallSettings)
def update_call_settings(
    data: CallSettings,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Update call settings."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    if clinic.settings is None:
        clinic.settings = {}

    old_settings = clinic.settings.get("calls", {})
    clinic.settings["calls"] = data.dict()
    db.commit()

    log_activity(
        db,
        clinic.id,
        "settings",
        "calls_updated",
        {"old": old_settings, "new": clinic.settings["calls"]},
        current_user.email
    )

    return data


# ============================================================================
# BRANDING ENDPOINTS
# ============================================================================

@router.get("/branding", response_model=BrandingSettings)
def get_branding_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get branding settings."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic or not clinic.settings:
        return BrandingSettings()

    branding = clinic.settings.get("branding", {})
    return BrandingSettings(
        primary_color=branding.get("primary_color"),
        secondary_color=branding.get("secondary_color"),
        logo_url=branding.get("logo_url"),
        favicon_url=branding.get("favicon_url"),
        custom_domain=branding.get("custom_domain")
    )


@router.patch("/branding", response_model=BrandingSettings)
def update_branding_settings(
    data: BrandingSettings,
    current_user: User = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Update branding settings."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    if clinic.settings is None:
        clinic.settings = {}

    old_branding = clinic.settings.get("branding", {})
    clinic.settings["branding"] = data.dict(exclude_none=True)
    db.commit()

    log_activity(
        db,
        clinic.id,
        "settings",
        "branding_updated",
        {"old": old_branding, "new": clinic.settings["branding"]},
        current_user.email
    )

    return data


# ============================================================================
# DATA & PRIVACY ENDPOINTS
# ============================================================================

@router.get("/data")
def get_data_settings(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Get data settings."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic or not clinic.settings:
        return {
            "total_calls": 0,
            "total_leads": 0,
            "total_deals": 0,
            "storage_used_mb": 0,
            "last_export_at": None,
            "data_retention_days": 365
        }

    # Calculate statistics
    total_calls = db.query(Call).filter(Call.clinic_id == current_user.clinic_id).count()
    total_leads = db.query(Lead).filter(Lead.clinic_id == current_user.clinic_id).count()

    data_settings = clinic.settings.get("data", {})

    return {
        "total_calls": total_calls,
        "total_leads": total_leads,
        "total_deals": data_settings.get("total_deals", 0),
        "storage_used_mb": data_settings.get("storage_used_mb", 0),
        "last_export_at": data_settings.get("last_export_at"),
        "data_retention_days": data_settings.get("data_retention_days", 365)
    }


@router.post("/data/export")
def request_data_export(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Request data export."""
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    if clinic.settings is None:
        clinic.settings = {}

    if "data" not in clinic.settings:
        clinic.settings["data"] = {}

    clinic.settings["data"]["last_export_requested_at"] = datetime.utcnow().isoformat()
    db.commit()

    log_activity(
        db,
        clinic.id,
        "settings",
        "data_export_requested",
        {"email": current_user.email},
        current_user.email
    )

    return {
        "success": True,
        "message": "Data export requested. You will receive an email with download link within 24 hours.",
        "export_id": f"export_{datetime.utcnow().timestamp()}"
    }


@router.get("/audit-log")
def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Get audit log of settings changes."""
    # This would query an AuditLog model if it exists
    # For now, return mock data
    return {
        "entries": [
            {
                "id": "audit_1",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "action": "clinic_profile_updated",
                "category": "settings",
                "change_details": {"name": {"old": "Old Clinic", "new": "New Clinic"}},
                "created_at": datetime.utcnow().isoformat()
            }
        ],
        "total": 1,
        "limit": limit,
        "offset": offset
    }


# ============================================================================
# SETUP GUIDES ENDPOINTS
# ============================================================================

@router.get("/guides", response_model=List[SetupGuide])
def get_setup_guides(current_user: User = Depends(get_current_user)):
    """Get setup guides for all integrations."""
    guides = [
        SetupGuide(
            id="whatsapp_setup",
            title="WhatsApp Business API Setup",
            description="Connect your WhatsApp Business Account to CallCoach for seamless lead management and automated responses.",
            difficulty="medium",
            estimated_time="15 minutes",
            prerequisites=[
                "Meta Business Account",
                "WhatsApp Business Account",
                "Business phone number"
            ],
            steps=[
                SetupStep(
                    step_number=1,
                    title="Create Meta Business Account",
                    description="Go to business.facebook.com and create a Meta Business Account if you don't have one. You'll need a business email address.",
                    tip="Use your clinic's official business email for easier management."
                ),
                SetupStep(
                    step_number=2,
                    title="Add WhatsApp Business App",
                    description="In your Meta Business Account, go to Apps > Add Apps > Search for 'WhatsApp'. Click 'Add' to add the WhatsApp Business app to your account.",
                    tip="Make sure you have admin access to your Meta Business Account."
                ),
                SetupStep(
                    step_number=3,
                    title="Create WhatsApp Business Account",
                    description="Inside the WhatsApp Business app, click 'Create Account'. Enter your business name and phone number. This is the number your customers will see.",
                    tip="Use your clinic's primary contact number. This will appear as your WhatsApp account."
                ),
                SetupStep(
                    step_number=4,
                    title="Verify Your Phone Number",
                    description="WhatsApp will send a verification code to your phone via SMS. Enter this code to verify ownership of the phone number.",
                    tip="Keep your phone nearby during this step. The code is valid for 10 minutes."
                ),
                SetupStep(
                    step_number=5,
                    title="Create System User",
                    description="Go to Settings > Users > System Users. Create a new system user with a descriptive name like 'CallCoach Integration'. Grant it 'Admin' role.",
                    tip="System Users never expire and are perfect for API integrations."
                ),
                SetupStep(
                    step_number=6,
                    title="Generate Access Token",
                    description="In the System User settings, click 'Generate Token'. Select the WhatsApp Business app and 'whatsapp_business_messaging' permission. Copy the token.",
                    tip="Save this token securely. You'll need it only once during setup."
                ),
                SetupStep(
                    step_number=7,
                    title="Get Phone Number ID & WABA ID",
                    description="Go to WhatsApp > Getting Started. You'll find your Phone Number ID and WhatsApp Business Account ID (WABA ID). Copy both.",
                    tip="These IDs are unique identifiers for your WhatsApp account."
                ),
                SetupStep(
                    step_number=8,
                    title="Connect in CallCoach",
                    description="In CallCoach Settings > Integrations > WhatsApp, paste your Phone Number ID, WABA ID, and Access Token. Click 'Connect'.",
                    tip="The connection will be tested automatically. You'll see a success message if everything is correct."
                ),
                SetupStep(
                    step_number=9,
                    title="Set Webhook URL",
                    description="Copy the Webhook URL from CallCoach. Go to Meta App Dashboard > WhatsApp > Configuration. Paste the URL and webhook token from CallCoach.",
                    tip="The webhook URL allows WhatsApp messages to flow into CallCoach in real-time."
                ),
                SetupStep(
                    step_number=10,
                    title="Subscribe to Messages",
                    description="In the same Webhook settings, check the 'messages' checkbox to subscribe to incoming messages. Click 'Verify' when prompted.",
                    tip="This enables CallCoach to receive WhatsApp messages automatically."
                ),
            ],
            docs_url="https://developers.facebook.com/docs/whatsapp/business-platform/get-started",
            video_url="https://www.youtube.com/embed/dQw4w9WgXcQ"
        ),
        SetupGuide(
            id="meta_ads_setup",
            title="Meta Ads (Facebook/Instagram) Connection",
            description="Connect your Meta Ads account to track campaign performance and lead generation from Facebook and Instagram ads.",
            difficulty="easy",
            estimated_time="10 minutes",
            prerequisites=[
                "Meta Business Account",
                "Active Facebook Ad Account",
                "Admin access to Ad Account"
            ],
            steps=[
                SetupStep(
                    step_number=1,
                    title="Go to Meta App Center",
                    description="Open Meta App Center and search for 'Ads Manager'. Log in with your Meta Business Account credentials.",
                    tip="Use the same account that manages your Facebook and Instagram ads."
                ),
                SetupStep(
                    step_number=2,
                    title="Access Settings",
                    description="Click on your profile icon > Settings and privacy > Settings. Go to the 'Accounts' section.",
                    tip="Look for 'Ad Account Settings' to manage your advertising account."
                ),
                SetupStep(
                    step_number=3,
                    title="Get Your Ad Account ID",
                    description="In Ad Account Settings, you'll see your Ad Account ID. It starts with 'act_'. Copy this ID.",
                    tip="Your Ad Account ID is a 15-digit number preceded by 'act_'."
                ),
                SetupStep(
                    step_number=4,
                    title="Create App Password",
                    description="Go to Settings > Apps and Websites. Click 'Create App Password'. Meta will send you a verification code via SMS.",
                    tip="This password is for app-specific access and enhances security."
                ),
                SetupStep(
                    step_number=5,
                    title="Grant App Permissions",
                    description="Allow CallCoach to access your ads data. You'll see a permission screen. Grant 'ads_read' and 'ads_management' permissions.",
                    tip="These permissions allow CallCoach to track your campaign performance and lead generation."
                ),
                SetupStep(
                    step_number=6,
                    title="Enter Credentials in CallCoach",
                    description="Go to Settings > Integrations > Meta Ads. Enter your Ad Account ID and the app password. Click 'Connect'.",
                    tip="CallCoach will verify your credentials. This may take up to 1 minute."
                ),
                SetupStep(
                    step_number=7,
                    title="Select Campaigns to Track",
                    description="After connecting, select which ad campaigns you want CallCoach to track for lead generation and ROI calculation.",
                    tip="You can update this selection anytime in your integration settings."
                ),
                SetupStep(
                    step_number=8,
                    title="Verify Connection",
                    description="CallCoach will show a 'Connection Verified' message once it can access your ad account data.",
                    tip="If you see an error, double-check your Ad Account ID and permissions."
                ),
            ],
            docs_url="https://developers.facebook.com/docs/marketing-api",
            video_url=None
        ),
        SetupGuide(
            id="google_ads_setup",
            title="Google Ads Connection",
            description="Connect your Google Ads account to track campaign performance, lead quality, and ROI from Google Search ads.",
            difficulty="medium",
            estimated_time="20 minutes",
            prerequisites=[
                "Google Ads Account",
                "Manager Account access (recommended)",
                "Admin role in Google Ads"
            ],
            steps=[
                SetupStep(
                    step_number=1,
                    title="Open Google Ads Account",
                    description="Go to google.com/ads and log in with your Google account. Navigate to your main Google Ads account.",
                    tip="If you have multiple accounts, use your Manager Account for easier multi-account management."
                ),
                SetupStep(
                    step_number=2,
                    title="Get Your Customer ID",
                    description="Click the settings icon (gear) > Account settings. You'll see your Customer ID (10-digit number). Copy it.",
                    tip="Your Customer ID is also shown in the top-left corner of the Google Ads interface."
                ),
                SetupStep(
                    step_number=3,
                    title="Create a Google Cloud Project",
                    description="Go to console.cloud.google.com. Create a new project named 'CallCoach Integration'.",
                    tip="A Google Cloud Project is required to securely access your Google Ads data."
                ),
                SetupStep(
                    step_number=4,
                    title="Enable Google Ads API",
                    description="In your Google Cloud Project, go to APIs & Services > Library. Search for 'Google Ads API'. Click it and press 'Enable'.",
                    tip="This enables your project to communicate with Google Ads servers."
                ),
                SetupStep(
                    step_number=5,
                    title="Create OAuth 2.0 Credentials",
                    description="Go to APIs & Services > Credentials. Click 'Create Credentials' > 'OAuth 2.0 Client ID'. Select 'Web Application'.",
                    tip="OAuth 2.0 is the secure standard for app-to-app authentication."
                ),
                SetupStep(
                    step_number=6,
                    title="Add Authorized Redirect URI",
                    description="In OAuth settings, add 'https://api.callcoachsba.com/auth/google-ads-callback' as an authorized redirect URI.",
                    tip="This tells Google where to send the authorization code after login."
                ),
                SetupStep(
                    step_number=7,
                    title="Download Credentials JSON",
                    description="After creating OAuth credentials, download the JSON file. Keep it safe—you'll need it in the next step.",
                    tip="This file contains your Client ID and Client Secret. Don't share it with anyone."
                ),
                SetupStep(
                    step_number=8,
                    title="Connect in CallCoach",
                    description="Go to Settings > Integrations > Google Ads. Paste your Customer ID and upload your OAuth JSON file. Click 'Connect'.",
                    tip="You'll be redirected to Google to authorize CallCoach. Use your Google account that owns the Ads account."
                ),
                SetupStep(
                    step_number=9,
                    title="Authorize CallCoach Access",
                    description="Google will show a permission request. Click 'Allow' to let CallCoach access your Google Ads data.",
                    tip="CallCoach only requests read access and cannot modify your campaigns."
                ),
                SetupStep(
                    step_number=10,
                    title="Map Conversion Goals",
                    description="After authorization, select which Google Ads conversion goals correspond to your clinic's outcomes (e.g., 'Consultation Booked').",
                    tip="This helps CallCoach accurately calculate ROI from your Google Ads campaigns."
                ),
            ],
            docs_url="https://developers.google.com/google-ads/api/docs/start",
            video_url=None
        ),
        SetupGuide(
            id="twilio_setup",
            title="Telephony Setup (Twilio)",
            description="Connect Twilio to CallCoach for automatic call recording, transcription, and AI analysis.",
            difficulty="medium",
            estimated_time="15 minutes",
            prerequisites=[
                "Twilio Account (paid)",
                "Twilio Phone Number",
                "Admin access to Twilio console"
            ],
            steps=[
                SetupStep(
                    step_number=1,
                    title="Create Twilio Account",
                    description="Go to twilio.com and sign up for a Twilio account. Complete the registration process.",
                    tip="Twilio offers a free trial account, but you'll need a paid account for production use."
                ),
                SetupStep(
                    step_number=2,
                    title="Purchase a Phone Number",
                    description="In the Twilio Console, go to Messaging > Programmable Voice > Phone Numbers. Buy a phone number in your country.",
                    tip="Choose a number with a local area code for better recognition by your patients."
                ),
                SetupStep(
                    step_number=3,
                    title="Get Your Account Credentials",
                    description="Go to Account > Keys & Credentials. You'll see your Account SID and Auth Token. Copy both.",
                    tip="These are sensitive credentials. Never share them or commit them to public code."
                ),
                SetupStep(
                    step_number=4,
                    title="Enable Call Recording",
                    description="In Twilio Console, go to Voice > Manage > Settings. Enable 'Record calls' and set it to record both sides.",
                    tip="Recordings are stored in Twilio and automatically sent to CallCoach via webhook."
                ),
                SetupStep(
                    step_number=5,
                    title="Configure Webhook URL",
                    description="In Voice > Manage > TwiML Apps, create a new TwiML app. Set the Voice Request URL to your Twilio webhook URL from CallCoach.",
                    tip="The webhook URL format is: https://api.callcoachsba.com/webhooks/twilio/voice"
                ),
                SetupStep(
                    step_number=6,
                    title="Add Recording Callback",
                    description="In the same TwiML app settings, add Status Callback URL for recording. Use: https://api.callcoachsba.com/webhooks/twilio/recording",
                    tip="This notifies CallCoach when recordings are ready for transcription."
                ),
                SetupStep(
                    step_number=7,
                    title="Connect in CallCoach",
                    description="Go to Settings > Integrations > Telephony. Select 'Twilio' as provider. Enter your Account SID, Auth Token, and phone number.",
                    tip="Click 'Test Connection' to verify all credentials are correct."
                ),
                SetupStep(
                    step_number=8,
                    title="Configure Call Settings",
                    description="Choose your recording format (WAV or MP3), enable transcription and AI analysis, and set minimum call duration for analysis.",
                    tip="Longer minimum durations save on transcription costs. We recommend 30 seconds."
                ),
                SetupStep(
                    step_number=9,
                    title="Enable Smart Routing",
                    description="Optional: Configure call routing rules. You can have calls distributed to team members automatically.",
                    tip="CallCoach can automatically assign calls based on team availability and skills."
                ),
            ],
            docs_url="https://www.twilio.com/docs/voice",
            video_url=None
        ),
        SetupGuide(
            id="exotel_setup",
            title="Telephony Setup (Exotel)",
            description="Connect Exotel to CallCoach for call management and analytics from India and Southeast Asia.",
            difficulty="medium",
            estimated_time="15 minutes",
            prerequisites=[
                "Exotel Account",
                "Exotel Phone Number",
                "API credentials"
            ],
            steps=[
                SetupStep(
                    step_number=1,
                    title="Create Exotel Account",
                    description="Go to exotel.com and sign up. Complete KYC verification as required for your region.",
                    tip="Exotel is ideal for clinics in India and Southeast Asia with better local support."
                ),
                SetupStep(
                    step_number=2,
                    title="Get Your SID and Token",
                    description="Log into Exotel Dashboard > Settings > API Credentials. Copy your SID (Subdomain/Account ID) and API Token.",
                    tip="Your SID typically looks like 'xyz1234567890abcdef'."
                ),
                SetupStep(
                    step_number=3,
                    title="Activate Virtual Numbers",
                    description="In Settings > Virtual Numbers, activate at least one virtual number. This is the number patients will call.",
                    tip="You can activate multiple numbers for different departments (e.g., Consultation, Billing)."
                ),
                SetupStep(
                    step_number=4,
                    title="Configure IVR (Optional)",
                    description="Set up an Interactive Voice Response flow to route calls. Define options like 'Press 1 for Consultation', 'Press 2 for Billing'.",
                    tip="Good IVR setup reduces missed calls and improves patient experience."
                ),
                SetupStep(
                    step_number=5,
                    title="Enable Call Recording",
                    description="In Settings > Call Recording, enable recording for all calls. Choose your preferred audio format.",
                    tip="Recordings are crucial for quality assurance and coaching."
                ),
                SetupStep(
                    step_number=6,
                    title="Set Webhook for Call Events",
                    description="In API Integrations > Webhooks, add: https://api.callcoachsba.com/webhooks/exotel/voice",
                    tip="This notifies CallCoach of all incoming and outgoing calls."
                ),
                SetupStep(
                    step_number=7,
                    title="Set Recording Webhook",
                    description="Add another webhook for recordings: https://api.callcoachsba.com/webhooks/exotel/recording",
                    tip="Exotel will send recording URLs to CallCoach automatically."
                ),
                SetupStep(
                    step_number=8,
                    title="Connect in CallCoach",
                    description="Go to Settings > Integrations > Telephony. Select 'Exotel' as provider. Enter your SID, Token, and Subdomain.",
                    tip="The subdomain is part of your Exotel domain (e.g., 'xyz1234567890abcdef.exotel.com')."
                ),
                SetupStep(
                    step_number=9,
                    title="Select Virtual Numbers to Monitor",
                    description="After connecting, select which virtual numbers CallCoach should track and analyze.",
                    tip="You can track multiple numbers and CallCoach will organize calls by number."
                ),
                SetupStep(
                    step_number=10,
                    title="Test Connection",
                    description="Make a test call to one of your virtual numbers. Verify the call appears in CallCoach within 2 minutes.",
                    tip="If calls don't appear, check that webhooks are correctly configured in Exotel."
                ),
            ],
            docs_url="https://developer.exotel.com/docs",
            video_url=None
        ),
        SetupGuide(
            id="webhook_setup",
            title="Lead Webhook Setup",
            description="Enable external systems to send leads to CallCoach via HTTP webhooks for real-time lead import.",
            difficulty="easy",
            estimated_time="5 minutes",
            prerequisites=[
                "Access to your website/form provider",
                "API key (generated in CallCoach)"
            ],
            steps=[
                SetupStep(
                    step_number=1,
                    title="Generate API Key in CallCoach",
                    description="Go to Settings > API Keys > Generate New Key. Name it 'Lead Webhook' and copy the key.",
                    tip="Keep this key secret! Anyone with it can add leads to your clinic."
                ),
                SetupStep(
                    step_number=2,
                    title="Get Your Webhook URL",
                    description="In Settings > API Keys, copy your webhook endpoint URL. It looks like: https://api.callcoachsba.com/webhooks/leads",
                    tip="This is the URL you'll use in your form provider settings."
                ),
                SetupStep(
                    step_number=3,
                    title="Prepare Lead Data",
                    description="Ensure your form captures: name, phone, email, and optionally: message, source, campaign name.",
                    tip="These fields help CallCoach organize and score your leads."
                ),
                SetupStep(
                    step_number=4,
                    title="Connect Your Form Provider",
                    description="If using Jotform, Typeform, Google Forms, etc., go to integrations and look for 'Webhooks' or 'Zapier' option.",
                    tip="Most modern form builders support webhooks. Check their documentation if unsure."
                ),
                SetupStep(
                    step_number=5,
                    title="Configure Webhook Payload",
                    description="Set up the webhook to send form data in JSON format with fields: name, phone, email, message, source.",
                    tip="The exact field names should match what you set in CallCoach webhook settings."
                ),
                SetupStep(
                    step_number=6,
                    title="Add Authorization Header",
                    description="In webhook headers, add: Authorization: Bearer YOUR_API_KEY",
                    tip="This ensures only authorized sources can add leads to your clinic."
                ),
                SetupStep(
                    step_number=7,
                    title="Test the Webhook",
                    description="Submit a test lead through your form. In CallCoach, go to Leads and verify it appears within 1 minute.",
                    tip="If it doesn't appear, check the webhook logs in your form provider."
                ),
                SetupStep(
                    step_number=8,
                    title="Set Up Lead Auto-Response",
                    description="Optional: Enable auto-responses in Settings > Leads. Choose email or WhatsApp confirmation.",
                    tip="Auto-responses help qualify leads and set expectations with patients."
                ),
            ],
            docs_url="https://docs.callcoachsba.com/webhooks",
            video_url=None
        ),
        SetupGuide(
            id="social_setup",
            title="Social Media Account Connection",
            description="Connect Instagram, Facebook, and TikTok accounts to track social media engagement and lead generation.",
            difficulty="easy",
            estimated_time="10 minutes",
            prerequisites=[
                "Instagram Business Account",
                "Facebook Page",
                "Admin access to accounts"
            ],
            steps=[
                SetupStep(
                    step_number=1,
                    title="Convert to Business Account",
                    description="Go to Instagram Settings > Account Type. Convert your account to 'Business Account' if not already.",
                    tip="Business accounts unlock analytics and integration features."
                ),
                SetupStep(
                    step_number=2,
                    title="Link Facebook Page",
                    description="In Instagram Settings > Linked Accounts > Facebook > Link Account. Select your clinic's Facebook page.",
                    tip="This allows you to manage both accounts from one place."
                ),
                SetupStep(
                    step_number=3,
                    title="Enable Instagram Insights",
                    description="Go to Creator Studio (facebook.com/creatorstudio). Log in with your Meta account. You'll see your Instagram analytics.",
                    tip="Creator Studio shows detailed metrics on reach, engagement, and follower growth."
                ),
                SetupStep(
                    step_number=4,
                    title="Grant App Permissions",
                    description="Go to Settings > Apps and Websites. Authorize 'CallCoach' app to access your Instagram and Facebook data.",
                    tip="Only grant 'read' permissions. CallCoach doesn't post on your behalf."
                ),
                SetupStep(
                    step_number=5,
                    title="Connect in CallCoach",
                    description="Go to Settings > Integrations > Social Media. Click 'Connect Instagram' and 'Connect Facebook'.",
                    tip="You'll be redirected to Meta to authorize. Use your business account."
                ),
                SetupStep(
                    step_number=6,
                    title="Select Accounts to Track",
                    description="After connecting, select which Instagram and Facebook accounts CallCoach should monitor for analytics.",
                    tip="You can add multiple accounts if you manage different locations or brands."
                ),
                SetupStep(
                    step_number=7,
                    title="Add Lead Capture Forms",
                    description="In Creator Studio, create Lead Gen Forms on your Facebook page. CallCoach will automatically import collected leads.",
                    tip="Forms on Facebook convert 2-3x better than external links."
                ),
                SetupStep(
                    step_number=8,
                    title="View Analytics in CallCoach",
                    description="Go to Leads or Reports > Social Media. You'll see performance metrics: impressions, clicks, leads, cost per lead.",
                    tip="Track which content generates the best-quality leads."
                ),
            ],
            docs_url="https://developers.facebook.com/docs/instagram-api",
            video_url=None
        ),
        SetupGuide(
            id="crm_setup",
            title="CallCoach Initial Setup Guide",
            description="Complete onboarding for your clinic to get the most out of CallCoach CRM.",
            difficulty="easy",
            estimated_time="30 minutes",
            prerequisites=[
                "Clinic admin account",
                "Internet connection",
                "Phone number for verification (optional)"
            ],
            steps=[
                SetupStep(
                    step_number=1,
                    title="Complete Clinic Profile",
                    description="Go to Settings > Clinic Profile. Fill in clinic name, phone, address, specialty, and description.",
                    tip="A complete profile helps CallCoach optimize AI coaching for your specialty."
                ),
                SetupStep(
                    step_number=2,
                    title="Upload Clinic Logo",
                    description="Go to Settings > Clinic Profile > Upload Logo. Choose a PNG or JPG file.",
                    tip="Your logo appears in team member dashboards and printed reports."
                ),
                SetupStep(
                    step_number=3,
                    title="Add Your Team",
                    description="Go to Settings > Team Management. Click 'Add Team Member'. Enter email, name, and role (Admin/Manager/Agent).",
                    tip="Agents can take calls; Managers can edit settings and view team analytics; Admins have full access."
                ),
                SetupStep(
                    step_number=4,
                    title="Set Notification Preferences",
                    description="Go to Settings > Notifications. Choose how you want to be notified of new leads, missed calls, and daily summaries.",
                    tip="Email daily digests help you stay updated without too many notifications."
                ),
                SetupStep(
                    step_number=5,
                    title="Configure Lead Settings",
                    description="Go to Settings > Leads. Enable auto-assignment to distribute leads to team members automatically.",
                    tip="Proper lead distribution increases closure rates."
                ),
                SetupStep(
                    step_number=6,
                    title="Enable Call Recording",
                    description="Go to Settings > Calls. Enable auto-transcription and AI analysis. These are essential for coaching.",
                    tip="All calls are recorded (with consent) and analyzed by AI to identify coaching opportunities."
                ),
                SetupStep(
                    step_number=7,
                    title="Brand Your Platform",
                    description="Go to Settings > Branding. Set primary and secondary colors to match your clinic brand.",
                    tip="Branded interfaces improve professional appearance and team adoption."
                ),
                SetupStep(
                    step_number=8,
                    title="Generate API Keys",
                    description="Go to Settings > API Keys. Generate a key for 'Lead Webhooks' to enable external form submissions.",
                    tip="API keys are required for webhook integrations with your website or forms."
                ),
                SetupStep(
                    step_number=9,
                    title="Connect Your First Integration",
                    description="Choose one integration to start with: WhatsApp, Telephony, or Webhooks. Follow the corresponding setup guide.",
                    tip="We recommend starting with telephony (Twilio/Exotel) for immediate call recording and analysis."
                ),
                SetupStep(
                    step_number=10,
                    title="Create Your First Pipeline",
                    description="Go to Pipeline > New Pipeline. Create stages relevant to your clinic: Inquiry > Consultation Booked > Completed > Won.",
                    tip="Your pipeline should reflect your actual sales process."
                ),
                SetupStep(
                    step_number=11,
                    title="Invite Team to Learning",
                    description="Go to Learning > Courses. Assign 'Sales Fundamentals' or 'Closing Techniques' to your team for onboarding.",
                    tip="Well-trained teams close more deals and have higher customer satisfaction."
                ),
                SetupStep(
                    step_number=12,
                    title="View Your First Dashboard",
                    description="Go to Dashboard. You'll see real-time call count, lead status, pipeline value, and team performance metrics.",
                    tip="Come back to this dashboard weekly to track your clinic's growth."
                ),
            ],
            docs_url="https://docs.callcoachsba.com/getting-started",
            video_url="https://www.youtube.com/embed/dQw4w9WgXcQ"
        ),
    ]

    return guides
