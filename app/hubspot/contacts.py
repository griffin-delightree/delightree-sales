"""Fetch HubSpot contacts associated with a company.

Uses the contact property `associatedcompanyid` (verified present) so we can pull
a company's roster with a single search, no associations API round-trip.
"""
from __future__ import annotations

from .client import HubSpotClient

# verified-present contact properties
CONTACT_PROPS = [
    "firstname", "lastname", "jobtitle", "email", "work_email",
    "phone", "mobilephone", "hs_linkedin_url", "linkedin",
    "hs_lead_status", "lifecyclestage", "hs_seniority", "associatedcompanyid",
]


async def contacts_for_company(client: HubSpotClient, company_id: str) -> list[dict]:
    """Return raw contact objects associated with the company."""
    return await client.search(
        "contacts",
        filter_groups=[
            {"filters": [{"propertyName": "associatedcompanyid", "operator": "EQ", "value": company_id}]}
        ],
        properties=CONTACT_PROPS,
    )


def contact_name(pr: dict) -> str:
    n = f"{pr.get('firstname') or ''} {pr.get('lastname') or ''}".strip()
    return n or "(no name)"


def contact_email(pr: dict) -> str:
    return (pr.get("email") or pr.get("work_email") or "").strip()


def contact_linkedin(pr: dict) -> str:
    return (pr.get("hs_linkedin_url") or pr.get("linkedin") or "").strip()
