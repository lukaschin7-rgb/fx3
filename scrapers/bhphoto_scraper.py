"""
B&H Photo used-department scraper.

B&H's search results have historically been more server-rendered than
MPB/KEH, but this still uses the headless-browser path for consistency
and because B&H does lazy-load some result content via JS.

>>> SELECTORS BELOW ARE UNVERIFIED, see README "Troubleshooting the retail
>>> scrapers" if this stops returning results. <<<
"""

from __future__ import annotations

import logging

from scrapers.browser_utils import extract_listing_cards, fetch_rendered_html
from scrapers.config import CREDIT_CARD_PAYABLE

logger = logging.getLogger(__name__)

# shopServiceFilters=Used-Equipment restricts to the used department.
SEARCH_URL = "https://www.bhphotovideo.com/c/search?q={query}&shopServiceFilters=Used-Equipment"

SELECTORS = {
    "card": "[data-selenium='miniProductPage'], .miniProdInfo, li[data-selenium='productItem']",
    "title": "[data-selenium='miniProductPageProductName'], .miniProdInfo__title, a[data-selenium='productItemName']",
    "price": "[data-selenium='uedPrice'], .price, span[data-selenium='ourPrice']",
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
            "condition_text": "Used (see listing for grade)",
            "shutter_count": None,
            "url": c["url"],
            "source": "bhphoto",
            "credit_card_payable": CREDIT_CARD_PAYABLE["bhphoto"],
        }
        for c in cards
    ]
