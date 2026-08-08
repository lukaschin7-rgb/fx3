"""
Sanity-checks a scraped result before it's allowed anywhere near the
database. Every scraper here is either an official API (trustworthy) or
best-effort HTML scraping against a page whose markup we couldn't verify
live (not trustworthy) -- this module is the safety net for the latter.

A scraper returning zero results is an obvious, visible failure (it shows
up as "0 listings" and gets noticed). A scraper returning *wrong* results
-- a stray "Add to Cart" button, an unrelated accessory that happens to
mention the camera in its title -- is silent and much worse, since it
looks like real data on the dashboard. This is that check.
"""

from __future__ import annotations

from scrapers.config import ACCESSORY_TITLE_KEYWORDS, MIN_PLAUSIBLE_PRICE, UI_JUNK_TITLES


def is_plausible_listing(title: str, price: float | None, category: str) -> bool:
    if not title or not title.strip():
        return False

    normalized = title.strip().lower()

    if normalized in UI_JUNK_TITLES:
        return False

    if len(normalized.split()) < 3:
        # Real product titles are descriptive ("Sony FX3 Body Only Used");
        # anything this short is almost certainly scraped UI chrome.
        return False

    if any(keyword in normalized for keyword in ACCESSORY_TITLE_KEYWORDS):
        return False

    if price is not None:
        floor = MIN_PLAUSIBLE_PRICE.get(category)
        if floor is not None and price < floor:
            return False

    return True
