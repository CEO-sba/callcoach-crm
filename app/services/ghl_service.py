"""
CallCoach CRM - GoHighLevel API Integration Service

Handles all communication with GoHighLevel's REST API v2.
- Validates API keys
- Fetches contacts and opportunities (leads)
- Maps GHL pipeline stages to CallCoach stages
- Syncs leads into the CallCoach pipeline
"""
import logging
from datetime import datetime
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

GHL_API_BASE = "https://services.leadconnectorhq.com"
GHL_API_TIMEOUT = 30

# GHL pipeline stage -> CallCoach stage mapping
# Users can have custom pipelines; this maps common GHL stage names
STAGE_MAP = {
    "new": "new_inquiry",
    "new lead": "new_inquiry",
    "new inquiry": "new_inquiry",
    "contacted": "contacted",
    "follow up": "contacted",
    "follow-up": "contacted",
    "appointment booked": "consultation_booked",
    "appointment scheduled": "consultation_booked",
    "consultation booked": "consultation_booked",
    "booked": "consultation_booked",
    "appointment completed": "consultation_done",
    "consultation done": "consultation_done",
    "showed": "consultation_done",
    "show": "consultation_done",
    "proposal sent": "proposal_sent",
    "quote sent": "proposal_sent",
    "won": "won",
    "closed won": "won",
    "converted": "won",
    "lost": "lost",
    "closed lost": "lost",
    "no show": "lost",
    "no-show": "lost",
}

DEFAULT_STAGE = "new_inquiry"


