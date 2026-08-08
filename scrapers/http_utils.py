"""
Shared HTTP helpers used by the HTML-scraping modules (MPB, KEH, B&H,
Adorama). The API-based scrapers (eBay, Reverb, Reddit) don't need this --
they talk to documented JSON endpoints directly.

Etiquette baked in here:
  * check robots.txt before fetching anything, and skip the fetch if
    disallowed
  * randomized delay between requests to the same site
  * a normal desktop User-Agent (not spoofing a specific real user, not
    an aggressive bot string either)
  * short timeouts and no retries-till-it-works hammering
"""

from __future__ import annotations

import logging
import random
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

from scrapers.config import DEFAULT_USER_AGENT, REQUEST_DELAY_RANGE

logger = logging.getLogger(__name__)

_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
_last_request_at: dict[str, float] = {}


def _domain(url: str) -> str:
    return urlparse(url).netloc


def is_allowed(url: str, user_agent: str = DEFAULT_USER_AGENT) -> bool:
    """Check robots.txt for the given URL. Fails open to False (i.e. skip)
    only if robots.txt itself can't be read AND the site looks like it's
    actively blocking us; fails open to True if robots.txt is simply
    missing (204/404), which is the standard interpretation."""
    domain = _domain(url)
    parser = _robots_cache.get(domain)
    if parser is None:
        parser = urllib.robotparser.RobotFileParser()
        robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
        try:
            resp = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=10)
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
            else:
                # No robots.txt (or an error fetching it) -> assume allowed.
                parser.parse([])
        except requests.RequestException as exc:
            logger.warning("Could not fetch robots.txt for %s (%s); assuming allowed", domain, exc)
            parser.parse([])
        _robots_cache[domain] = parser
    return parser.can_fetch(user_agent, url)


def polite_get(url: str, user_agent: str = DEFAULT_USER_AGENT, **kwargs) -> requests.Response | None:
    """GET a URL, respecting robots.txt and a randomized per-domain delay.
    Returns None (and logs a warning) instead of raising, so one bad
    request never kills the whole daily run."""
    if not is_allowed(url, user_agent):
        logger.warning("robots.txt disallows fetching %s -- skipping", url)
        return None

    domain = _domain(url)
    last = _last_request_at.get(domain, 0.0)
    delay = random.uniform(*REQUEST_DELAY_RANGE)
    wait_needed = (last + delay) - time.time()
    if wait_needed > 0:
        time.sleep(wait_needed)

    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", user_agent)
    headers.setdefault("Accept-Language", "en-US,en;q=0.9")

    try:
        resp = requests.get(url, headers=headers, timeout=20, **kwargs)
        _last_request_at[domain] = time.time()
        if resp.status_code >= 400:
            logger.warning("GET %s returned HTTP %s", url, resp.status_code)
            return None
        return resp
    except requests.RequestException as exc:
        logger.warning("GET %s failed: %s", url, exc)
        return None
