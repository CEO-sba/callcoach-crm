"""
CallCoach CRM - Lead Distribution Engine
Handles intelligent lead distribution based on channel rules and weighted percentages.
"""
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models_whatsapp import Lead
from app.models import User
from app.models_distribution import LeadDistributionRule, LeadDistributionLog

logger = logging.getLogger(__name__)


# Channel mapping from Lead.source to distribution channel
SOURCE_TO_CHANNEL_MAP = {
    "form_meta": "meta",
    "meta_lead_form": "meta",
    "form_google": "google",
    "whatsapp": "whatsapp",
    "walk_in": "walk_in",
    "call": "call",
    "manual": "manual",
    "website": "website",
}


def get_channel_from_source(source: str) -> str:
    """
    Convert Lead.source to distribution channel.
    Default to the source itself if not mapped.
    """
    return SOURCE_TO_CHANNEL_MAP.get(source, source)


def distribute_lead(
    db: Session,
    clinic_id: str,
    lead_id: str,
    channel: str = None,
) -> tuple[str, str]:
    """
    Distribute a lead to an agent based on channel percentage rules.

    Algorithm:
    1. Get all active rules for this clinic + channel
    2. If no rules exist for channel, try "all" channel rules
    3. If still no rules, use round-robin among all active clinic agents
    4. Use weighted random selection based on percentages
    5. Smart weighting: track actual counts and slightly favor under-assigned agents
    6. Create LeadDistributionLog entry
    7. Update lead.assigned_agent_id

    Args:
        db: Database session
        clinic_id: Clinic ID
        lead_id: Lead ID to distribute
        channel: Distribution channel (optional - can be inferred from lead)

    Returns:
        tuple: (assigned_agent_id, method_used)

    Raises:
        ValueError: If lead not found or no agents available
        HTTPException: If clinic has no agents
    """
    # Get the lead
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    # Determine channel if not provided
    if not channel:
        channel = get_channel_from_source(lead.source)
        logger.info(f"Lead {lead_id}: Determined channel '{channel}' from source '{lead.source}'")

    # Try to get rules for this channel
    rules = db.query(LeadDistributionRule).filter(
        and_(
            LeadDistributionRule.clinic_id == clinic_id,
            LeadDistributionRule.channel == channel,
            LeadDistributionRule.is_active == True
        )
    ).all()

    # Fallback to "all" channel if no specific rules
    if not rules:
        logger.info(f"No rules for clinic {clinic_id} channel '{channel}', trying 'all'")
        rules = db.query(LeadDistributionRule).filter(
            and_(
                LeadDistributionRule.clinic_id == clinic_id,
                LeadDistributionRule.channel == "all",
                LeadDistributionRule.is_active == True
            )
        ).all()

    # Use weighted random selection if rules exist
    if rules:
        agent_id, method = _weighted_random_selection(db, clinic_id, channel, rules)
        logger.info(f"Lead {lead_id}: Assigned to agent {agent_id} via {method}")
    else:
        # Fallback to round-robin among all active agents
        logger.info(f"No distribution rules found for clinic {clinic_id} channel '{channel}', using round-robin")
        agent_id, method = _round_robin_selection(db, clinic_id)

    if not agent_id:
        raise ValueError(f"No active agents available for clinic {clinic_id}")

    # Update lead assignment
    lead.assigned_agent_id = agent_id
    lead.updated_at = datetime.utcnow()

    # Create distribution log
    rule_id = next((r.id for r in rules), None) if rules else None
    log_entry = LeadDistributionLog(
        clinic_id=clinic_id,
        lead_id=lead_id,
        agent_id=agent_id,
        channel=channel,
        rule_id=rule_id,
        method=method,
    )
    db.add(log_entry)
    db.commit()

    logger.info(f"Lead {lead_id} distributed to agent {agent_id} via {method}")
    return agent_id, method


