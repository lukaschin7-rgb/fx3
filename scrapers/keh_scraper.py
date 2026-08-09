"""
KEH scraper.

Like MPB, KEH organizes by one product page per exact item (e.g.
/shop/sony-cinema-line-fx3-full-frame-digital-camera-4k120p-12mp.html)
rather than a keyword-searchable results grid. This is Magento-based
storefront markup (data-ui-id attributes, schema.org itemprop microdata),
which is more stable to select on than auto-generated class names.

Confirmed against real markup pulled from the live site on 2026-08-09:

    <span class="base" data-ui-id="page-title-wrapper" itemprop="name">
      Sony Cinema Line FX3 Full-Frame Digital E-Mount Camera {4K120p/12MP}
    </span>
    ...
    <span class="price">$4,162.00</span>

Condition/grade is NOT extracted here despite KEH clearly showing one
(e.g. "LN-" for "Like New minus") -- the grade badge on the live page is
styled with Tailwind utility classes only (h-1/2, font-bold, etc.) with no
unique class, data-testid, or id to anchor a selector on, so there's no
reliable way to select just that element without also matching unrelated
page furniture. Price + title (and, for the camera, MPB's shutter count)
already cover the essentials; a future pass could look for a stable
ancestor if a real grade breakdown turns out to matter.

Caveat: if KEH offers multiple condition grades for the same item via a
dropdown/selector that updates price without changing the URL, only
whichever price is present in the initial page load gets captured --
this doesn't attempt a grade-by-grade breakdown the way mpb_scraper.py
does for MPB.

A target with no `keh_url` set in scrapers/config.py is skipped (logged,
not an error) until we've confirmed a real URL for it.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from scrapers.browser_utils import fetch_rendered_html

logger = logging.getLogger(__name__)

TITLE_SELECTOR = "[data-ui-id='page-title-wrapper']"
PRICE_SELECTOR = ".price"

_PRICE_RE = re.compile(r"\$\s?([\d][\d,]*(?:\.\d{2})?)")

_page_cache: dict[str, str] = {}


def _get_html(url: str) -> str:
    if url not in _page_cache:
        _page_cache[url] = fetch_rendered_html(url, wait_selector=PRICE_SELECTOR) or ""
    return _page_cache[url]


def search(term: str, target) -> list[dict]:  # noqa: ARG001 -- term unused, single product-page fetch
    url = getattr(target, "keh_url", None)
    if not url:
        logger.info("No confirmed KEH product URL for %s yet -- skipping", target.key)
        return []

    html = _get_html(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one(TITLE_SELECTOR)
    title = title_el.get_text(strip=True) if title_el else target.label

    price_el = soup.select_one(PRICE_SELECTOR)
    if not price_el:
        return []
    price_match = _PRICE_RE.search(price_el.get_text())
    if not price_match:
        return []
    price = float(price_match.group(1).replace(",", ""))

    return [
        {
            "title": title,
            "price": price,
            "currency": "USD",
            "condition_text": None,
            "shutter_count": None,
            "url": url,
            "source": "keh",
        }
    ]
