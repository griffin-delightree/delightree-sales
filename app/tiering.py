"""Role detection + size-band tiering, reproduced from the spec.

Sources: KNOWLEDGE.md sec 2, kyle/SKILL.md "SIZE BANDS + TIERING MATRIX",
ENGINE-STANDARDS.md "TIERING", and the canonical overrides:
  - C-SUITE OVERRIDE (2026-06-26): any C-level exec, Founder, or President is
    ALWAYS Tier 1 in EVERY band.
  - Franchise Development / HR / Finance are ALWAYS Tier 3.

Bands by verified current unit count: 10-25, 26-50, 50+.
"""
from __future__ import annotations

import re
from enum import Enum


class Role(str, Enum):
    CSUITE = "c_suite"                  # CEO/CxO/Founder/President/Owner/Principal -> ALWAYS T1
    OPERATIONS = "operations"
    SUPPORT = "franchise_support"
    COMPLIANCE = "compliance_qa"
    TRAINING = "training_ld"
    FBC = "fbc_field"
    REGIONAL_VP = "regional_district_vp"
    GROWTH = "growth"
    FRANCHISE_DEV = "franchise_development"   # ALWAYS T3
    HR = "hr_people"                          # ALWAYS T3
    FINANCE = "finance"                       # ALWAYS T3 (unless CFO -> caught by CSUITE)
    OTHER_ICP = "other_icp"                   # corporate but unclassified -> default T2
    EXCLUDED = "excluded"                     # franchisee / store-level / broker -> drop


# C-suite / T1-seniority detection uses WHOLE-WORD tokens: abbreviations like
# "cto"/"coo" must not match inside words such as "dire[cto]r" or "[coo]rdinator".
# Per the NBM tiers, T1 = C-suite, President, Founder, Managing Partner, VP/SVP.
# NOTE: "owner" is intentionally NOT here — a bare "Owner" at a franchise brand is
# almost always a FRANCHISEE (the customer's customer), so it's excluded below.
# A legitimate corporate owner is essentially always also Founder/CEO/President and
# is caught by those tokens.
_CSUITE_ABBREV = {"ceo", "cfo", "coo", "cmo", "cto", "cso", "cgo", "cio", "cro", "chro", "cxo", "cpo", "cdo"}
_CSUITE_WORDS = {"chief", "founder", "cofounder", "principal"}
_VP_ABBREV = {"vp", "svp", "evp"}


def _tokens(title: str) -> set[str]:
    return set(re.findall(r"[a-z]+", (title or "").lower()))


def _is_csuite(title: str) -> bool:
    toks = _tokens(title)
    if toks & _CSUITE_ABBREV:
        return True
    if toks & _CSUITE_WORDS:
        return True
    if toks & _VP_ABBREV:                            # VP/SVP/EVP in any buyer dept -> T1
        return True
    if "vice" in toks and "president" in toks:       # "Vice President ..." -> T1
        return True
    if "president" in toks:                          # President -> T1
        return True
    if "managing" in toks and "partner" in toks:     # Managing Partner -> T1
        return True
    return False


# Franchisee / unit-level / store-level / broker titles -> never a corporate buyer -> drop.
_EXCLUDED = ["franchisee", "franchise owner", "owner/operator", "owner operator",
             "owner-operator", "operator", "multi-unit owner", "multi unit owner",
             "unit owner", "franchise partner", "store", "barista", "crew member",
             "design consultant", "sales representative", "account executive",
             "franchise opportunit", "franserve", "franchoice", "ifpg", "broker",
             "recruiter", "intern"]
_FRANCHISE_DEV = ["franchise development", "franchise dev", "development director",
                  "director of development", "franchise sales", "franchise recruit"]