def _weighted_random_selection(
    db: Session,
    clinic_id: str,
    channel: str,
    rules: List[LeadDistributionRule],
) -> tuple[str, str]:
    """
    Select agent using weighted random selection with smart tracking.
    Maintains accurate distribution percentages over time by accounting
    for actual assignment counts.
    """
    # Get assignment counts for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_counts = {}

    agent_ids = [r.agent_id for r in rules]
    for agent_id in agent_ids:
        count = db.query(func.count(LeadDistributionLog.id)).filter(
            and_(
                LeadDistributionLog.clinic_id == clinic_id,
                LeadDistributionLog.agent_id == agent_id,
                LeadDistributionLog.channel == channel,
                LeadDistributionLog.created_at >= thirty_days_ago,
            )
        ).scalar()
        recent_counts[agent_id] = count or 0

    # Calculate total and percentages
    total_recent = sum(recent_counts.values())
    rule_dict = {r.agent_id: r.percentage for r in rules}

    # Build weighted list with smart adjustments
    # If an agent is under-assigned compared to their percentage, boost them slightly
    weighted_agents = []
    for rule in rules:
        agent_id = rule.agent_id
        target_percentage = rule.percentage

        if total_recent > 0:
            actual_percentage = (recent_counts[agent_id] / total_recent) * 100
            # Boost weight if under-assigned, reduce if over-assigned
            # Use a sigmoid-like adjustment: if actual < target, weight up to 110%
            adjustment = (target_percentage - actual_percentage) * 0.5
            adjusted_percentage = max(1, target_percentage + adjustment)
        else:
            # First assignments: use target percentage
            adjusted_percentage = target_percentage

        # Add agent to weighted list (percentage weight)
        # Ensure at least 1 for agents with 0%
        weight = max(1, int(adjusted_percentage))
        weighted_agents.extend([agent_id] * weight)

    # Random selection from weighted list
    if weighted_agents:
        selected_agent_id = random.choice(weighted_agents)
        return selected_agent_id, "percentage_rule"

    # Fallback to any available agent from rules
    return rules[0].agent_id, "percentage_rule"


def _round_robin_selection(
    db: Session,
    clinic_id: str,
) -> tuple[str, str]:
    """
    Select agent using round-robin method.
    Distributes leads evenly among all active clinic agents.
    """
    # Get all active agents for the clinic
    active_agents = db.query(User).filter(
        and_(
            User.clinic_id == clinic_id,
            User.is_active == True,
        )
    ).all()

    if not active_agents:
        return None, "round_robin"

    # Count recent assignments for each agent (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    assignment_counts = {}

    for agent in active_agents:
        count = db.query(func.count(LeadDistributionLog.id)).filter(
            and_(
                LeadDistributionLog.clinic_id == clinic_id,
                LeadDistributionLog.agent_id == agent.id,
                LeadDistributionLog.created_at >= seven_days_ago,
            )
        ).scalar()
        assignment_counts[agent.id] = count or 0

    # Select agent with fewest recent assignments
    selected_agent = min(active_agents, key=lambda a: assignment_counts[a.id])
    return selected_agent.id, "round_robin"


def get_distribution_stats(
    db: Session,
    clinic_id: str,
    days: int = 30,
) -> Dict:
    """
    Get distribution statistics for the clinic.

    Returns:
        dict: Stats grouped by channel and agent
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    logs = db.query(LeadDistributionLog).filter(
        and_(
            LeadDistributionLog.clinic_id == clinic_id,
            LeadDistributionLog.created_at >= cutoff_date,
        )
    ).all()

    # Group by channel and agent
    stats_by_channel = {}
    for log in logs:
        if log.channel not in stats_by_channel:
            stats_by_channel[log.channel] = {}

        if log.agent_id not in stats_by_channel[log.channel]:
            stats_by_channel[log.channel][log.agent_id] = {
                "agent_id": log.agent_id,
                "agent_name": log.agent.full_name if log.agent else "Unknown",
                "count": 0,
                "percentage": 0,
            }

        stats_by_channel[log.channel][log.agent_id]["count"] += 1

    # Calculate percentages per channel
    for channel, agents in stats_by_channel.items():
        total = sum(a["count"] for a in agents.values())
        for agent in agents.values():
            agent["percentage"] = (agent["count"] / total * 100) if total > 0 else 0

    return {
        "days": days,
        "cutoff_date": cutoff_date.isoformat(),
        "stats_by_channel": stats_by_channel,
    }


def validate_percentage_distribution(assignments: List[Dict]) -> bool:
    """
    Validate that percentage assignments sum to 100.

    Args:
        assignments: List of {agent_id, percentage}

    Returns:
        bool: True if valid

    Raises:
        ValueError: If percentages don't sum to 100
    """
    total = sum(a.get("percentage", 0) for a in assignments)
    if total != 100:
        raise ValueError(f"Percentages must sum to 100, got {total}")
    return True


def get_available_channels() -> List[str]:
    """Get list of supported distribution channels."""
    return list(SOURCE_TO_CHANNEL_MAP.values()) + ["all"]
