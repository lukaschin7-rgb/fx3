"""
Reddit scraper -- r/photomarket and r/AVexchange.

Uses Reddit's read-only public JSON endpoints (no OAuth app needed) with a
descriptive User-Agent, per Reddit's API rules. This is the "lighter-touch
alternative" used in place of Facebook Marketplace / Craigslist, which are
both aggressively bot-protected and not worth the maintenance burden for a
personal project.

Note: these are peer-to-peer classifieds posts, not storefronts, so they're
tagged as NOT credit-card-payable (usually PayPal G&S / F&F, cash, etc.)
and get correspondingly lower ranking priority.
"""

from __future__ import annotations

import logging
import time

import requests

from scrapers.config import REDDIT_SUBREDDITS, REDDIT_USER_AGENT

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.reddit.com/r/{subreddit}/search.json"


def search(term: str) -> list[dict]:
    results: list[dict] = []
    for subreddit in REDDIT_SUBREDDITS:
        try:
            resp = requests.get(
                SEARCH_URL.format(subreddit=subreddit),
                headers={"User-Agent": REDDIT_USER_AGENT},
                params={"q": term, "restrict_sr": 1, "sort": "new", "limit": 25},
                timeout=20,
            )
        except requests.RequestException as exc:
            logger.warning("Reddit search failed for r/%s %r: %s", subreddit, term, exc)
            continue

        if resp.status_code != 200:
            logger.warning("Reddit search for r/%s %r returned HTTP %s", subreddit, term, resp.status_code)
            continue

        for child in resp.json().get("data", {}).get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            # Selling posts on these subreddits conventionally start with
            # "[USA-XX] [H] <gear> [W] PayPal/Venmo" or similar -- we don't
            # try to be clever about parsing that, just surface the post
            # and let a human glance at it. Price is rarely structured, so
            # it's left blank (ranked last within its group, price ascending
            # sort just puts it at the top since 0/None sorts first --
            # dashboard shows "see post" instead of a $0 price in that case).
            results.append(
                {
                    "title": title,
                    "price": None,
                    "currency": "USD",
                    "condition_text": None,
                    "shutter_count": None,
                    "url": f"https://www.reddit.com{post.get('permalink', '')}",
                    "source": "reddit",
                }
            )

        time.sleep(1.5)  # be polite between subreddit calls

    return results
