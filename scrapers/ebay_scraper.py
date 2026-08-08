"""
eBay Browse API scraper.

Requires two environment variables (see README for how to get them):
  EBAY_CLIENT_ID
  EBAY_CLIENT_SECRET

Uses the OAuth2 "client credentials" grant to get an application access
token (no user login involved -- this is read-only public search), then
calls the Browse API's item_summary/search endpoint.

Docs: https://developer.ebay.com/api-docs/buy/browse/overview.html
"""

from __future__ import annotations

import base64
import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
ITEM_URL = "https://api.ebay.com/buy/browse/v1/item/{item_id}"

# Used / very good / good / acceptable -- excludes New / Refurbished.
USED_CONDITION_IDS = "3000|4000|5000|6000"

_token_cache: dict[str, float | str] = {}


def _get_access_token() -> str | None:
    client_id = os.environ.get("EBAY_CLIENT_ID")
    client_secret = os.environ.get("EBAY_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.warning("EBAY_CLIENT_ID / EBAY_CLIENT_SECRET not set -- skipping eBay")
        return None

    cached_token = _token_cache.get("token")
    expires_at = _token_cache.get("expires_at", 0)
    if cached_token and time.time() < expires_at:
        return cached_token  # type: ignore[return-value]

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=20,
    )
    if resp.status_code != 200:
        logger.warning("eBay OAuth token request failed: HTTP %s %s", resp.status_code, resp.text[:200])
        return None

    payload = resp.json()
    token = payload["access_token"]
    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + payload.get("expires_in", 7000) - 60
    return token


_SHUTTER_RE = re.compile(r"shutter\s*count[:\s]*([\d,]+)", re.IGNORECASE)
_ACTUATION_RE = re.compile(r"([\d,]{3,7})\s*(?:actuations|clicks)", re.IGNORECASE)


def _extract_shutter_count(text: str) -> int | None:
    for pattern in (_SHUTTER_RE, _ACTUATION_RE):
        match = pattern.search(text or "")
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _maybe_fetch_shutter_count(token: str, item_id: str) -> int | None:
    """Only called for camera listings -- one extra API call per FX3 result
    to pull the full description and look for a shutter count."""
    try:
        resp = requests.get(
            ITEM_URL.format(item_id=item_id),
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            },
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        description = resp.json().get("description", "")
        return _extract_shutter_count(description)
    except requests.RequestException as exc:
        logger.warning("eBay item detail fetch failed for %s: %s", item_id, exc)
        return None


def search(term: str, category: str) -> list[dict]:
    """Search eBay for `term`. `category` is "camera" or "lens" -- cameras
    get an extra per-item call to look for a shutter count."""
    token = _get_access_token()
    if not token:
        return []

    results: list[dict] = []
    try:
        resp = requests.get(
            SEARCH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            },
            params={
                "q": term,
                "filter": f"conditionIds:{{{USED_CONDITION_IDS}}}",
                "limit": "50",
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        logger.warning("eBay search request failed for %r: %s", term, exc)
        return []

    if resp.status_code != 200:
        logger.warning("eBay search for %r returned HTTP %s: %s", term, resp.status_code, resp.text[:200])
        return []

    for item in resp.json().get("itemSummaries", []):
        title = item.get("title", "")
        price_info = item.get("price", {})
        shutter_count = None
        if category == "camera":
            shutter_count = _extract_shutter_count(title)
            if shutter_count is None:
                shutter_count = _maybe_fetch_shutter_count(token, item.get("itemId", ""))

        results.append(
            {
                "title": title,
                "price": float(price_info.get("value", 0) or 0),
                "currency": price_info.get("currency", "USD"),
                "condition_text": item.get("condition"),
                "shutter_count": shutter_count,
                "url": item.get("itemWebUrl"),
                "source": "ebay",
            }
        )

    return results
