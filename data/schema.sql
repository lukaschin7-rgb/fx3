-- SQLite schema for the FX3 deal-finder.
-- This file just documents the schema; storage.py creates it automatically
-- (CREATE TABLE IF NOT EXISTS) so you never have to run this by hand.

CREATE TABLE IF NOT EXISTS listings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    target_key          TEXT NOT NULL,      -- e.g. "sony_fx3", "sony_2470_gm2"
    target_label        TEXT NOT NULL,      -- human-readable, e.g. "Sony 24-70mm f/2.8 GM II"
    category            TEXT NOT NULL,      -- "camera" or "lens"
    is_primary_target   INTEGER NOT NULL,   -- 1 = on your explicit list, 0 = candidate favorite
    title               TEXT NOT NULL,
    price               REAL,
    currency            TEXT DEFAULT 'USD',
    condition_text      TEXT,
    shutter_count       INTEGER,            -- camera only, NULL if not listed/found
    source              TEXT NOT NULL,      -- ebay | reverb | mpb | keh | bhphoto | adorama | reddit
    url                 TEXT NOT NULL,
    credit_card_payable INTEGER NOT NULL DEFAULT 0,
    dedupe_group_id     INTEGER,            -- points at the id of the "primary" listing in its group
    first_seen_date     TEXT NOT NULL,      -- ISO date, YYYY-MM-DD
    last_seen_date      TEXT NOT NULL,
    last_seen_run_id    INTEGER,
    UNIQUE(source, url)
);

CREATE INDEX IF NOT EXISTS idx_listings_target ON listings(target_key);
CREATE INDEX IF NOT EXISTS idx_listings_first_seen ON listings(first_seen_date);
CREATE INDEX IF NOT EXISTS idx_listings_dedupe_group ON listings(dedupe_group_id);

CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,   -- ISO datetime, UTC
    finished_at     TEXT,
    new_listings    INTEGER DEFAULT 0,
    total_listings  INTEGER DEFAULT 0,
    errors          TEXT              -- newline-separated warnings/errors from this run, if any
);
