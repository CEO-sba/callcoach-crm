"""
CallCoach CRM - Lead Scoring Service
AI-powered lead scoring based on multiple signals.
"""
import logging
from sqlalchemy.orm import Session
from app.models_whatsapp import Lead, WhatsAppConversation, WhatsAppMessage

logger = logging.getLogger(__name__)


def calculate_lead_score(db: Session, lead: Lead) -> int:
    """Calculate lead score (0-100) based on multiple factors."""

    score = 0

    # 1. Contact completeness (max 15 points)
    if lead.phone:
        score += 5
    if lead.email:
        score += 5
    if lead.name and lead.name != f"WhatsApp {lead.phone}":
        score += 5

    # 2. Procedure interest (max 20 points)
    high_value_procedures = [
        "hair transplant", "hair_transplant_fue", "hair_transplant_fut",
        "rhinoplasty", "facelift", "breast_augmentation", "tummy_tuck",
        "liposuction", "smile_makeover", "dental_veneers"
    ]
    medium_value_procedures = [
        "botox", "fillers", "coolsculpting", "skin_tightening",
        "laser_hair_removal", "blepharoplasty", "scalp_micropigmentation"
    ]

    if lead.procedure_interest:
        interest_lower = lead.procedure_interest.lower().replace(" ", "_")
        if any(p in interest_lower for p in high_value_procedures):
            score += 20
        elif any(p in interest_lower for p in medium_value_procedures):
            score += 15
        else:
            score += 10

    # 3. Source quality (max 15 points)
    source_scores = {
        "meta_lead_form": 15,  # Filled a form = high intent
        "form_google": 15,
        "form_meta": 14,
        "whatsapp": 12,  # Initiated contact = decent intent
        "call": 13,
        "walk_in": 15,
        "manual": 5,
    }
    score += source_scores.get(lead.source, 5)

    # 4. Campaign source (max 10 points)
    if lead.campaign_source:
        campaign_scores = {
            "google": 10,  # Google search = high intent
            "meta": 7,
            "organic": 5,
            "direct": 6,
        }
        score += campaign_scores.get(lead.campaign_source.lower(), 3)

    # 5. Engagement (max 25 points) - based on WhatsApp conversation
    conversation = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.lead_id == lead.id
    ).first()

    if conversation:
        # Has a conversation = engaged
        score += 5

        # Count inbound messages (patient-initiated)
        inbound_count = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.conversation_id == conversation.id,
            WhatsAppMessage.direction == "inbound"
        ).count()

        if inbound_count >= 10:
            score += 20  # Very engaged
        elif inbound_count >= 5:
            score += 15
        elif inbound_count >= 3:
            score += 10
        elif inbound_count >= 1:
            score += 5

    # 6. Status progression (max 15 points)
    status_scores = {
        "new": 0,
        "contacted": 5,
        "qualified": 10,
        "consultation_booked": 15,
        "converted": 15,
        "lost": 0,
    }
    score += status_scores.get(lead.status, 0)

    # Cap at 100
    return min(score, 100)


def update_lead_score(db: Session, lead: Lead):
    """Recalculate and save lead score."""
    new_score = calculate_lead_score(db, lead)
    lead.lead_score = new_score
    db.commit()
    return new_score
