"""HubSpot property INTERNAL NAMES, centralized and overridable.

Standard HubSpot properties have stable internal names (safe defaults below).
CUSTOM properties (adr, company_status, vertical, location_count) almost
certainly have portal-specific internal names that differ from these guesses.

>>> ACTION FOR REVOPS: verify the four CUSTOM names against your portal before
    running step 2 against live data. Fastest check: the connected-HubSpot
    "get properties for companies" call, or Settings > Properties in the UI.
    Override any that differ via HUBSPOT_PROPERTIES_FILE (a JSON file) so no
    code changes are needed.

Example override file (HUBSPOT_PROPERTIES_FILE):
    { "adr": "adr_owner", "company_status": "prospecting_status",
      "vertical": "industry_vertical", "location_count": "of_locations" }
"""
from __future__ import annotations

import json
from functools import lru_cache

from ..config import get_settings

# logical name -> HubSpot internal name
DEFAULTS: dict[str, str] = {
    # --- standard HubSpot company properties (stable) ---
    "name": "name",
    "domain": "domain",
    "hubspot_owner_id": "hubspot_owner_id",
    "open_deals": "hs_num_open_deals",
    "notes_last_contacted": "notes_last_contacted",   # excludes marketing email, per HubSpot
    "lifecyclestage": "lifecyclestage",
    "recent_deal_amount": "recent_deal_amount",
    "phone": "phone",                                  # HQ main line
    # --- CUSTOM properties (VERIFIED against live schema 2026-07-02) ---
    "adr": "adr",                                      # enumeration; values ARE owner ids (Justin=83840653)
    "company_status": "company_status",                # enumeration; see EXCLUDED_STATUS_VALUES
    "vertical": "industry_mapped",                     # "Industry (Mapped)" - 8-category taxonomy, card label
    "location_count": "total_location_count",          # "Total Location Count" (current franchise unit count)
    "location_count_fallback": "locations",            # "Open Locations" - used only if primary is empty
}

# company_status STORED VALUES that DISQUALIFY (case-insensitive contains-match in code).
# NOTE: stored value != display label (e.g. "Actively Prospecting" shows as "Working").
# "Recycle" stays eligible, per spec.
EXCLUDED_STATUS_VALUES: list[str] = [
    "Blacklist",
    "Not Prospectable: Parent Brand",
]

# company_status STORED VALUES that stay ELIGIBLE but drop to priority 2 (surfaced
# after all P1 companies). "No Contacts" means HubSpot has no associated contacts, so
# the engine must source everyone net-new -> worth doing, just lower priority.
DEPRIORITIZED_STATUS_VALUES: list[str] = [
    "Not Prospectable: No Contacts",
]

# lifecyclestage STORED VALUES that DISQUALIFY (already sold). Verified from schema:
#   "customer"  -> "Active Customer"
#   "252674132" -> "Onboarding Customer"
# ("252719626"/Churned and "252696617"/Partner are intentionally NOT excluded here.)
EXCLUDED_LIFECYCLE_VALUES: list[str] = ["customer", "252674132"]


@lru_cache
def props() -> dict[str, str]:
    """Merged property map: DEFAULTS overlaid with the optional override file."""
    merged = dict(DEFAULTS)
    path = get_settings().hubspot_properties_file
    if path:
        overrides = json.loads(open(path).read())
        merged.update({k: v for k, v in overrides.items() if k in DEFAULTS})
    return merged


def p(logical: str) -> str:
    """Internal name for a logical property, e.g. p('open_deals') -> 'hs_num_open_deals'."""
    return props()[logical]


def all_internal_names() -> list[str]:
    return list(props().values())
