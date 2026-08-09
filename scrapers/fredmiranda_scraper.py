"""
FredMiranda "Buy & Sell" forum scraper (board 10).

Like Reddit's r/photomarket, this is peer-to-peer classifieds, not a
storefront -- not credit-card-payable, and the price usually lives inside
the thread title itself (e.g. "[FS] Sony FX3 body, mint - $2600") rather
than a separate structured field.

Unlike MPB/KEH/B&H/Adorama, forum software is typically server-rendered
rather than a JS single-page app, so this uses a plain HTTP request
(scrapers.http_utils.polite_get -- robots.txt check + rate limiting)
instead of a headless browser. That said, the CSS selector below is still
an unverified guess (this dev environment can't reach fredmiranda.com to
confirm the real markup) -- see README "Troubleshooting the retail
scrapers" if this comes back empty.

The board's listing page is fetched once per run and cached in memory;
every gear target's search terms are matched against that same fetch
rather than re-requesting the page for each one.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from scrapers.http_utils import polite_get

logger = logging.getLogger(__name__)

BOARD_URL = "https://www.fredmiranda.com/forum/board/10/"

# Edit this if the scraper starts returning nothing -- see README.
THREAD_LINK_SELECTOR = "a[href*='/forum/topic/']"

_PRICE_RE = re.compile(r"\$\s?([\d][\d,]*(?:\.\d{2})?)")

_cache: list[dict] | None = None


def _fetch_threads() -> list[dict]:
    global _cache
    if _cache is not None:
        return _cache

    resp = polite_get(BOARD_URL)
    if resp is None:
        _cache = []
        return _cache

    soup = BeautifulSoup(resp.text, "lxml")
    threads: list[dict] = []
    seen_urls: set[str] = set()
    for link in soup.select(THREAD_LINK_SELECTOR):
        title = link.get_text(strip=True)
        href = link.get("href", "")
        if not title or not href:
            continue
        url = href if href.startswith("http") else f"https://www.fredmiranda.com{href}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        threads.append({"title": title, "url": url})

    if not threads:
        logger.warning("No threads found on %s -- selector may need updating", BOARD_URL)

    _cache = threads
    return threads


def search(term: str) -> list[dict]:
    """Only checks the current front page of the board (recent threads) --
    good enough for a daily "what's new" scraper since older threads that
    scroll off get tracked by first-seen date anyway, not re-checked."""
    term_lower = term.lower()
    results = []
    for thread in _fetch_threads():
        if term_lower not in thread["title"].lower():
            continue
        price_match = _PRICE_RE.search(thread["title"])
        price = float(price_match.group(1).replace(",", "")) if price_match else None
        results.append(
            {
                "title": thread["title"],
                "price": price,
                "currency": "USD",
                "condition_text": None,
                "shutter_count": None,
                "url": thread["url"],
                "source": "fredmiranda",
            }
        )
    return results