_HR = ["human resources", "people ", "people operations", "talent", "recruiting lead", "chro", "hr "]
_FINANCE = ["finance", "financial", "accounting", "controller", "treasurer", "bookkeep"]
_OPERATIONS = ["operation"]
_SUPPORT = ["franchise support", "support", "field support"]
_COMPLIANCE = ["compliance", "quality", " qa", "brand standard", "audit"]
_TRAINING = ["training", "learning", "l&d", "onboarding", "education"]
_FBC = ["franchise business consultant", "fbc", "field consultant", "business coach", "field coach"]
_REGIONAL = ["regional", "district", "area director", "area manager", "area developer"]
_GROWTH = ["growth", "marketing", "revenue"]


def _has(title: str, needles: list[str]) -> bool:
    return any(n in title for n in needles)


def classify_role(title: str) -> Role:
    t = f" {(title or '').lower().strip()} "
    if _has(t, _EXCLUDED):
        return Role.EXCLUDED
    if _is_csuite(title):
        return Role.CSUITE
    # A bare "Owner" (no C-suite/Founder/President signal) at a franchise brand is a
    # franchisee, not corporate HQ -> drop. (Founder/CEO/President owners were caught above.)
    if "owner" in _tokens(title):
        return Role.EXCLUDED
    # ALWAYS-T3 families before the general ops/support matching
    if _has(t, _FRANCHISE_DEV):
        return Role.FRANCHISE_DEV
    if _has(t, _HR):
        return Role.HR
    if _has(t, _FINANCE):
        return Role.FINANCE
    if _has(t, _FBC):
        return Role.FBC
    if _has(t, _COMPLIANCE):
        return Role.COMPLIANCE
    if _has(t, _SUPPORT):
        return Role.SUPPORT
    if _has(t, _TRAINING):
        return Role.TRAINING
    if _has(t, _OPERATIONS):
        return Role.OPERATIONS
    if _has(t, _REGIONAL):
        return Role.REGIONAL_VP
    if _has(t, _GROWTH):
        return Role.GROWTH
    if not (title or "").strip():
        return Role.OTHER_ICP
    return Role.OTHER_ICP


def band_of(location_count: int | None) -> str:
    """10-25 / 26-50 / 50+. Unknown -> assume 50+ (most inclusive; C-suite is T1
    regardless, and this errs toward surfacing more contacts, per exhaustive-coverage)."""
    if location_count is None:
        return "50+"
    if location_count <= 25:
        return "10-25"
    if location_count <= 50:
        return "26-50"
    return "50+"


# Tier tables per band. C-suite handled by override (always T1); the ALWAYS-T3
# families (Franchise Dev / HR / Finance) handled by override too.
_T1 = {
    "10-25": {Role.OPERATIONS},
    "26-50": {Role.OPERATIONS, Role.SUPPORT, Role.COMPLIANCE},
    "50+":  {Role.OPERATIONS, Role.SUPPORT, Role.COMPLIANCE},
}
_T2 = {
    "10-25": {Role.TRAINING, Role.SUPPORT, Role.FBC},
    "26-50": {Role.TRAINING, Role.FBC, Role.REGIONAL_VP, Role.GROWTH},
    "50+":  {Role.TRAINING, Role.FBC, Role.REGIONAL_VP, Role.GROWTH},
}
# everything corporate not in T1/T2 and not an always-T3 family defaults to T2


ALWAYS_T3 = {Role.FRANCHISE_DEV, Role.HR, Role.FINANCE}


def tier_for(title: str, location_count: int | None) -> tuple[str, Role]:
    """Return ("T1"|"T2"|"T3", Role). EXCLUDED roles return ("", EXCLUDED)."""
    role = classify_role(title)
    if role is Role.EXCLUDED:
        return "", role
    if role is Role.CSUITE:                       # C-suite override: always T1
        return "T1", role
    if role in ALWAYS_T3:                          # Franchise Dev / HR / Finance: always T3
        return "T3", role
    band = band_of(location_count)
    if role in _T1[band]:
        return "T1", role
    if role in _T2[band]:
        return "T2", role
    # OTHER_ICP or a role not elevated in this band -> T2 (kept, per exhaustive coverage)
    return "T2", role


# tier sort weight for ordering within a company
TIER_ORDER = {"T1": 0, "T2": 1, "T3": 2}
