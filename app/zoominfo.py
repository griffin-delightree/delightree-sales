"""ZoomInfo API client — net-new contact sourcing (OAuth2 client-credentials).

Flow (per ZoomInfo docs, docs.zoominfo.com):
  auth   : POST /gtm/oauth/v1/token   (Basic client_id:client_secret, grant_type=client_credentials)
  search : POST /gtm/data/v1/contacts/search
  enrich : POST /gtm/data/v1/contacts/enrich

Gated on ZOOMINFO_CLIENT_ID + ZOOMINFO_CLIENT_SECRET. No creds -> configured() is
False -> every function is a no-op. Every sourced contact is still flagged
NOT-LINKEDIN-VERIFIED downstream, same as any other.

Response shapes vary (JSON:API), so parsing is deliberately defensive — the
/admin/zoominfo-test endpoint returns the RAW payloads so we can confirm/tune.
"""
from __future__ import annotations

import base64
import time

import httpx

from .config import get_settings

BASE = "https://api.zoominfo.com/gtm"

_token: dict = {"value": None, "exp": 0.0}


def _website(domain: str) -> str:
    """ZoomInfo's companyWebsite wants http://www.example.com format, not a bare domain."""
    d = (domain or "").strip().lower()
    for pre in ("https://", "http://"):
        if d.startswith(pre):
            d = d[len(pre):]
    if d.startswith("www."):
        d = d[4:]
    d = d.split("/")[0]
    return f"http://www.{d}" if d else ""


def _search_attrs(company_name: str = "", domain: str = "") -> dict:
    """Company match criteria for a contact search — prefer domain (precise)."""
    if domain:
        w = _website(domain)
        if w:
            return {"companyWebsite": w}
    if company_name:
        return {"companyName": company_name}
    return {}


def configured() -> bool:
    s = get_settings()
    return bool(s.zoominfo_client_id and s.zoominfo_client_secret)


