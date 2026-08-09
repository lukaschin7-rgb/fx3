# FX3 & Lens Deal Finder

A daily-running tool that scans the used market for a **Sony FX3** and a
shortlist of **zoom lenses** good for handheld, run-and-gun documentary
work, and shows you what's genuinely new since yesterday.

It runs automatically once a day on GitHub's servers (via GitHub Actions),
so your phone or laptop doesn't need to be on. The results show up on a
free web page (GitHub Pages) you can check from anywhere.

---

## How it works (plain-language overview)

```
 GitHub Actions (runs daily, on GitHub's servers)
        │
        ├─ 1. scrapers/run_all.py
        │       queries eBay, Reverb, MPB, KEH, B&H, Adorama, and Reddit
        │       for the FX3 and each target lens
        │       │
        │       └─ saves everything into data/listings.db (SQLite)
        │           and figures out which listings are brand new today
        │
        ├─ 2. app/generate_dashboard.py
        │       reads listings.db and writes docs/index.html
        │
        └─ 3. commits data/listings.db + docs/index.html back to the repo
                │
                └─ GitHub Pages serves docs/index.html as a website
```

Nothing needs a server you pay for or maintain: GitHub Pages hosts the
static dashboard for free regardless of repo visibility, and GitHub
Actions gives every free personal account 2,000 minutes/month of compute
-- this repo is currently **private**, so it draws from that quota (a
public repo would get unlimited free minutes instead). One daily run
of this workflow takes roughly 10-20 minutes (most of it is the
randomized delays before each retail-site request, done on purpose to be
polite), so a full month of daily runs is comfortably inside the free
2,000-minute allowance. If you'd rather not think about it at all, making
the repo public would remove the cap entirely -- entirely optional, and
only sensible if you're fine with the code (not your API keys, those stay
secret either way) being publicly visible.

### Repo layout

```
scrapers/     one module per source, plus run_all.py (the daily orchestrator)
              and config.py (the list of gear you're tracking -- edit this
              to add/remove lenses)
data/         SQLite schema + storage helpers, and listings.db itself
              (the database file is committed to the repo so history
              persists between daily runs)
app/          dashboard generator + HTML template
docs/         the generated dashboard (docs/index.html) -- this is what
              GitHub Pages serves. Don't hand-edit this, it's overwritten
              every run.
.github/workflows/daily.yml   the GitHub Actions schedule definition
scripts/run_daily.sh          convenience script to run everything locally
```

---

## What you need to do (one-time setup)

Three things require action from you, because they involve your accounts:
1. Get an eBay API key (free)
2. Get a Reverb API key (free)
3. Add those keys as GitHub "Secrets" and turn on GitHub Pages

Everything else (the code, the repo, the daily schedule) is already set
up. Take these one at a time.

### 1. eBay Browse API access (free)

This lets the scraper search eBay listings the same way the eBay website
does, without needing your eBay password.

1. Go to **https://developer.ebay.com/** and sign in with (or create) a
   free eBay account.
2. Go to **My Account -> Application Keys** (sometimes under
   "Application Access Keys").
3. Create a **production** keyset for a new application (name it anything,
   e.g. "fx3-deal-finder").
4. eBay may ask you to configure a "Marketplace Account Deletion /
   Closure Notification" endpoint before it issues production keys --
   this is a privacy-compliance step for apps that could hold eBay user
   data. Since this tool never touches user accounts, look for an
   "opt out" / "I don't process this data" option in that form. eBay's
   UI for this changes occasionally, so if you get stuck, their developer
   support docs (search "marketplace account deletion notification") walk
   through it, or tell me what you're seeing and I'll help.
5. Copy the **Client ID (App ID)** and **Client Secret (Cert ID)** shown
   for the production keyset. You'll paste these into GitHub in step 3
   below -- don't put them in any file in this repo.

### 2. Reverb API token (free)

Heads-up: Reverb is mainly a musical-instrument marketplace. It does have
broader gear categories, but you may see thin or no results for cameras
compared to eBay/MPB/KEH. It's included because you asked for it and it
costs nothing to run -- just don't expect it to be the main source of
deals.