class GHLClient:
    """GoHighLevel API v2 client."""

    def __init__(self, api_key: str, location_id: Optional[str] = None):
        self.api_key = api_key
        self.location_id = location_id

        # Private Integration Tokens (pit-*) don't use "Bearer" prefix.
        # OAuth tokens (usually JWT starting with "ey") need "Bearer" prefix.
        if api_key.startswith("Bearer "):
            auth_value = api_key  # User already included Bearer
        elif api_key.startswith("ey"):
            auth_value = f"Bearer {api_key}"  # OAuth JWT token
        else:
            auth_value = api_key  # Private Integration Token (no prefix)

        self.headers = {
            "Authorization": auth_value,
            "Version": "2021-07-28",
            "Content-Type": "application/json",
        }

    async def validate_key(self) -> dict:
        """
        Validate the API key by fetching the location/account info.
        Returns location data if valid, raises on invalid.
        """
        async with httpx.AsyncClient(timeout=GHL_API_TIMEOUT) as client:
            # Try to get locations
            if self.location_id:
                url = f"{GHL_API_BASE}/locations/{self.location_id}"
                resp = await client.get(url, headers=self.headers)
            else:
                # Try fetching contacts as a validation check
                url = f"{GHL_API_BASE}/contacts/"
                resp = await client.get(
                    url,
                    headers=self.headers,
                    params={"limit": 1}
                )

            if resp.status_code == 401:
                raise ValueError("Invalid API key. Please check your GoHighLevel API key.")
            if resp.status_code == 403:
                raise ValueError("API key does not have sufficient permissions. Enable contacts and opportunities scopes.")
            if resp.status_code >= 400:
                raise ValueError(f"GoHighLevel API error ({resp.status_code}): {resp.text[:200]}")

            return resp.json()

    async def get_contacts(
        self,
        limit: int = 100,
        after: Optional[str] = None,
        start_after: Optional[datetime] = None
    ) -> dict:
        """
        Fetch contacts from GHL.
        Returns: { contacts: [...], meta: { total, nextPageUrl, startAfterId } }
        """
        params = {"limit": min(limit, 100)}
        if after:
            params["startAfterId"] = after
        if start_after:
            params["startAfter"] = int(start_after.timestamp() * 1000)
        if self.location_id:
            params["locationId"] = self.location_id

        async with httpx.AsyncClient(timeout=GHL_API_TIMEOUT) as client:
            resp = await client.get(
                f"{GHL_API_BASE}/contacts/",
                headers=self.headers,
                params=params
            )
            resp.raise_for_status()
            return resp.json()

    async def get_pipelines(self) -> list:
        """Fetch all pipelines for the location."""
        params = {}
        if self.location_id:
            params["locationId"] = self.location_id

        async with httpx.AsyncClient(timeout=GHL_API_TIMEOUT) as client:
            resp = await client.get(
                f"{GHL_API_BASE}/opportunities/pipelines",
                headers=self.headers,
                params=params
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("pipelines", [])

    async def get_opportunities(
        self,
        pipeline_id: Optional[str] = None,
        limit: int = 100,
        after: Optional[str] = None
    ) -> dict:
        """
        Fetch opportunities (leads/deals) from a GHL pipeline.
        Returns: { opportunities: [...], meta: {...} }
        """
        params = {"limit": min(limit, 100)}
        if pipeline_id:
            params["pipelineId"] = pipeline_id
        if after:
            params["startAfterId"] = after
        if self.location_id:
            params["locationId"] = self.location_id

        async with httpx.AsyncClient(timeout=GHL_API_TIMEOUT) as client:
            resp = await client.get(
                f"{GHL_API_BASE}/opportunities/search",
                headers=self.headers,
                params=params
            )
            resp.raise_for_status()
            return resp.json()

    async def get_contact_detail(self, contact_id: str) -> dict:
        """Fetch full contact details."""
        async with httpx.AsyncClient(timeout=GHL_API_TIMEOUT) as client:
            resp = await client.get(
                f"{GHL_API_BASE}/contacts/{contact_id}",
                headers=self.headers
            )
            resp.raise_for_status()
            return resp.json().get("contact", {})


def map_ghl_stage(ghl_stage_name: str) -> str:
    """Map a GoHighLevel stage name to a CallCoach pipeline stage."""
    if not ghl_stage_name:
        return DEFAULT_STAGE
    normalized = ghl_stage_name.strip().lower()
    return STAGE_MAP.get(normalized, DEFAULT_STAGE)


def map_ghl_opportunity_to_deal(opp: dict, contact: dict = None) -> dict:
    """
    Convert a GHL opportunity + contact into a CallCoach deal dict.
    Ready to be used for PipelineDeal creation.
    """
    # Extract contact info from opportunity or separate contact
    contact_name = opp.get("contact", {}).get("name", "")
    contact_phone = opp.get("contact", {}).get("phone", "")
    contact_email = opp.get("contact", {}).get("email", "")

    if contact:
        contact_name = contact_name or f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
        contact_phone = contact_phone or contact.get("phone", "")
        contact_email = contact_email or contact.get("email", "")

    # Map stage
    stage_name = opp.get("pipelineStageId", "")
    # GHL opportunities have stageName in some API versions
    stage_display = opp.get("status", "open")

    # Extract monetary value
    monetary_value = opp.get("monetaryValue", 0) or 0

    # Determine source from tags or source field
    source = opp.get("source", "gohighlevel")

    # Build the deal data
    deal_data = {
        "contact_name": contact_name or "Unknown",
        "contact_phone": contact_phone,
        "contact_email": contact_email,
        "title": opp.get("name", contact_name or "GHL Lead"),
        "treatment_interest": ", ".join(opp.get("tags", [])) if opp.get("tags") else None,
        "deal_value": float(monetary_value),
        "stage": DEFAULT_STAGE,  # Will be refined by stage mapping
        "priority": "medium",
        "source": source or "gohighlevel",
        "ghl_contact_id": opp.get("contactId") or (contact.get("id") if contact else None),
        "ghl_opportunity_id": opp.get("id"),
    }

    # Map status to stage
    opp_status = (opp.get("status") or "").lower()
    if opp_status == "won":
        deal_data["stage"] = "won"
        deal_data["status"] = "won"
    elif opp_status == "lost":
        deal_data["stage"] = "lost"
        deal_data["status"] = "lost"
    elif opp_status == "abandoned":
        deal_data["stage"] = "lost"
        deal_data["status"] = "lost"
        deal_data["lost_reason"] = "Abandoned in GHL"

    return deal_data


def map_ghl_contact_to_deal(contact: dict) -> dict:
    """
    Convert a standalone GHL contact (no opportunity) into a CallCoach deal.
    Used when syncing contacts directly instead of opportunities.
    """
    first = contact.get("firstName", "")
    last = contact.get("lastName", "")
    name = f"{first} {last}".strip() or contact.get("name", "Unknown")

    tags = contact.get("tags", [])

    return {
        "contact_name": name,
        "contact_phone": contact.get("phone", ""),
        "contact_email": contact.get("email", ""),
        "title": f"{name} - GHL Lead",
        "treatment_interest": ", ".join(tags) if tags else None,
        "deal_value": 0,
        "stage": "new_inquiry",
        "priority": "medium",
        "source": contact.get("source", "gohighlevel"),
        "ghl_contact_id": contact.get("id"),
        "ghl_opportunity_id": None,
    }
