"""
Shared Playwright helpers for the JS-rendered retail sites (MPB, KEH, B&H,
Adorama all load search results via client-side JavaScript, so a plain
`requests` GET won't see any listings -- a real (headless) browser is
needed).

IMPORTANT / HONEST CAVEAT: the exact CSS selectors in mpb_scraper.py,
keh_scraper.py, bhphoto_scraper.py, and adorama_scraper.py are best-effort
and were NOT verified against the live sites at build time (this dev
environment can't reach those domains). If a scraper starts returning zero
results, the site's markup has likely changed. See README.md ->
"Troubleshooting the retail scrapers" for how to fix it in ~10 minutes
using your phone or laptop browser's dev tools.
"""

from __future__ import annotations

import logging
import random
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrapers.config import DEFAULT_USER_AGENT, REQUEST_DELAY_RANGE
from scrapers.http_utils import is_allowed

logger = logging.getLogger(__name__)

_PRICE_RE = re.compile(r"\$\s?([\d][\d,]*(?:\.\d{2})?)")


def fetch_rendered_html(url: str, wait_selector: str | None = None, timeout_ms: int = 15000) -> str | None:
    """Load `url` in headless Chromium and return the fully-rendered HTML,
    or None if robots.txt disallows it or the page fails to load."""
    if not is_allowed(url):
        logger.warning("robots.txt disallows fetching %s -- skipping", url)
        return None

    time.sleep(random.uniform(*REQUEST_DELAY_RANGE))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=DEFAULT_USER_AGENT)
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=timeout_ms)
                except Exception:  # noqa: BLE001 -- selector may be stale, still return what loaded
                    logger.warning("Timed out waiting for %r on %s -- site markup may have changed", wait_selector, url)
            html = page.content()
            browser.close()
            return html
    except Exception as exc:  # noqa: BLE001 -- never let one site's failure kill the run
        logger.warning("Failed to render %s: %s", url, exc)
        return None


def extract_listing_cards(
    html: str,
    base_url: str,
    card_selector: str | None = None,
    title_selector: str | None = None,
    price_selector: str | None = None,
    link_selector: str | None = None,
) -> list[dict]:
    """Best-effort extraction of (title, price, url) tuples from a search
    results page.

    If `card_selector` etc. are given, they're tried first (this is where
    a site-specific scraper plugs in whatever it discovered via browser
    dev tools). If those don't find anything -- e.g. because the site's
    markup changed -- this falls back to a generic heuristic: find every
    element containing a "$price", then walk up to the nearest ancestor
    that also contains a link, and use that link's text as the title and
    href as the URL. It's not pretty, but it keeps the scraper limping
    along (returning *something*) instead of going to zero silently.
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    if card_selector:
        cards = soup.select(card_selector)
        for card in cards:
            title_el = card.select_one(title_selector) if title_selector else None
            price_el = card.select_one(price_selector) if price_selector else None
            link_el = card.select_one(link_selector) if link_selector else card.find("a", href=True)

            if not (title_el and price_el and link_el):
                continue
            price_match = _PRICE_RE.search(price_el.get_text())
            if not price_match:
                continue
            results.append(
                {
                    "title": title_el.get_text(strip=True),
                    "price": float(price_match.group(1).replace(",", "")),
                    "url": urljoin(base_url, link_el.get("href", "")),
                }
            )
        if results:
            return results
        logger.warning(
            "Site-specific selectors found nothing on %s -- falling back to generic price-based extraction", base_url
        )

    # Generic fallback.
    seen_urls: set[str] = set()
    for price_node in soup.find_all(string=_PRICE_RE):
        price_match = _PRICE_RE.search(price_node)
        if not price_match:
            continue
        container = price_node.parent
        link_el = None
        for _ in range(4):  # walk up a few levels looking for a link + title text
            if container is None:
                break
            link_el = container.find("a", href=True)
            if link_el and link_el.get_text(strip=True):
                break
            container = container.parent
        if not link_el:
            continue
        url = urljoin(base_url, link_el.get("href", ""))
        if url in seen_urls:
            continue
        seen_urls.add(url)
        results.append(
            {
                "title": link_el.get_text(strip=True),
                "price": float(price_match.group(1).replace(",", "")),
                "url": url,
            }
        )

    return results