1. Log into **https://reverb.com** (or create a free account).
2. Go to your account settings and look for an **API** / **API access**
   section (Reverb sometimes calls this "Personal Access Tokens").
3. Generate a token and copy it.

### 3. Add your keys to GitHub, and turn on the dashboard

Your keys go into GitHub's encrypted "Secrets" store, not into any file --
that's what keeps them out of the repo and out of `.env`.

1. On GitHub, open this repo: **lukaschin7-rgb/fx3**
2. Go to **Settings -> Secrets and variables -> Actions**
3. Click **New repository secret** and add each of these (name must match
   exactly):
   - `EBAY_CLIENT_ID`
   - `EBAY_CLIENT_SECRET`
   - `REVERB_API_TOKEN`
4. Still in **Settings**, go to **Actions -> General -> Workflow
   permissions**, and select **"Read and write permissions"**, then Save.
   (This is what lets the daily job commit the day's results back to the
   repo.)
5. Go to **Settings -> Pages**. Under "Build and deployment", set
   **Source: Deploy from a branch**, branch **main**, folder **/docs**,
   then Save. GitHub will give you a URL like
   `https://lukaschin7-rgb.github.io/fx3/` -- bookmark that, it's your
   dashboard.

> **Important:** the daily schedule and Pages both key off the **main**
> branch. This project was built on a branch called
> `claude/sony-fx3-lens-deals-t3qu5j`. Once you're happy with it, merge
> that branch into `main` (I can open a pull request for you if you'd
> like -- just ask) so the schedule actually starts firing and Pages has
> something to serve.

That's it for setup. The workflow will now run automatically every day at
13:00 UTC (~6am Pacific / 9am Eastern -- edit the `cron:` line in
`.github/workflows/daily.yml` to change the time). You can also trigger it
manually any time: go to the **Actions** tab -> **Daily FX3 deal scrape**
-> **Run workflow**.

---

## Running it yourself (optional, e.g. to test before merging)

You'll need Python 3.11+ installed.

```bash
git clone https://github.com/lukaschin7-rgb/fx3.git
cd fx3
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium   # needed for the MPB/KEH/B&H/Adorama scrapers

cp .env.example .env
# edit .env and paste in your EBAY_CLIENT_ID / EBAY_CLIENT_SECRET / REVERB_API_TOKEN

./scripts/run_daily.sh
```

Then open `docs/index.html` in a browser to see the dashboard.

To just rebuild the dashboard from whatever's already in the database
(no new scraping): `python -m app.generate_dashboard`.

---

## What gets tracked

**Camera:** Sony FX3 (used)

**Lenses (your explicit list):**
Sony 24-70mm f/2.8 GM II, Sony 28-135mm f/4 PZ, Sigma 28-70mm f/2.8,
Tamron 28-75mm f/2.8, Sony 16-35mm f/2.8 GM, Sony 70-200mm f/2.8 GM II

**"Other lenses worth watching":** a secondary watchlist of zooms that
come up often in doc/run-and-gun circles (Sony 24-105 G, Sony 20-70 G,
Tamron 17-28mm, Tamron 35-150mm, Sigma 24-70 Art, Sigma 18-50mm, Sony
16-70 ZA, Sony 18-105 PZ). These are scraped like everything else, but
only surface on the dashboard once one of them has actually shown up 3+
times, so you're not shown noise for something that appeared once.

To add, remove, or reword any of these, edit `scrapers/config.py` -- it's
just a list, no other code needs to change.

## Sources

| Source | Method | Credit-card payable? |
|---|---|---|
| eBay | official Browse API | Yes |
| Reverb | official API | Yes |
| MPB | scraped (headless browser) | Yes |
| KEH | scraped (headless browser) | Yes |
| B&H (used dept.) | scraped (headless browser) | Yes |
| Adorama (used dept.) | scraped (headless browser) | Yes |
| Reddit (r/photomarket, r/AVexchange) | official read-only JSON API | Usually not (PayPal G&S / cash) |
| FredMiranda (Buy & Sell forum, board 10) | scraped (plain HTTP, no headless browser needed) | No (peer-to-peer) |

