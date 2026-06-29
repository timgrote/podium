import logging

import httpx

from ..config import settings

logger = logging.getLogger("conductor")

KEYGEN_BASE = "https://api.keygen.sh/v1"
PAGE_SIZE = 100


def fetch_trial_licenses() -> list[dict]:
    """Fetch all Raindrop trial licenses from KeyGen.

    Returns a list of normalized dicts ``{name, email, created, expiry, status}``.
    Returns ``[]`` if the token is unset or on any HTTP error (never raises).
    """
    token = settings.keygen_api_token
    if not token:
        logger.warning("CONDUCTOR_KEYGEN_API_TOKEN not set; skipping trial fetch")
        return []

    url = f"{KEYGEN_BASE}/accounts/{settings.keygen_account_id}/licenses"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.api+json",
    }

    results: list[dict] = []
    page = 1
    try:
        while True:
            params = {
                "policy": settings.keygen_trial_policy_id,
                "page[number]": page,
                "page[size]": PAGE_SIZE,
            }
            resp = httpx.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            for lic in data:
                attrs = lic.get("attributes", {})
                results.append({
                    "name": attrs.get("name") or "",
                    "email": (attrs.get("metadata") or {}).get("email") or "",
                    "created": attrs.get("created"),
                    "expiry": attrs.get("expiry"),
                    "status": attrs.get("status"),
                })
            if len(data) < PAGE_SIZE:
                break
            page += 1
    except Exception as e:
        logger.warning(f"KeyGen trial fetch failed: {e}")
        return []

    return results