async def _get_token(client: httpx.AsyncClient) -> str | None:
    now = time.time()
    if _token["value"] and now < _token["exp"] - 60:
        return _token["value"]
    if not configured():
        return None
    s = get_settings()
    basic = base64.b64encode(f"{s.zoominfo_client_id}:{s.zoominfo_client_secret}".encode()).decode()
    r = await client.post(
        f"{BASE}/oauth/v1/token",
        headers={"Authorization": f"Basic {basic}",
                 "Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"},
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    j = r.json()
    _token["value"] = j.get("access_token")
    _token["exp"] = now + int(j.get("expires_in", 3600) or 3600)
    return _token["value"]


def _records(payload: dict) -> list[dict]:
    """Pull contact records out of a JSON:API-ish response, tolerant of shape.
    Handles {data:[{id,attributes:{}}]}, {data:{data:[...]}}, {results:[...]}, etc."""
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    # unwrap one level of nesting if attributes wraps the list
    if isinstance(data, dict):
        for k in ("data", "results", "contacts", "attributes"):
            v = data.get(k)
            if isinstance(v, list):
                data = v
                break
        else:
            if isinstance(data.get("attributes"), dict):
                data = [data]
    if not isinstance(data, list):
        data = payload.get("results") or payload.get("contacts") or []
    out = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        # flatten {id, attributes:{...}} -> single dict
        merged = dict(item)
        if isinstance(item.get("attributes"), dict):
            merged = {**item["attributes"], **{"id": item.get("id", item["attributes"].get("id"))}}
        out.append(merged)
    return out


def _linkedin_from(rec: dict) -> str:
    for u in (rec.get("externalUrls") or []):
        if not isinstance(u, dict):
            continue
        t = str(u.get("type", "")).lower()
        url = u.get("url") or ""
        if "linkedin" in t or "linkedin.com" in url.lower():
            return url
    return rec.get("linkedInUrl") or rec.get("linkedin_url") or ""


# Rank search results so we enrich decision-makers first (enrich is what costs credits).
_TITLE_PRIORITY = [
    "chief", "ceo", "coo", "cfo", "cmo", "president", "founder", "owner",
    "vice president", "vp", "head of", "franchise", "director of operations",
    "operations", "director", "general manager",
]


def _title_rank(title: str) -> int:
    t = (title or "").lower()
    for i, kw in enumerate(_TITLE_PRIORITY):
        if kw in t:
            return i
    return 99


async def source_contacts(*, company_name: str = "", domain: str = "", cap: int = 8) -> list[dict]:
    """Return up to `cap` net-new contacts for a company as normalized dicts:
    {name, first, last, title, email, phone, mobile, linkedin, zi_id}. [] on any
    problem (never raises to the caller)."""
    if not configured():
        return []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            token = await _get_token(client)
            if not token:
                return []
            hdr = {"Authorization": f"Bearer {token}",
                   "Content-Type": "application/vnd.api+json", "Accept": "application/vnd.api+json"}
            attrs = _search_attrs(company_name, domain)
            if not attrs:
                return []
            sr = await client.post(f"{BASE}/data/v1/contacts/search", headers=hdr,
                                   json={"data": {"type": "ContactSearch", "attributes": attrs}})
            sr.raise_for_status()
            found = _records(sr.json())
            # enrich the most senior first (credit control + relevance)
            found.sort(key=lambda r: _title_rank(r.get("jobTitle") or r.get("title") or ""))
            ids = [r.get("id") for r in found if r.get("id")][:cap]
            if not ids:
                return []
            er = await client.post(f"{BASE}/data/v1/contacts/enrich", headers=hdr, json={"data": {
                "type": "ContactEnrich",
                "attributes": {
                    "matchPersonInput": [{"personId": i} for i in ids],
                    "outputFields": ["id", "firstName", "lastName", "jobTitle", "email",
                                     "phone", "mobilePhone", "externalUrls"],
                    "requiredFields": ["id"],
                }}})
            er.raise_for_status()
            out = []
            for rec in _records(er.json()):
                first, last = rec.get("firstName") or "", rec.get("lastName") or ""
                name = f"{first} {last}".strip()
                if not name:
                    continue
                out.append({
                    "zi_id": rec.get("id"), "name": name, "first": first, "last": last,
                    "title": rec.get("jobTitle") or "",
                    "email": rec.get("email") or "",
                    "phone": rec.get("phone") or "", "mobile": rec.get("mobilePhone") or "",
                    "linkedin": _linkedin_from(rec),
                })
            return out
    except (httpx.HTTPError, ValueError, KeyError):
        return []


async def diagnostic(company_name: str = "", domain: str = "") -> dict:
    """Run auth + a sample search + enrich and return RAW payloads for verification.
    Used by /admin/zoominfo-test. Never raises — reports the failure instead."""
    if not configured():
        s = get_settings()
        return {"ok": False, "step": "config",
                "ZOOMINFO_CLIENT_ID_visible": bool(s.zoominfo_client_id),
                "ZOOMINFO_CLIENT_SECRET_visible": bool(s.zoominfo_client_secret),
                "hint": "Both must be true. If either is false, that env var name isn't matching "
                        "exactly (underscores, no quotes/spaces) or the deploy with it isn't Live yet.",
                "error": "credentials not visible to the app"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                token = await _get_token(client)
            except httpx.HTTPStatusError as e:
                return {"ok": False, "step": "auth", "status": e.response.status_code,
                        "error": e.response.text[:500]}
            if not token:
                return {"ok": False, "step": "auth", "error": "no access_token returned"}
            hdr = {"Authorization": f"Bearer {token}",
                   "Content-Type": "application/vnd.api+json", "Accept": "application/vnd.api+json"}
            attrs = _search_attrs(company_name, domain) or {"companyName": company_name or "ZoomInfo"}
            sr = await client.post(f"{BASE}/data/v1/contacts/search", headers=hdr,
                                   json={"data": {"type": "ContactSearch", "attributes": attrs}})
            search_json = _safe_json(sr)
            found = _records(search_json)
            ids = [r.get("id") for r in found if r.get("id")][:3]
            enrich_json = None
            if ids:
                er = await client.post(f"{BASE}/data/v1/contacts/enrich", headers=hdr, json={"data": {
                    "type": "ContactEnrich",
                    "attributes": {"matchPersonInput": [{"personId": i} for i in ids],
                                   "outputFields": ["id", "firstName", "lastName", "jobTitle",
                                                    "email", "phone", "mobilePhone", "externalUrls"],
                                   "requiredFields": ["id"]}}})
                enrich_json = _safe_json(er)
            return {
                "ok": sr.status_code < 400,
                "auth": "ok (token received)",
                "search_status": sr.status_code,
                "search_found": len(found),
                "search_raw": _truncate(search_json),
                "enrich_raw": _truncate(enrich_json),
                "parsed_preview": _records(enrich_json) if enrich_json else [],
            }
    except httpx.HTTPError as e:
        return {"ok": False, "step": "request", "error": str(e)[:500]}


def _safe_json(resp: httpx.Response):
    try:
        return resp.json()
    except ValueError:
        return {"_non_json_body": resp.text[:1000], "_status": resp.status_code}


def _truncate(obj, limit: int = 4000):
    import json
    if obj is None:
        return None
    s = json.dumps(obj)[:limit]
    return s
