"""
Builds the static dashboard (docs/index.html) from whatever is currently
in the SQLite database. Run this after scrapers/run_all.py.

Usage:
    python -m app.generate_dashboard

The output goes to docs/index.html, which GitHub Pages serves directly --
see README.md for how to turn Pages on for this repo.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from data import storage  # noqa: E402
from scrapers.config import FAVORITE_LISTING_THRESHOLD  # noqa: E402

TEMPLATE_DIR = Path(__file__).parent / "templates"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "index.html"


def _group_key(listing: dict) -> int:
    return listing["dedupe_group_id"] or listing["id"]


def collapse_duplicates(listings: list[dict]) -> list[dict]:
    """Group near-identical cross-site listings. Returns one row per group
    (the earliest-seen listing), annotated with `also_listed_on`: a list of
    {source, url} for the other sites the same item showed up on."""
    groups: dict[int, list[dict]] = {}
    for listing in listings:
        groups.setdefault(_group_key(listing), []).append(listing)

    collapsed = []
    for group_key, members in groups.items():
        primary = next((m for m in members if m["id"] == group_key), members[0])
        others = [m for m in members if m is not primary]
        primary = dict(primary)
        primary["also_listed_on"] = [{"source": o["source"], "url": o["url"]} for o in others]
        collapsed.append(primary)
    return collapsed


def sort_key(listing: dict) -> tuple:
    # Credit-card-payable sites first (False sorts after True, so invert),
    # then price ascending. Listings with no price (e.g. Reddit posts) sort
    # to the end of their group.
    price = listing.get("price")
    return (0 if listing.get("credit_card_payable") else 1, price if price is not None else float("inf"))


def split_sections(listings: list[dict]) -> dict:
    primary = [listing_ for listing_ in listings if listing_["is_primary_target"]]
    cameras = sorted((listing_ for listing_ in primary if listing_["category"] == "camera"), key=sort_key)
    lenses = sorted((listing_ for listing_ in primary if listing_["category"] == "lens"), key=sort_key)
    return {"cameras": cameras, "lenses": lenses}


def main() -> None:
    conn = storage.get_connection()
    storage.init_db(conn)

    last_run = storage.get_last_run(conn)
    all_listings = collapse_duplicates(storage.get_all_listings(conn))
    new_today_raw = storage.get_new_today(conn)
    new_today_urls = {(listing_["source"], listing_["url"]) for listing_ in new_today_raw}
    new_today = [listing_ for listing_ in all_listings if (listing_["source"], listing_["url"]) in new_today_urls]

    favorites = [
        f for f in storage.get_candidate_favorite_counts(conn) if f["listing_count"] >= FAVORITE_LISTING_THRESHOLD
    ]

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("dashboard.html.j2")

    html = template.render(
        generated_at=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        last_run=dict(last_run) if last_run else None,
        new_today=split_sections(new_today),
        all_sections=split_sections(all_listings),
        favorites=favorites,
    )

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")

    conn.close()


if __name__ == "__main__":
    main()
