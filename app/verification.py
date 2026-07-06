"""Verification status assignment.

The spec's bar: "live LinkedIn in the rep's Chrome is decisive." A server cannot
do that. So:
  - No contact is EVER stamped LINKEDIN_VERIFIED by the server.
  - A contact corroborated by ZoomInfo employmentHistory + Apollo (when those
    providers are configured) reaches ZOOMINFO_CORROBORATED - still flagged.
  - Everything else is NOT_LINKEDIN_VERIFIED.
  - Conflicting/departure signals -> HELD_OUT (do not present as active).

Every status except LINKEDIN_VERIFIED renders the visible
"NOT LINKEDIN-VERIFIED - confirm before outreach" flag plus a one-click LinkedIn
link, so a human closes the loop before any outreach.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from .models import VerificationStatus as VS

CONFIRM_FLAG = "NOT LINKEDIN-VERIFIED - confirm before outreach"

_LABELS = {
    VS.LINKEDIN_VERIFIED: "LinkedIn-verified active",
    VS.ZOOMINFO_CORROBORATED: f"{CONFIRM_FLAG} (ZoomInfo/Apollo corroborated only)",
    VS.COMPANY_PAGE_ONLY: f"{CONFIRM_FLAG} (company page only - may be an outsourced broker)",
    VS.NOT_LINKEDIN_VERIFIED: CONFIRM_FLAG,
    VS.HELD_OUT: "HELD OUT - sources conflict or a departure signal was seen; do NOT contact until confirmed",
}


def label_for(status: VS) -> str:
    return _LABELS[status]


def linkedin_url(existing: str | None, name: str, company: str) -> str:
    """Use the real profile URL if HubSpot/ZoomInfo has one; otherwise build a
    LinkedIn people-search URL so a human can confirm in one click."""
    if existing and "linkedin.com/in/" in existing:
        return existing
    if existing and "linkedin.com" in existing:
        return existing
    q = quote_plus(f"{name} {company}".strip())
    return f"https://www.linkedin.com/search/results/people/?keywords={q}"


def assess(
    *,
    linkedin_checked: bool = False,
    linkedin_current: bool | None = None,
    zoominfo_active: bool | None = None,
    apollo_active: bool | None = None,
    on_company_page: bool | None = None,
    departure_signal: bool = False,
) -> VS:
    """Combine whatever sources ran into a status. Server callers pass
    linkedin_checked=False, so the ceiling is ZOOMINFO_CORROBORATED."""
    if departure_signal:
        return VS.HELD_OUT
    if linkedin_checked and linkedin_current:
        return VS.LINKEDIN_VERIFIED
    if linkedin_checked and linkedin_current is False:
        return VS.HELD_OUT
    if zoominfo_active or apollo_active:
        return VS.ZOOMINFO_CORROBORATED
    if on_company_page:
        return VS.COMPANY_PAGE_ONLY
    return VS.NOT_LINKEDIN_VERIFIED


def sources_note(*, zoominfo: bool, apollo: bool, company_page: bool) -> str:
    checked, missing = [], []
    (checked if zoominfo else missing).append("ZoomInfo")
    (checked if apollo else missing).append("Apollo")
    (checked if company_page else missing).append("company page")
    parts = []
    if checked:
        parts.append("checked: " + ", ".join(checked))
    parts.append("LinkedIn: not checked (server)")
    if missing:
        parts.append("not run: " + ", ".join(missing))
    return "; ".join(parts)
