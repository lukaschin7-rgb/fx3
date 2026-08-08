"""
Adorama used-department scraper.

>>> SELECTORS BELOW ARE UNVERIFIED, see README "Troubleshooting the retail
>>> scrapers" if this stops returning results. <<<
"""

from __future__ import annotations

import logging

from scrapers.browser_utils import extract_listing_cards, fetch_rendered_html
from scrapers.config import CREDIT_CARD_PAYABLE

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.adorama.com/searchsite/{query}?condition=Used"

SELECTORS = {
    "card": ".card-body, .product-item, [data-testid='product-card']",
    "title": ".card-title, .product-item__title, [data-testid='product-title']",
    "price": ".card-price, .product-item__price, [data-testid='product-price']",
    "link": "a",
}


def search(term: str) -> list[dict]:
    url = SEARCH_URL.format(query=term.replace(" ", "%20"))
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
            "condition_text": "Used (see listing for grade)",
            "shutter_count": None,
            "url": c["url"],
            "source": "adorama",
            "credit_card_payable": CREDIT_CARD_PAYABLE["adorama"],
        }
        for c in cards
    ]
