"""
Daily orchestrator. Runs every configured scraper against every configured
gear target, dedupes, and stores results in SQLite.

Usage:
    python -m scrapers.run_all

Designed to be safe to run from GitHub Actions on a schedule: a failure in
any one scraper (bad selector, API outage, rate limit) is caught, logged,
and recorded in the `runs` table -- it never takes down the rest of the
pipeline.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data import storage  # noqa: E402
from scrapers import (  # noqa: E402
    adorama_scraper,
    bhphoto_scraper,
    dedupe,
    ebay_scraper,
    fredmiranda_scraper,
    keh_scraper,
    mpb_scraper,
    reddit_scraper,
    relevance,
    reverb_scraper,
)
from scrapers.config import ALL_TARGETS, CREDIT_CARD_PAYABLE, PRICE_OPTIONAL_SOURCES  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_all")

# (source name, callable). API-based sources take (term); eBay also wants
# the target's category so it knows whether to look for a shutter count.
SOURCES = ["ebay", "reverb", "mpb", "keh", "bhphoto", "adorama", "reddit", "fredmiranda"]


def run_source(source: str, term: str, target) -> list[dict]:
    try:
        if source == "ebay":
            return ebay_scraper.search(term, target.category)
        if source == "reverb":
            return reverb_scraper.search(term)
        if source == "reddit":
            return reddit_scraper.search(term)
        if source == "mpb":
            return mpb_scraper.search(term, target)
        if source == "keh":
            return keh_scraper.search(term, target)
        if source == "bhphoto":
            return bhphoto_scraper.search(term)
        if source == "adorama":
            return adorama_scraper.search(term)
        if source == "fredmiranda":
            return fredmiranda_scraper.search(term)
    except Exception as exc:  # noqa: BLE001 -- one source failing must not stop the run
        logger.exception("Scraper %s failed for term %r: %s", source, term, exc)
        return []
    return []


def main() -> None:
    conn = storage.get_connection()
    storage.init_db(conn)
    run_id = storage.start_run(conn)

    errors: list[str] = []
    new_count = 0
    total_count = 0

    for target in ALL_TARGETS:
        # Pull what we already know about this target so dedupe can compare
        # new results against it.
        existing = storage.get_listings_for_target(conn, target.key)

        for source in SOURCES:
            for term in target.search_terms:
                logger.info("Searching %s for %r (%s)", source, term, target.key)
                try:
                    raw_results = run_source(source, term, target)
                except Exception as exc:  # noqa: BLE001
                    msg = f"{source}/{target.key}/{term}: {exc}"
                    logger.exception(msg)
                    errors.append(msg)
                    continue

                for raw in raw_results:
                    if not raw.get("url"):
                        continue
                    if raw.get("price") is None and source not in PRICE_OPTIONAL_SOURCES:
                        # Peer-to-peer classifieds (Reddit, FredMiranda) legitimately
                        # have no structured price; every other source should have
                        # one, so skip anything that came back malformed.
                        continue

                    if not relevance.is_plausible_listing(raw.get("title"), raw.get("price"), target.category):
                        logger.info(
                            "Filtered out implausible result from %s for %s: %r ($%s)",
                            source, target.key, raw.get("title"), raw.get("price"),
                        )
                        continue

                    listing = {
                        "target_key": target.key,
                        "target_label": target.label,
                        "category": target.category,
                        "is_primary_target": target.is_primary,
                        "title": raw["title"],
                        "price": raw.get("price"),
                        "currency": raw.get("currency", "USD"),
                        "condition_text": raw.get("condition_text"),
                        "shutter_count": raw.get("shutter_count"),
                        "source": raw["source"],
                        "url": raw["url"],
                        "credit_card_payable": raw.get(
                            "credit_card_payable", CREDIT_CARD_PAYABLE.get(raw["source"], False)
                        ),
                    }

                    dupe_group = dedupe.find_duplicate_group(listing, existing)
                    if dupe_group:
                        listing["dedupe_group_id"] = dupe_group

                    is_new = storage.upsert_listing(conn, listing, run_id)
                    total_count += 1
                    if is_new:
                        new_count += 1
                        existing.append(listing)  # so later sources this run can dedupe against it too

    storage.finish_run(conn, run_id, new_count, total_count, errors)
    conn.close()

    logger.info("Run complete: %d new listings, %d total processed, %d errors", new_count, total_count, len(errors))
    if errors:
        logger.warning("Errors this run:\n%s", "\n".join(errors))


if __name__ == "__main__":
    main()
