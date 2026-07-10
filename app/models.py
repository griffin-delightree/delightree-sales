"""Shared domain models used across the pipeline.

Step 2 uses CandidateCompany. Contact/VerificationStatus are defined now so the
verification contract is fixed from the start (steps 3-5 fill them in).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Per the spec's 3-source protocol. A server cannot open a live LinkedIn in
    the rep's Chrome, so the CEILING any server-side check can reach is
    NOT_LINKEDIN_VERIFIED. Only a logged human/live-LinkedIn confirmation may set
    LINKEDIN_VERIFIED. The renderer shows the red "confirm before outreach" flag
    for anything that is not LINKEDIN_VERIFIED.
    """

    LINKEDIN_VERIFIED = "linkedin_verified"          # live LinkedIn confirmed current (human only)
    ZOOMINFO_CORROBORATED = "zoominfo_corroborated"  # ZoomInfo+Apollo agree, LinkedIn not checked -> still flag
    COMPANY_PAGE_ONLY = "company_page_only"          # only appears on About/Team page -> weak, flag
    NOT_LINKEDIN_VERIFIED = "not_linkedin_verified"  # sourced but unconfirmed -> flag
    HELD_OUT = "held_out"                            # sources conflict / departure signal -> do NOT present as active

    @property
    def is_clean_active(self) -> bool:
        return self is VerificationStatus.LINKEDIN_VERIFIED


class EligibilityReason(str, Enum):
    """Why a company did (or did not) make the candidate pool. Used for the
    audit trail so a rep/RevOps can see exactly why an account was surfaced or
    skipped."""

    ELIGIBLE = "eligible"
    OWNED_BY_REP = "owned_by_rep"
    AE_OWNED_ADR_REP = "ae_owned_adr_rep"
    HAS_OPEN_DEAL = "has_open_deal"
    RECENTLY_CONTACTED = "recently_contacted"
    EXCLUDED_STATUS = "excluded_status"
    IS_CUSTOMER = "is_customer"
    ALREADY_WORKED = "already_worked"          # in tracker.completed_company_ids
    BELOW_LOCATION_FLOOR = "below_location_floor"
    ABOVE_LOCATION_CEILING = "above_location_ceiling"


class CandidateCompany(BaseModel):
    """A company that cleared the query-level eligibility filters and is a member
    of the daily pool for one rep. Enrichment/verification (steps 3+) refine this
    into the full company record used by data.json."""

    id: str                                   # HubSpot company id
    name: str
    domain: str = ""
    vertical: str = ""                        # from custom property if present; else enriched later
    status: str = ""                          # company_status
    lifecyclestage: str = ""
    hubspot_owner_id: str = ""
    adr: str = ""
    open_deals: int = 0
    notes_last_contacted: Optional[str] = None   # ISO date string or None (never contacted)
    location_count: Optional[int] = None          # None => must be web-verified in enrichment
    hubspot_url: str = ""
    matched_reason: EligibilityReason = EligibilityReason.ELIGIBLE
    priority: int = 1                             # 1 = normal; 2 = deprioritized (e.g. "No Contacts")
    priority_reason: str = ""                     # why it was deprioritized, for the audit trail
    raw: dict = Field(default_factory=dict, repr=False)   # full property bag for debugging


# ------------------------- enriched output (steps 3-5) -------------------------

Tier = str  # "T1" | "T2" | "T3"


class Contact(BaseModel):
    """A tiered, verification-flagged contact rendered on the page. Maps 1:1 to
    the `contacts[]` entry in the data.json contract that build_artifact.py reads."""

    id: str = ""
    name: str
    title: str = ""
    tier: Tier = "T2"
    li: str = ""                                 # LinkedIn URL (profile, or a search URL for a human check)
    email: str = ""
    email_note: str = ""                         # NO EMAIL / pattern-guess / verified, etc.
    phone: str = ""
    hub: str = ""                                # HubSpot status/label for the contact
    hub_url: str = ""                            # direct link to the contact's HubSpot record
    local: bool = False                          # Denver-metro -> in-person lunch badge

    # verification (drives the mandatory "confirm before outreach" flag in the render)
    verif_status: VerificationStatus = VerificationStatus.NOT_LINKEDIN_VERIFIED
    verif_label: str = ""                        # human-readable badge text
    verif_sources: str = ""                      # which sources were/weren't checked

    # A/B emails + LinkedIn message (populated by drafting, step 4; absent -> no email block renders)
    a_subj: str = ""
    a_body: str = ""
    b_subj: str = ""
    b_body: str = ""
    li_msg: str = ""                             # LinkedIn cold message (Vinci also writes this)

    @property
    def has_emails(self) -> bool:
        return bool(self.a_subj and self.a_body)


class Company(BaseModel):
    """One researched company on the daily slate. Maps to a `companies[]` entry."""

    id: str
    name: str
    domain: str = ""
    vertical: str = ""
    status: str = ""
    last_touch: str = ""                          # ISO date or "" ; "Dormant since <date>"
    hubspot: str = ""                            # HubSpot record URL
    reconnect_ok: bool = False                    # True => "Warm reconnect"; False => "Fresh outreach"
    proof: str = ""                              # customer proof point to reference
    hq_phone: str = ""
    overview: str = ""
    flags: str = ""
    manual: bool = False                          # True => rep added it via "+ Add company"
    contacts: list[Contact] = Field(default_factory=list)


class PageData(BaseModel):
    """The full per-rep payload rendered to HTML (the data.json contract)."""

    generated: str                               # page date, e.g. "2026-07-02"
    signature: str
    companies: list[Company] = Field(default_factory=list)

    def to_data_json(self) -> dict:
        """Exact shape build_artifact.py's JS expects."""
        return {
            "generated": self.generated,
            "signature": self.signature,
            "companies": [
                {
                    "id": c.id, "name": c.name, "domain": c.domain, "vertical": c.vertical,
                    "status": c.status, "last_touch": c.last_touch, "hubspot": c.hubspot,
                    "reconnect_ok": c.reconnect_ok, "proof": c.proof, "hq_phone": c.hq_phone,
                    "overview": c.overview, "flags": c.flags, "manual": c.manual,
                    "contacts": [
                        {
                            "id": ct.id,
                            "tier": ct.tier, "name": ct.name, "title": ct.title, "li": ct.li,
                            "email": ct.email, "email_note": ct.email_note, "phone": ct.phone,
                            "hub": ct.hub, "hub_url": ct.hub_url, "local": ct.local,
                            "verif_status": ct.verif_status.value, "verif_label": ct.verif_label,
                            "verif_sources": ct.verif_sources,
                            **({"a_subj": ct.a_subj, "a_body": ct.a_body,
                                "b_subj": ct.b_subj, "b_body": ct.b_body,
                                "li_msg": ct.li_msg} if ct.has_emails else {}),
                        }
                        for ct in c.contacts
                    ],
                }
                for c in self.companies
            ],
        }
