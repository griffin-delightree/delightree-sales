"""Thin async HubSpot REST client. Read-only for v1 (we NEVER write back).

Single private-app token from settings; per-rep scoping is enforced by the
callers (eligibility builds owner-scoped filters). This client itself is
account-wide, so every query MUST carry an owner/adr filter.
"""
from __future__ import annotations

from typing import Any, Iterator

import httpx

from ..config import get_settings

BASE = "https://api.hubapi.com"
SEARCH_PAGE_LIMIT = 100  # HubSpot search API max page size


class HubSpotError(RuntimeError):
    pass


class HubSpotClient:
    def __init__(self, token: str | None = None, timeout: float = 30.0):
        self._token = token or get_settings().hubspot_token
        if not self._token:
            raise HubSpotError("HUBSPOT_TOKEN is not set (.env).")
        self._client = httpx.AsyncClient(
            base_url=BASE,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )

    async def __aenter__(self) -> "HubSpotClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, json: dict) -> dict:
        r = await self._client.post(path, json=json)
        if r.status_code >= 400:
            raise HubSpotError(f"HubSpot {r.status_code} on {path}: {r.text[:500]}")
        return r.json()

    async def search(
        self,
        object_type: str,
        filter_groups: list[dict],
        properties: list[str],
        *,
        sorts: list[dict] | None = None,
        max_results: int | None = None,
    ) -> list[dict]:
        """Run a CRM search across all pages (filter_groups are OR'd together;
        filters within a group are AND'd). Returns the raw result objects.
        """
        path = f"/crm/v3/objects/{object_type}/search"
        results: list[dict] = []
        after: str | None = None
        while True:
            payload: dict[str, Any] = {
                "filterGroups": filter_groups,
                "properties": properties,
                "limit": SEARCH_PAGE_LIMIT,
            }
            if sorts:
                payload["sorts"] = sorts
            if after:
                payload["after"] = after
            data = await self._post(path, payload)
            results.extend(data.get("results", []))
            if max_results and len(results) >= max_results:
                return results[:max_results]
            after = (data.get("paging", {}).get("next") or {}).get("after")
            if not after:
                break
        return results

    async def get_portal_id(self) -> str:
        """Fetch the account portal id (for record deep-links). Empty on failure."""
        try:
            r = await self._client.get("/account-info/v3/details")
            if r.status_code < 400:
                return str(r.json().get("portalId", "") or "")
        except httpx.HTTPError:
            pass
        return ""

    async def list_owners(self) -> list[dict]:
        """Every HubSpot user/owner (id, email, firstName, lastName). Paginated.
        Needs the private-app scope crm.objects.owners.read."""
        owners: list[dict] = []
        after: str | None = None
        while True:
            params: dict[str, Any] = {"limit": 100}
            if after:
                params["after"] = after
            r = await self._client.get("/crm/v3/owners/", params=params)
            if r.status_code >= 400:
                raise HubSpotError(f"HubSpot {r.status_code} on /owners: {r.text[:300]}")
            data = r.json()
            owners.extend(data.get("results", []))
            after = (data.get("paging", {}).get("next") or {}).get("after")
            if not after:
                break
        return owners

    async def get_owner(self, owner_id: str) -> dict:
        r = await self._client.get(f"/crm/v3/owners/{owner_id}")
        if r.status_code >= 400:
            raise HubSpotError(f"HubSpot {r.status_code} on owner {owner_id}: {r.text[:300]}")
        return r.json()


def chunked(seq: list, n: int) -> Iterator[list]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]