**Facebook Marketplace and Craigslist were deliberately left out.** Both
require a logged-in session and actively fingerprint/block automated
access, and Craigslist in particular has a history of pursuing scrapers
legally. Reddit and FredMiranda cover the same "peer-to-peer classifieds"
niche without those problems.

The four retail-site scrapers (MPB/KEH/B&H/Adorama) and the FredMiranda
scraper check `robots.txt` before every request, use a randomized
2.5-5.5 second delay between requests, and identify as a normal desktop
browser rather than an aggressive bot.

**FredMiranda specifics/limitations:** it only reads the current front
page of the board (the most recent threads) once per run, not every page
ever posted -- fine for a daily "what's new" check, but a thread that's
scrolled off the front page between runs won't be picked up. Matching is
a plain case-insensitive substring match against each search term, so
phrasing quirks (e.g. "24-70 GM2" vs "24-70mm GM II") can cause misses;
this is looser than eBay/Reverb's real search but was the simplest thing
that could work without live access to verify the site's own search
feature. The thread-link CSS selector is, like the four retail scrapers,
an educated guess -- see Troubleshooting below if it comes back empty.

## Ranking and dedup logic

- Credit-card-payable sites are ranked above non-CC sites (Reddit, FredMiranda).
- Within that, sorted by price ascending.
- Near-identical listings that show up on two sites (same price within
  ~3% and near-identical title) are collapsed into one row, with "also
  listed on ___" shown underneath.
- A listing only counts as "New Today" the first time its (source, URL)
  pair has ever been seen. Re-appearing the next day doesn't re-flag it.

## Troubleshooting the retail scrapers (MPB / KEH / B&H / Adorama / FredMiranda)

These sites don't have a public API, so the scrapers render the page (in
a headless browser for MPB/KEH/B&H/Adorama, plain HTTP for FredMiranda)
and pull listings out of the HTML using CSS selectors. **These selectors
were written from general knowledge of each site's layout, not verified
against the live pages** (this dev environment couldn't reach those
domains to check).

Confirmed as of the first live runs: **MPB, KEH, B&H, and Adorama's
selectors are currently stale** -- every search times out waiting for the
guessed selector and falls back to a generic extraction pass that (after
the relevance filter) mostly finds nothing. They're safe to leave running
(they fail closed, not with garbage), but they won't surface real listings
until someone fixes the selectors against the live markup:

1. Open the site's search page in your phone or laptop browser (e.g.
   `mpb.com/en-us/search?query=sony+fx3`).
2. Open browser dev tools (on desktop: right-click a listing -> Inspect).
3. Find the repeating "card" element that wraps one listing, and the
   elements inside it for the title, price, and link.
4. Open the matching file (`scrapers/mpb_scraper.py`,
   `keh_scraper.py`, `bhphoto_scraper.py`, or `adorama_scraper.py`) and
   update the `SELECTORS` dictionary at the top with what you found.
   (For FredMiranda, it's `THREAD_LINK_SELECTOR` in
   `scrapers/fredmiranda_scraper.py` -- find the link element each thread
   title lives in.)
5. Commit and push -- no other code needs to change.

If you'd rather not deal with this yourself, paste me what you see in dev
tools (or just tell me a scraper broke) and I'll update the selectors.

## Known limitations

- **Shutter count** is only captured when a site displays it directly in
  the listing title/description; it's not pulled by opening every
  individual listing page (that would multiply the number of requests
  significantly). eBay gets one extra API call per FX3 result to check its
  full description for a shutter count; the other sources only check the
  search-result text.
- **Reverb** inventory for cameras/lenses may be sparse -- it's a
  music-gear-first marketplace.
- **Facebook Marketplace / Craigslist** are not scraped (see above).
- The retail-site scrapers are best-effort HTML scraping and may need
  occasional selector maintenance (see Troubleshooting above).

## Costs

$0. eBay's Browse API, Reverb's API, Reddit's public API, GitHub Actions
(public repo), and GitHub Pages are all free at this usage level.
