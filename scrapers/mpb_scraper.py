"""
MPB scraper.

Unlike a typical keyword-search results grid, MPB organizes by one product
page per exact item (e.g. /en-us/product/sony-pxw-fx3), with every
condition/grade MPB currently has in stock priced on that same page. So
instead of searching, this fetches the known product-page URL for a
target (GearTarget.mpb_url) and reads off each grade as its own listing.

Confirmed against real markup pulled from the live site (via browser dev
tools) on 2026-08-09 -- unlike the other retail scrapers, these selectors
were verified, not guessed:

    <div class="highlights-container">
      <div class="sc-ERObt btSVfv">
        <h4 class="... price" data-testid="product-card__price__price" ...>$4,049</h4>
      </div>
      <span class="... formatted-condition" data-testid="formatted-condition">
        Cosmetic condition: <span class="condition-wrapper">Excellent</span>
      </span>
      <ul class="...">
        <li>
          <span class="attribute-label" data-testid="product-card__attributes__attribute-label">Shutter count: </span>
          <span class="attribute-value" data-testid="product-card__attributes__attribute-value">3,291</span>
        </li>
      </ul>
    </div>

Note the `data-testid` attributes are used for selection, not the `sc-xxxxx`
classes next to them -- those are auto-generated styled-components hashes
that change on every MPB deploy and would break the scraper immediately.

Caveat: if MPB hides some grades behind a tab/accordion that needs a click
to reveal (rather than all grades being present in the initial page load),
only the default-shown grade(s) will be captured here. Flagged as a
possible follow-up if the dashboard seems to be missing grades you can see
on the site.

A target with no `mpb_url` set in scrapers/config.py is simply skipped
(logged, not an error) until we've confirmed a real URL for it.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from scrapers.browser_utils import fetch_rendered_html

logger = logging.getLogger(__name__)

CARD_SELECTOR = ".highlights-container"
PRICE_SELECTOR = "[data-testid='product-card__price__price']"
CONDITION_SELECTOR = "[data-testid='formatted-condition'] .condition-wrapper"
ATTR_LABEL_SELECTOR = "[data-testid='product-card__attributes__attribute-label']"
ATTR_VALUE_SELECTOR = "[data-testid='product-card__attributes__attribute-value']"

_PRICE_RE = re.compile(r"\$\s?([\d][\d,]*(?:\.\d{2})?)")

_page_cache: dict[str, str] = {}


def _get_html(url: str) -> str:
    if url not in _page_cache:
        _page_cache[url] = fetch_rendered_html(url, wait_selector=CARD_SELECTOR) or ""
    return _page_cache[url]


def _extract_shutter_count(card) -> int | None:
    for li in card.select("ul li"):
        label_el = li.select_one(ATTR_LABEL_SELECTOR)
        value_el = li.select_one(ATTR_VALUE_SELECTOR)
        if not (label_el and value_el):
            continue
        if "shutter" in label_el.get_text(strip=True).lower():
            digits = re.sub(r"[^\d]", "", value_el.get_text())
            return int(digits) if digits else None
    return None


def search(term: str, target) -> list[dict]:  # noqa: ARG001 -- term unused, kept for a uniform scraper interface
    url = getattr(target, "mpb_url", None)
    if not url:
        logger.info("No confirmed MPB product URL for %s yet -- skipping", target.key)
        return []

    html = _get_html(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    results = []
    for card in soup.select(CARD_SELECTOR):
        price_el = card.select_one(PRICE_SELECTOR)
        if not price_el:
            continue
        price_match = _PRICE_RE.search(price_el.get_text())
        if not price_match:
            continue
        price = float(price_match.group(1).replace(",", ""))

        condition_el = card.select_one(CONDITION_SELECTOR)
        condition_text = condition_el.get_text(strip=True) if condition_el else None

        shutter_count = _extract_shutter_count(card) if target.category == "camera" else None

        title_bits = [target.label]
        if condition_text:
            title_bits.append(condition_text)
        title = " - ".join(title_bits)

        # All grades live on the same page, so give each its own synthetic
        # URL fragment to keep them distinct for dedup/first-seen tracking --
        # it still points at the real product page when clicked.
        variant_id = f"{condition_text or 'na'}-{shutter_count or price}".lower().replace(" ", "-")
        variant_url = f"{url}#{variant_id}"

        results.append(
            {
                "title": title,
                "price": price,
                "currency": "USD",
                "condition_text": condition_text,
                "shutter_count": shutter_count,
                "url": variant_url,
                "source": "mpb",
            }
        )

    return results
