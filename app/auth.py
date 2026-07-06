"""Authentication + rep scoping.

Two ways in, both resolving to a Rep record (which carries the HubSpot owner_id
that scopes every data access):

  1. Google OAuth (production SSO) - active when GOOGLE_CLIENT_ID/SECRET are set.
     The authenticated Google email is matched to a rep in reps.json, and the
     Workspace hosted-domain is enforced.
  2. Signed magic-links (for testing / immediate rollout) - a per-rep URL signed
     with SESSION_SECRET. Lets you push a working link to each rep before the
     Google OAuth client is stood up.

Scoping rule: the rep is ALWAYS derived from the session, never from a URL
parameter, so a rep can only ever reach their own owner_id's data.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .config import get_settings
from .registry import Rep, get_rep

MAGIC_SALT = "delightree-magic-link"
SESSION_EMAIL_KEY = "rep_email"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt=MAGIC_SALT)


def make_magic_token(email: str) -> str:
    return _serializer().dumps(email.strip().lower())


def verify_magic_token(token: str, max_age_days: int = 30) -> str | None:
    try:
        return _serializer().loads(token, max_age=max_age_days * 86400)
    except (BadSignature, SignatureExpired):
        return None


def google_configured() -> bool:
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret)


def rep_from_session(session: dict) -> Rep | None:
    email = session.get(SESSION_EMAIL_KEY)
    return get_rep(email) if email else None


# ---------------------------- per-user passwords ----------------------------
# Salted PBKDF2 hashes, stored in a gitignored file under DATA_DIR (never in
# reps.json, never plaintext). Format: pbkdf2_sha256$<iters>$<salt_hex>$<hash_hex>

_PBKDF2_ITERS = 200_000


def _creds_path() -> Path:
    d = get_settings().data_dir
    d.mkdir(parents=True, exist_ok=True)
    return d / "credentials.json"


def _load_creds() -> dict[str, str]:
    p = _creds_path()
    return json.loads(p.read_text()) if p.exists() else {}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERS)
    return f"pbkdf2_sha256${_PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def _verify(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def set_password(email: str, password: str) -> None:
    creds = _load_creds()
    creds[email.strip().lower()] = hash_password(password)
    _creds_path().write_text(json.dumps(creds, indent=2))


def has_password(email: str) -> bool:
    return email.strip().lower() in _load_creds()


def check_password(email: str, password: str) -> bool:
    stored = _load_creds().get(email.strip().lower())
    return bool(stored) and _verify(password, stored)
