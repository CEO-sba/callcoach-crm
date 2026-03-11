"""
CallCoach CRM - Contacts Router
Aggregates contacts from calls and pipeline deals.
"""
import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.models import Call, PipelineDeal, User
from app.auth import get_current_user

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


def _build_contacts(db: Session, clinic_id: str):
    """Build a deduplicated list of contacts from calls and deals."""
    contacts = {}

    # Get contacts from calls
    calls = db.query(Call).filter(Call.clinic_id == clinic_id).order_by(Call.call_date.desc()).all()
    for call in calls:
        key = (call.caller_phone or call.caller_email or call.caller_name or call.id).strip().lower()
        if not key:
            continue
        if key not in contacts:
            contacts[key] = {
                "name": call.caller_name or "",
                "phone": call.caller_phone or "",
                "email": call.caller_email or "",
                "total_calls": 0,
                "total_deals": 0,
                "last_call_date": None,
                "first_seen": None,
                "treatments_interested": [],
                "source": "",
                "latest_sentiment": "",
                "latest_intent": "",
                "deal_stages": [],
                "deal_value": 0,
            }
        c = contacts[key]
        c["total_calls"] += 1
        if not c["name"] and call.caller_name:
            c["name"] = call.caller_name
        if not c["phone"] and call.caller_phone:
            c["phone"] = call.caller_phone
        if not c["email"] and call.caller_email:
            c["email"] = call.caller_email
        if call.call_date:
            if not c["last_call_date"] or call.call_date > c["last_call_date"]:
                c["last_call_date"] = call.call_date
                c["latest_sentiment"] = call.ai_sentiment or ""
                c["latest_intent"] = call.ai_intent or ""
            if not c["first_seen"] or call.call_date < c["first_seen"]:
                c["first_seen"] = call.call_date
        if call.ai_key_topics:
            for topic in call.ai_key_topics:
                if topic and topic not in c["treatments_interested"]:
                    c["treatments_interested"].append(topic)

    # Merge contacts from deals
    deals = db.query(PipelineDeal).filter(PipelineDeal.clinic_id == clinic_id).all()
    for deal in deals:
        key = (deal.contact_phone or deal.contact_email or deal.contact_name or deal.id).strip().lower()
        if not key:
            continue
        if key not in contacts:
            contacts[key] = {
                "name": deal.contact_name or "",
                "phone": deal.contact_phone or "",
                "email": deal.contact_email or "",
                "total_calls": 0,
                "total_deals": 0,
                "last_call_date": None,
                "first_seen": deal.created_at,
                "treatments_interested": [],
                "source": deal.source or "",
                "latest_sentiment": "",
                "latest_intent": "",
                "deal_stages": [],
                "deal_value": 0,
            }
        c = contacts[key]
        c["total_deals"] += 1
        if not c["name"] and deal.contact_name:
            c["name"] = deal.contact_name
        if not c["phone"] and deal.contact_phone:
            c["phone"] = deal.contact_phone
        if not c["email"] and deal.contact_email:
            c["email"] = deal.contact_email
        if deal.treatment_interest and deal.treatment_interest not in c["treatments_interested"]:
            c["treatments_interested"].append(deal.treatment_interest)
        if not c["source"] and deal.source:
            c["source"] = deal.source
        if deal.stage:
            c["deal_stages"].append(deal.stage)
        c["deal_value"] += deal.deal_value or 0
        if deal.created_at:
            if not c["first_seen"] or deal.created_at < c["first_seen"]:
                c["first_seen"] = deal.created_at

    # Convert to list and sort by last interaction
    result = []
    for key, c in contacts.items():
        result.append({
            "id": key,
            "name": c["name"],
            "phone": c["phone"],
            "email": c["email"],
            "total_calls": c["total_calls"],
            "total_deals": c["total_deals"],
            "last_call_date": c["last_call_date"].isoformat() if c["last_call_date"] else None,
            "first_seen": c["first_seen"].isoformat() if c["first_seen"] else None,
            "treatments_interested": ", ".join(c["treatments_interested"]),
            "source": c["source"],
            "latest_sentiment": c["latest_sentiment"],
            "latest_intent": c["latest_intent"],
            "deal_stages": ", ".join(c["deal_stages"]),
            "deal_value": c["deal_value"],
        })

    result.sort(key=lambda x: x["last_call_date"] or x["first_seen"] or "", reverse=True)
    return result


@router.get("")
def list_contacts(
    updated_since: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all unique contacts aggregated from calls and deals.

    Optional: pass updated_since (ISO datetime) to get only contacts
    created/updated after that timestamp. Used for mobile app incremental sync.
    """
    contacts = _build_contacts(db, current_user.clinic_id)

    if updated_since:
        try:
            since = datetime.fromisoformat(updated_since.replace("Z", "+00:00"))
            contacts = [
                c for c in contacts
                if (c.get("last_call_date") and datetime.fromisoformat(c["last_call_date"]) > since)
                or (c.get("first_seen") and datetime.fromisoformat(c["first_seen"]) > since)
            ]
        except (ValueError, TypeError):
            pass

    return {"contacts": contacts, "total": len(contacts), "timestamp": datetime.utcnow().isoformat()}


@router.get("/csv")
def download_contacts_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download all contacts as CSV."""
    contacts = _build_contacts(db, current_user.clinic_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Phone", "Email", "Total Calls", "Total Deals",
        "Last Call Date", "First Seen", "Treatments Interested",
        "Source", "Latest Sentiment", "Latest Intent",
        "Deal Stages", "Deal Value"
    ])
    for c in contacts:
        writer.writerow([
            c["name"], c["phone"], c["email"], c["total_calls"], c["total_deals"],
            c["last_call_date"] or "", c["first_seen"] or "",
            c["treatments_interested"], c["source"],
            c["latest_sentiment"], c["latest_intent"],
            c["deal_stages"], c["deal_value"]
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=contacts_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        }
    )
