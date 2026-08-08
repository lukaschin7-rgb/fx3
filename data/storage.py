"""
SQLite storage layer. Everything the scrapers and the dashboard generator
need to read/write listings lives here -- no other module should touch
the database directly.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "listings.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def start_run(conn: sqlite3.Connection) -> int:
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    cur = conn.execute("INSERT INTO runs (started_at) VALUES (?)", (now,))
    conn.commit()
    return cur.lastrowid


def finish_run(conn: sqlite3.Connection, run_id: int, new_listings: int, total_listings: int, errors: list[str]) -> None:
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE runs SET finished_at = ?, new_listings = ?, total_listings = ?, errors = ? WHERE id = ?",
        (now, new_listings, total_listings, "\n".join(errors), run_id),
    )
    conn.commit()


def get_last_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()


def get_listings_for_target(conn: sqlite3.Connection, target_key: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM listings WHERE target_key = ?", (target_key,)).fetchall()
    return [dict(r) for r in rows]


def upsert_listing(conn: sqlite3.Connection, listing: dict, run_id: int) -> bool:
    """Insert a new listing, or refresh last_seen_date/last_seen_run_id for
    an existing one (same source + url). Returns True if this is a listing
    we've never seen before (i.e. genuinely new today)."""
    today = dt.date.today().isoformat()
    existing = conn.execute(
        "SELECT id FROM listings WHERE source = ? AND url = ?",
        (listing["source"], listing["url"]),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE listings SET last_seen_date = ?, last_seen_run_id = ?, price = ?, condition_text = ? WHERE id = ?",
            (today, run_id, listing.get("price"), listing.get("condition_text"), existing["id"]),
        )
        conn.commit()
        return False

    conn.execute(
        """
        INSERT INTO listings (
            target_key, target_label, category, is_primary_target, title, price, currency,
            condition_text, shutter_count, source, url, credit_card_payable,
            dedupe_group_id, first_seen_date, last_seen_date, last_seen_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            listing["target_key"],
            listing["target_label"],
            listing["category"],
            int(listing["is_primary_target"]),
            listing["title"],
            listing.get("price"),
            listing.get("currency", "USD"),
            listing.get("condition_text"),
            listing.get("shutter_count"),
            listing["source"],
            listing["url"],
            int(listing.get("credit_card_payable", False)),
            listing.get("dedupe_group_id"),
            today,
            today,
            run_id,
        ),
    )
    conn.commit()
    return True


def set_dedupe_group(conn: sqlite3.Connection, listing_url: str, source: str, group_id: int) -> None:
    conn.execute(
        "UPDATE listings SET dedupe_group_id = ? WHERE source = ? AND url = ?",
        (group_id, source, listing_url),
    )
    conn.commit()


def get_all_listings(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM listings ORDER BY first_seen_date DESC").fetchall()
    return [dict(r) for r in rows]


def get_new_today(conn: sqlite3.Connection) -> list[dict]:
    today = dt.date.today().isoformat()
    rows = conn.execute(
        "SELECT * FROM listings WHERE first_seen_date = ? AND (dedupe_group_id IS NULL OR dedupe_group_id = id)",
        (today,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_candidate_favorite_counts(conn: sqlite3.Connection) -> list[dict]:
    """Total distinct-listing counts per candidate ('not on your explicit
    list') lens, so the dashboard can flag ones that keep showing up."""
    rows = conn.execute(
        """
        SELECT target_key, target_label, COUNT(*) as listing_count
        FROM listings
        WHERE is_primary_target = 0
          AND (dedupe_group_id IS NULL OR dedupe_group_id = id)
        GROUP BY target_key, target_label
        ORDER BY listing_count DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]
