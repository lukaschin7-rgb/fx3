"""
Reverb API scraper.

Heads up: Reverb is primarily a musical-instrument marketplace. It does
have broader "Pro Audio / Video" and camera-adjacent categories, but
inventory for cameras and lenses will likely be thinner than the photo-
specific sites. This scraper is included because it was asked for and
costs nothing to run -- it just may not turn up much.

Requires one environment variable (see README):
  REVERB_API_TOKEN

Docs: https://www.reverb.com/page/api
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.reverb.com/api/listings"


def search(term: str) -> list[dict]:
    token = os.environ.get("REVERB_API_TOKEN")
    headers = {
        "Accept": "application/hal+json",
        "Accept-Version": "3.0",
        "Content-Type": "application/hal+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        logger.warning("REVERB_API_TOKEN not set -- calling Reverb unauthenticated (limited results)")

    try:
        resp = requests.get(
            SEARCH_URL,
            headers=headers,
            params={"query": term, "condition": "used", "per_page": 50},
            timeout=20,
        )
    except requests.RequestException as exc:
        logger.warning("Reverb search request failed for %r: %s", term, exc)
        return []

    if resp.status_code != 200:
        logger.warning("Reverb search for %r returned HTTP %s: %s", term, resp.status_code, resp.text[:200])
        return []

    results = []
    for listing in resp.json().get("listings", []):
        price = listing.get("price", {}) or {}
        results.append(
            {
                "title": listing.get("title", ""),
                "price": float(price.get("amount", 0) or 0),
                "currency": price.get("currency", "USD"),
                "condition_text": (listing.get("condition") or {}).get("display_name"),
                "shutter_count": None,
                "url": (listing.get("_links", {}).get("web", {}) or {}).get("href"),
                "source": "reverb",
            }
        )
    return results
