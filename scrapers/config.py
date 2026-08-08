"""
Target gear list and site configuration for the FX3 deal-finder.

Everything the scrapers search for lives here. To track a new lens or
adjust search phrasing, edit the lists below -- nothing else needs to
change.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GearTarget:
    key: str                # stable id, used in the database
    label: str              # human-readable name shown on the dashboard
    category: str           # "camera" or "lens"
    search_terms: list[str] # phrases sent to each source's search
    is_primary: bool = True # False = "candidate favorite", only surfaced if it trends


# ---------------------------------------------------------------------------
# Primary targets -- exactly what you asked to track.
# ---------------------------------------------------------------------------

CAMERAS: list[GearTarget] = [
    GearTarget(
        key="sony_fx3",
        label="Sony FX3",
        category="camera",
        search_terms=["Sony FX3", "Sony ILME-FX3"],
    ),
]

LENSES: list[GearTarget] = [
    GearTarget(
        key="sony_2470_gm2",
        label="Sony 24-70mm f/2.8 GM II",
        category="lens",
        search_terms=["Sony 24-70mm GM II", "Sony FE 24-70 f2.8 GM II", "SEL2470GM2"],
    ),
    GearTarget(
        key="sony_28135_pz",
        label="Sony 28-135mm f/4 PZ",
        category="lens",
        search_terms=["Sony 28-135mm PZ", "Sony FE PZ 28-135", "SELP28135G"],
    ),
    GearTarget(
        key="sigma_2870_28",
        label="Sigma 28-70mm f/2.8 DG DN",
        category="lens",
        search_terms=["Sigma 28-70mm f2.8 DG DN", "Sigma 28-70 Contemporary E-mount"],
    ),
    GearTarget(
        key="tamron_2875_28",
        label="Tamron 28-75mm f/2.8",
        category="lens",
        search_terms=["Tamron 28-75mm f2.8", "Tamron 28-75 Di III RXD", "Tamron 28-75 G2"],
    ),
    GearTarget(
        key="sony_1635_gm",
        label="Sony 16-35mm f/2.8 GM",
        category="lens",
        search_terms=["Sony 16-35mm GM", "Sony FE 16-35 f2.8 GM", "SEL1635GM"],
    ),
    GearTarget(
        key="sony_70200_gm2",
        label="Sony 70-200mm f/2.8 GM II",
        category="lens",
        search_terms=["Sony 70-200mm GM II", "Sony FE 70-200 f2.8 GM II", "SEL70200GM2"],
    ),
]

# ---------------------------------------------------------------------------
# Candidate favorites -- zooms that come up a lot in run-and-gun / doc
# shooter circles but that you didn't explicitly ask for. These are scraped
# just like the primary list, but they only show up on the dashboard once
# they've actually appeared FAVORITE_LISTING_THRESHOLD+ times, so you're not
# flooded with noise for a lens that only showed up once.
# ---------------------------------------------------------------------------

FAVORITE_LISTING_THRESHOLD = 3

CANDIDATE_LENSES: list[GearTarget] = [
    GearTarget(
        key="sony_24105_g",
        label="Sony 24-105mm f/4 G",
        category="lens",
        search_terms=["Sony 24-105mm f4 G", "Sony FE 24-105 G", "SEL24105G"],
        is_primary=False,
    ),
    GearTarget(
        key="sony_2070_g",
        label="Sony 20-70mm f/4 G",
        category="lens",
        search_terms=["Sony 20-70mm f4 G", "Sony FE 20-70 G", "SEL2070G"],
        is_primary=False,
    ),
    GearTarget(
        key="tamron_1728_28",
        label="Tamron 17-28mm f/2.8",
        category="lens",
        search_terms=["Tamron 17-28mm f2.8", "Tamron 17-28 Di III RXD"],
        is_primary=False,
    ),
    GearTarget(
        key="tamron_35150",
        label="Tamron 35-150mm f/2-2.8",
        category="lens",
        search_terms=["Tamron 35-150mm", "Tamron 35-150 f2-2.8"],
        is_primary=False,
    ),
    GearTarget(
        key="sigma_2470_28_art",
        label="Sigma 24-70mm f/2.8 DN Art",
        category="lens",
        search_terms=["Sigma 24-70mm f2.8 DG DN Art", "Sigma 24-70 Art E-mount"],
        is_primary=False,
    ),
    GearTarget(
        key="sigma_18_50",
        label="Sigma 18-50mm f/2.8 DC DN",
        category="lens",
        search_terms=["Sigma 18-50mm f2.8 DC DN", "Sigma 18-50 Contemporary E-mount"],
        is_primary=False,
    ),
    GearTarget(
        key="sony_1670z",
        label="Sony 16-70mm f/4 ZA (Vario-Tessar)",
        category="lens",
        search_terms=["Sony 16-70mm f4 ZA", "Sony E 16-70 Zeiss"],
        is_primary=False,
    ),
    GearTarget(
        key="sony_18105g",
        label="Sony 18-105mm f/4 G PZ",
        category="lens",
        search_terms=["Sony 18-105mm f4 G PZ", "SELP18105G"],
        is_primary=False,
    ),
]

ALL_TARGETS: list[GearTarget] = CAMERAS + LENSES + CANDIDATE_LENSES


# ---------------------------------------------------------------------------
# Site metadata: whether it's credit-card payable (ranking factor), and
# a normal desktop user-agent to send when scraping (not an API).
# ---------------------------------------------------------------------------

CREDIT_CARD_PAYABLE = {
    "ebay": True,
    "reverb": True,
    "mpb": True,
    "keh": True,
    "bhphoto": True,
    "adorama": True,
    "reddit": False,
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Minimum / maximum delay (seconds) between requests to the same
# HTML-scraped site. Randomized so we're not hammering on a fixed interval.
REQUEST_DELAY_RANGE = (2.5, 5.5)

REDDIT_SUBREDDITS = ["photomarket", "AVexchange"]
REDDIT_USER_AGENT = "python:fx3-deal-finder:v1.0 (personal, non-commercial use)"
