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


# NBM seniority-first tiering (per the "Which meetings earn NBM credit" chart):
#   T1 = C-suite / President / Founder / Managing Partner / VP-SVP  (via _is_csuite)
#   T2 = Director or Head-of in a buyer function
#   T3 = manager-level & below, plus HR / Legal / Real Estate / Consultant /
#        FBC / Field / franchise success-support at manager level
# Franchisees / unit / store are EXCLUDED (classify_role).
_ALWAYS_T3_FUNC = [
    "human resources", " hr ", "people operations", "talent",
    "legal", "counsel", "attorney", "paralegal",
    "real estate", "realty",
    "consultant", "advisor", "adviser",
    "franchise business consultant", "fbc", "field consultant", "field coach",
    "business coach", "franchise coach", "field manager",
]


def _is_director(title: str) -> bool:
    if "director" in _tokens(title):
        return True
    return "head of " in f" {(title or '').lower()} "


def tier_for(title: str, location_count: int | None = None) -> tuple[str, Role]:
    """NBM seniority tier. EXCLUDED (franchisee/unit/store) -> ("", EXCLUDED).
    location_count is accepted for signature stability but no longer bands tiers."""
    role = classify_role(title)
    if role is Role.EXCLUDED:
        return "", role
    if _is_csuite(title):                          # C-suite/President/Founder/MP/VP/SVP -> T1
        return "T1", role
    t = f" {(title or '').lower().strip()} "
    if _has(t, _ALWAYS_T3_FUNC):                   # HR/Legal/RealEstate/Consultant/FBC/Field -> T3
        return "T3", role
    if _is_director(title):                        # Director / Head-of a buyer function -> T2
        return "T2", role
    return "T3", role                              # manager-level & below -> T3


# tier sort weight for ordering within a company
TIER_ORDER = {"T1": 0, "T2": 1, "T3": 2}
