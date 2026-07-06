"""Central runtime configuration, loaded from environment / .env.

Only HubSpot + paths are required for steps 1-2; the rest are declared now so the
env is complete but stay optional until their step lands.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- HubSpot ---
    hubspot_token: str = Field(default="", alias="HUBSPOT_TOKEN")
    hubspot_properties_file: str = Field(default="", alias="HUBSPOT_PROPERTIES_FILE")
    # portal id for building record deep-links; auto-fetched if left blank
    hubspot_portal_id: str = Field(default="", alias="HUBSPOT_PORTAL_ID")

    # --- Anthropic (step 4) ---
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-opus-4-8", alias="ANTHROPIC_MODEL")

    # --- Enrichment (step 3) ---
    zoominfo_username: str = Field(default="", alias="ZOOMINFO_USERNAME")
    zoominfo_password: str = Field(default="", alias="ZOOMINFO_PASSWORD")
    zoominfo_client_id: str = Field(default="", alias="ZOOMINFO_CLIENT_ID")
    apollo_api_key: str = Field(default="", alias="APOLLO_API_KEY")

    # --- Google OAuth (step 6) ---
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_hosted_domain: str = Field(default="delightree.com", alias="GOOGLE_HOSTED_DOMAIN")
    oauth_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback", alias="OAUTH_REDIRECT_URI"
    )
    session_secret: str = Field(default="dev-insecure-secret", alias="SESSION_SECRET")
    # HTTPS-only session cookie. Keep False for local http; the deploy sets it True.
    session_https_only: bool = Field(default=False, alias="SESSION_HTTPS_ONLY")
    # First-boot convenience: if credentials.json is empty and this is set, every rep
    # gets this temporary password so the team can log in immediately after deploy.
    bootstrap_password: str = Field(default="", alias="BOOTSTRAP_PASSWORD")

    # --- non-Google team entry (shared link) ---
    # Shared passcode gate for the single team link. Anyone with the link + this
    # code can pick a rep and see that rep's book, so treat it as a shared secret,
    # not per-user auth. Leave blank ONLY for local testing (no gate).
    team_access_code: str = Field(default="", alias="TEAM_ACCESS_CODE")

    # --- Paths ---
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    reps_file: Path = Field(default=Path("./reps.json"), alias="REPS_FILE")

    # --- Engine defaults (overridable per-rep later if needed) ---
    dormancy_days: int = 30
    location_floor: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
