"""Rep registry: the single source of truth for every per-rep value.

Loaded from reps.json. NOTHING per-rep (owner id, name, signature, city, area
codes) is hardcoded anywhere else in the app. Google email -> Rep record is the
only mapping used to scope a request to a rep's book.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from .config import get_settings


class Rep(BaseModel):
    email: str
    rep_name: str
    hubspot_owner_id: str
    ae_owner_ids: list[str] = Field(default_factory=list)
    signature: str
    booking_link: str = ""
    home_city: str = ""
    home_area_codes: list[str] = Field(default_factory=list)
    active: bool = True
    role: str = "rep"                            # "rep" | "admin" (admin dashboard, later)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def owned_by_me_owner_ids(self) -> list[str]:
        """AE owner ids whose companies count as mine when adr == my owner id."""
        return self.ae_owner_ids


def _load_raw() -> dict[str, dict]:
    path: Path = get_settings().reps_file
    if not path.exists():
        raise FileNotFoundError(f"reps.json not found at {path.resolve()}")
    data = json.loads(path.read_text())
    # keys beginning with "_" are comments/examples, not real reps
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache
def load_reps() -> dict[str, Rep]:
    """email (lowercased) -> Rep. Fails fast on a malformed/incomplete record."""
    reps: dict[str, Rep] = {}
    for email, cfg in _load_raw().items():
        key = email.strip().lower()
        reps[key] = Rep(email=key, **cfg)
    return reps


def get_rep(email: str) -> Rep | None:
    return load_reps().get(email.strip().lower())


def require_rep(email: str) -> Rep:
    rep = get_rep(email)
    if rep is None:
        raise KeyError(
            f"No rep registered for '{email}'. Add them to reps.json before scoping a request."
        )
    return rep


def active_reps() -> list[Rep]:
    return [r for r in load_reps().values() if r.active]
