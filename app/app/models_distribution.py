"""
CallCoach CRM - Lead Distribution Models
Manages lead distribution rules and tracks distribution history.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class LeadDistributionRule(Base):
    """
    Defines how leads should be distributed to agents by channel.
    For each clinic + channel combination, defines multiple agents with percentages.
    """
    __tablename__ = "lead_distribution_rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    channel = Column(String(50), nullable=False)
    # Supported channels: "meta", "google", "website", "walk_in", "referral", "whatsapp", "manual", "call", "all"
    agent_id = Column(String, ForeignKey("users.id"), nullable=False)
    percentage = Column(Integer, nullable=False)  # 0-100
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one rule per clinic+channel+agent
    __table_args__ = (UniqueConstraint(
        'clinic_id', 'channel', 'agent_id',
        name='uq_distribution_rule'
    ),)

    # Relationships
    clinic = relationship("Clinic", foreign_keys=[clinic_id])
    agent = relationship("User", foreign_keys=[agent_id])
    logs = relationship("LeadDistributionLog", back_populates="rule", cascade="all, delete-orphan")


class LeadDistributionLog(Base):
    """
    Audit trail for lead assignments.
    Tracks every lead-to-agent assignment with method and rule used.
    """
    __tablename__ = "lead_distribution_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    agent_id = Column(String, ForeignKey("users.id"), nullable=False)
    channel = Column(String(50), nullable=False)  # The channel of the lead
    rule_id = Column(String, ForeignKey("lead_distribution_rules.id"), nullable=True)
    # method: "percentage_rule" (weighted random), "round_robin", "manual", "fallback"
    method = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", foreign_keys=[clinic_id])
    lead = relationship("Lead", foreign_keys=[lead_id])
    agent = relationship("User", foreign_keys=[agent_id])
    rule = relationship("LeadDistributionRule", back_populates="logs", foreign_keys=[rule_id])
