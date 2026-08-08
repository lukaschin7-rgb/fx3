"""
Near-duplicate detection across sources.

Exact duplicates (same source + same URL seen again on a later run) are
handled in data/storage.py via an upsert on (source, url).

This module handles the harder case: the *same physical listing* showing
up on two different sites (e.g. a seller cross-posts to both eBay and
Reverb), or a site re-listing the same item under a slightly different
title. We flag these as a duplicate group rather than dropping them
outright -- the dashboard shows the first-seen one as primary and
collapses the rest under "also listed on".
"""

from __future__ import annotations

import difflib
import re

PRICE_TOLERANCE = 0.03  # 3% -- covers cross-site fee differences
TITLE_SIMILARITY_THRESHOLD = 0.82


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def titles_similar(a: str, b: str) -> bool:
    ratio = difflib.SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()
    return ratio >= TITLE_SIMILARITY_THRESHOLD


def prices_close(a: float, b: float) -> bool:
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(a, b) <= PRICE_TOLERANCE


def find_duplicate_group(new_listing: dict, existing_listings: list[dict]) -> int | None:
    """Given a freshly-scraped listing and the listings already in the DB
    for the same gear target, return the dedupe_group_id of a match, or
    None if this looks like a genuinely distinct listing.

    `existing_listings` should already be filtered to the same
    `target_key` (and ideally the same category) before calling this --
    we don't cross-match a lens against a camera.
    """
    for existing in existing_listings:
        if existing.get("source") == new_listing.get("source") and existing.get("url") == new_listing.get("url"):
            # Handled by upsert, but just in case it's passed in here too.
            return existing.get("dedupe_group_id")
        if prices_close(new_listing.get("price", 0), existing.get("price", 0)) and titles_similar(
            new_listing.get("title", ""), existing.get("title", "")
        ):
            return existing.get("dedupe_group_id") or existing.get("id")
    return None
