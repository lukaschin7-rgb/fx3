"""
MPB used-gear scraper.

MPB's search results are rendered client-side (React), so this uses a
headless browser (see browser_utils.py) rather than a plain HTTP request.

>>> SELECTORS BELOW ARE UNVERIFIED, see README "Troubleshooting the retail
>>> scrapers" if this stops returning results. <<<
"""

from __future__ import annotations

import logging

from scrapers.browser_utils import extract_listing_cards, fetch_rendered_html
from scrapers.config import CREDIT_CARD_PAYABLE

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.mpb.com/en-us/search?query={query}"

# Edit these if the scraper starts returning nothing -- see README.
SELECTORS = {
    "card": "[data-testid='product-card'], .product-card, li.product-tile",
    "title": "[data-testid='product-title'], .product-card__title, .product-tile__title",
    "price": "[data-testid='product-price'], .product-card__price, .product-tile__price",
    "link": "a",
}


def search(term: str) -> list[dict]:
    url = SEARCH_URL.format(query=term.replace(" ", "+"))
    html = fetch_rendered_html(url, wait_selector=SELECTORS["card"])
    if not html:
        return []

    cards = extract_listing_cards(
        html,
        base_url=url,
        card_selector=SELECTORS["card"],
        title_selector=SELECTORS["title"],
        price_selector=SELECTORS["price"],
        link_selector=SELECTORS["link"],
    )

    return [
        {
            "title": c["title"],
            "price": c["price"],
            "currency": "USD",
            "condition_text": None,
            "shutter_count": None,
            "url": c["url"],
            "source": "mpb",
            "credit_card_payable": CREDIT_CARD_PAYABLE["mpb"],
        }
        for c in cards
    ]
