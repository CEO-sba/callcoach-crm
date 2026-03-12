"""
CallCoach CRM - Lead Distribution Router
Handles lead distribution rules and automatic/manual lead assignments.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import User
from app.models_whatsapp import Lead
from app.models_distribution import LeadDistributionRule, LeadDistributionLog
from app.services import lead_distributor
from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/distribution", tags=["distribution"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

from pydantic import BaseModel, Field
from typing import Dict, Any


class AgentAssignment(BaseModel):
    """Single agent assignment with percentage"""
    agent_id: str
    percentage: int = Field(..., ge=0, le=100)


class DistributionRuleCreate(BaseModel):
    """Create/update distribution rules for a channel"""
    channel: str
    assignments: List[AgentAssignment]


class DistributionRuleOut(BaseModel):
    """Distribution rule response"""
    id: str
    clinic_id: str
    channel: str
    agent_id: str
    agent_name: Optional[str] = None
    percentage: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChannelStatus(BaseModel):
    """Status of distribution rules for a channel"""
    channel: str
    has_rules: bool
    total_percentage: int
    agent_count: int
    assignments: List[Dict[str, Any]]


class LeadAssignmentOut(BaseModel):
    """Lead assignment response"""
    lead_id: str
    agent_id: str
    agent_name: Optional[str] = None
    method: str
    created_at: datetime


class LeadOut(BaseModel):
    """Lead response with assignment info"""
    id: str
    clinic_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: str
    campaign_name: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    status: str
    lead_score: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DistributionStats(BaseModel):
    """Distribution statistics"""
    days: int
    cutoff_date: datetime
    stats_by_channel: Dict[str, Dict[str, Any]]


# ============================================================================
# Rule Management Endpoints (Admin/Manager only)
# ============================================================================

@router.get("/rules", dependencies=[Depends(require_role(["admin", "manager"]))])
async def get_all_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all distribution rules for the clinic, grouped by channel.
    Admin/Manager only.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Super admins cannot manage clinic-specific rules")

    rules = db.query(LeadDistributionRule).filter(
        LeadDistributionRule.clinic_id == clinic_id
    ).all()

    # Group by channel
    grouped = {}
    for rule in rules:
        if rule.channel not in grouped:
            grouped[rule.channel] = []

        agent = db.query(User).filter(User.id == rule.agent_id).first()
        grouped[rule.channel].append({
            "id": rule.id,
            "agent_id": rule.agent_id,
            "agent_name": agent.full_name if agent else "Unknown",
            "percentage": rule.percentage,
            "is_active": rule.is_active,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
        })

    return {
        "clinic_id": clinic_id,
        "rules_by_channel": grouped,
    }


@router.post("/rules", dependencies=[Depends(require_role(["admin", "manager"]))])
async def set_rules(
    payload: DistributionRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Set distribution rules for a specific channel.
    Validates percentages sum to 100.
    Replaces all existing rules for that channel.
    Admin/Manager only.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Super admins cannot manage clinic-specific rules")

    # Validate percentages
    try:
        lead_distributor.validate_percentage_distribution(
            [{"percentage": a.percentage} for a in payload.assignments]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate channel
    valid_channels = lead_distributor.get_available_channels()
    if payload.channel not in valid_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel '{payload.channel}'. Valid channels: {', '.join(valid_channels)}"
        )

    # Validate agents exist and belong to clinic
    for assignment in payload.assignments:
        agent = db.query(User).filter(
            and_(
                User.id == assignment.agent_id,
                User.clinic_id == clinic_id,
                User.is_active == True,
            )
        ).first()
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent {assignment.agent_id} not found or inactive"
            )

    # Delete existing rules for this channel
    db.query(LeadDistributionRule).filter(
        and_(
            LeadDistributionRule.clinic_id == clinic_id,
            LeadDistributionRule.channel == payload.channel,
        )
    ).delete()

    # Create new rules
    created_rules = []
    for assignment in payload.assignments:
        rule = LeadDistributionRule(
            clinic_id=clinic_id,
            channel=payload.channel,
            agent_id=assignment.agent_id,
            percentage=assignment.percentage,
            is_active=True,
        )
        db.add(rule)
        created_rules.append(rule)

    db.commit()

    # Log activity
    log_activity(
        db=db,
        clinic_id=clinic_id,
        category="lead",
        action="distribution_rules_updated",
        details={"channel": payload.channel, "assignments": len(payload.assignments)},
        user_email=current_user.email,
    )

    logger.info(
        f"Updated distribution rules for clinic {clinic_id} channel '{payload.channel}' "
        f"with {len(payload.assignments)} assignments"
    )

    return {
        "success": True,
        "channel": payload.channel,
        "assignments": [
            {
                "agent_id": rule.agent_id,
                "percentage": rule.percentage,
            }
            for rule in created_rules
        ],
    }


@router.delete("/rules/{channel}", dependencies=[Depends(require_role(["admin", "manager"]))])
async def delete_rules(
    channel: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove all distribution rules for a channel.
    Admin/Manager only.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Super admins cannot manage clinic-specific rules")

    deleted = db.query(LeadDistributionRule).filter(
        and_(
            LeadDistributionRule.clinic_id == clinic_id,
            LeadDistributionRule.channel == channel,
        )
    ).delete()

    db.commit()

    # Log activity
    log_activity(
        db=db,
        clinic_id=clinic_id,
        category="lead",
        action="distribution_rules_deleted",
        details={"channel": channel, "deleted_count": deleted},
        user_email=current_user.email,
    )

    logger.info(f"Deleted {deleted} distribution rules for clinic {clinic_id} channel '{channel}'")

    return {
        "success": True,
        "channel": channel,
        "deleted_count": deleted,
    }


@router.get("/channels", dependencies=[Depends(require_role(["admin", "manager"]))])
async def get_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of available channels with current rule status.
    Admin/Manager only.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Super admins cannot manage clinic-specific rules")

    available_channels = lead_distributor.get_available_channels()
    channel_statuses = []

    for channel in available_channels:
        rules = db.query(LeadDistributionRule).filter(
            and_(
                LeadDistributionRule.clinic_id == clinic_id,
                LeadDistributionRule.channel == channel,
                LeadDistributionRule.is_active == True,
            )
        ).all()

        total_percentage = sum(r.percentage for r in rules)
        assignments = []
        for rule in rules:
            agent = db.query(User).filter(User.id == rule.agent_id).first()
            assignments.append({
                "agent_id": rule.agent_id,
                "agent_name": agent.full_name if agent else "Unknown",
                "percentage": rule.percentage,
            })

        channel_statuses.append({
            "channel": channel,
            "has_rules": len(rules) > 0,
            "total_percentage": total_percentage,
            "agent_count": len(rules),
            "assignments": assignments,
        })

    return {
        "clinic_id": clinic_id,
        "channels": channel_statuses,
    }


@router.get("/stats", dependencies=[Depends(require_role(["admin", "manager"]))])
async def get_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get distribution statistics for last N days.
    Shows how many leads were assigned to each agent by channel.
    Admin/Manager only.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Super admins cannot view clinic-specific stats")

    stats = lead_distributor.get_distribution_stats(
        db=db,
        clinic_id=clinic_id,
        days=days,
    )

    return {
        "clinic_id": clinic_id,
        **stats,
    }


# ============================================================================
# Lead Assignment Endpoints
# ============================================================================

@router.post("/assign/{lead_id}", dependencies=[Depends(require_role(["admin", "manager"]))])
async def manually_assign_lead(
    lead_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually assign or reassign a lead to an agent.
    Admin/Manager only.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Super admins cannot assign leads")

    # Get lead
    lead = db.query(Lead).filter(
        and_(
            Lead.id == lead_id,
            Lead.clinic_id == clinic_id,
        )
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Validate agent
    agent = db.query(User).filter(
        and_(
            User.id == agent_id,
            User.clinic_id == clinic_id,
            User.is_active == True,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or inactive")

    # Assign lead
    lead.assigned_agent_id = agent_id
    lead.updated_at = datetime.utcnow()

    # Log manual assignment
    channel = lead_distributor.get_channel_from_source(lead.source)
    log_entry = LeadDistributionLog(
        clinic_id=clinic_id,
        lead_id=lead_id,
        agent_id=agent_id,
        channel=channel,
        method="manual",
    )
    db.add(log_entry)
    db.commit()

    # Log activity
    log_activity(
        db=db,
        clinic_id=clinic_id,
        category="lead",
        action="lead_manually_assigned",
        details={"agent_name": agent.full_name},
        user_email=current_user.email,
        related_id=lead_id,
        related_type="lead",
    )

    logger.info(f"Lead {lead_id} manually assigned to agent {agent_id} by {current_user.email}")

    return {
        "success": True,
        "lead_id": lead_id,
        "agent_id": agent_id,
        "agent_name": agent.full_name,
    }


@router.post("/auto-assign")
async def auto_assign_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Auto-assign a lead based on distribution rules.
    Can be called by any authenticated user (typically from lead creation).
    Determines channel from lead.source and applies rules.
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        # If super admin, try to get clinic from lead
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        clinic_id = lead.clinic_id
    else:
        # Verify lead belongs to user's clinic
        lead = db.query(Lead).filter(
            and_(
                Lead.id == lead_id,
                Lead.clinic_id == clinic_id,
            )
        ).first()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

    # Auto-assign using distribution engine
    try:
        agent_id, method = lead_distributor.distribute_lead(
            db=db,
            clinic_id=clinic_id,
            lead_id=lead_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get agent details
    agent = db.query(User).filter(User.id == agent_id).first()

    logger.info(
        f"Lead {lead_id} auto-assigned to agent {agent_id} via {method} "
        f"for clinic {clinic_id}"
    )

    return {
        "success": True,
        "lead_id": lead_id,
        "agent_id": agent_id,
        "agent_name": agent.full_name if agent else "Unknown",
        "method": method,
        "assigned_at": datetime.utcnow(),
    }


# ============================================================================
# Agent View Filtering
# ============================================================================

@router.get("/my-leads")
async def get_my_leads(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get leads assigned to the current agent.
    Agents can ONLY see leads assigned to them.
    Admins/Managers see all clinic leads (use /distribution/rules instead).

    Optional filters:
    - status: Filter by lead status (new, contacted, qualified, etc.)
    - source: Filter by lead source (whatsapp, form_meta, etc.)
    - days: Only return leads from last N days
    """
    clinic_id = current_user.clinic_id
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Super admins cannot view agent leads")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Build query
    query = db.query(Lead).filter(
        and_(
            Lead.clinic_id == clinic_id,
            Lead.assigned_agent_id == current_user.id,
            Lead.created_at >= cutoff_date,
        )
    )

    # Apply filters
    if status:
        query = query.filter(Lead.status == status)
    if source:
        query = query.filter(Lead.source == source)

    leads = query.order_by(Lead.created_at.desc()).all()

    # Build response
    lead_list = []
    for lead in leads:
        lead_list.append({
            "id": lead.id,
            "name": lead.name,
            "phone": lead.phone,
            "email": lead.email,
            "source": lead.source,
            "campaign_name": lead.campaign_name,
            "status": lead.status,
            "lead_score": lead.lead_score,
            "created_at": lead.created_at,
            "updated_at": lead.updated_at,
        })

    return {
        "clinic_id": clinic_id,
        "agent_id": current_user.id,
        "agent_name": current_user.full_name,
        "filters": {
            "status": status,
            "source": source,
            "days": days,
        },
        "total_leads": len(leads),
        "leads": lead_list,
    }
