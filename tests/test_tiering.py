"""Tiering classifier tests: C-suite override, always-T3 families, band matrix,
exclusions, and the 'Vice President' != President edge case."""
from __future__ import annotations

from app.tiering import tier_for, classify_role, Role


def test_csuite_override_all_bands():
    for band_locs in (12, 40, 200, None):
        assert tier_for("Chief Operating Officer", band_locs)[0] == "T1"
        assert tier_for("Founder & CEO", band_locs)[0] == "T1"
        assert tier_for("President", band_locs)[0] == "T1"
        assert tier_for("CFO", band_locs)[0] == "T1"          # CFO is C-suite, beats Finance=T3


def test_vice_president_is_not_csuite():
    assert classify_role("Vice President") is not Role.CSUITE
    # generic VP -> T2 (kept, not elevated to T1)
    assert tier_for("Vice President", 200)[0] == "T2"
    # but a functional VP tiers by function
    assert tier_for("VP of Operations", 200)[0] == "T1"


def test_always_t3_families():
    for locs in (12, 40, 200):
        assert tier_for("Director of Franchise Development", locs)[0] == "T3"
        assert tier_for("Head of People", locs)[0] == "T3"
        assert tier_for("Director of Finance", locs)[0] == "T3"


def test_band_matrix():
    # Support/Compliance are T1 only at 26+; T2 at 10-25
    assert tier_for("Director of Franchise Support", 20)[0] == "T2"
    assert tier_for("Director of Franchise Support", 40)[0] == "T1"
    assert tier_for("Compliance Manager", 200)[0] == "T1"
    assert tier_for("Training Manager", 200)[0] == "T2"


def test_exclusions():
    assert classify_role("Franchisee") is Role.EXCLUDED
    assert classify_role("Franchise Opportunity Consultant") is Role.EXCLUDED
    assert classify_role("Store Manager") is Role.EXCLUDED
    assert tier_for("Barista", 50)[0] == ""


if __name__ == "__main__":
    test_csuite_override_all_bands()
    test_vice_president_is_not_csuite()
    test_always_t3_families()
    test_band_matrix()
    test_exclusions()
    print("all tiering tests passed")
