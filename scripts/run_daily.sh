#!/usr/bin/env bash
# Convenience script for running the whole pipeline locally (scrape, then
# rebuild the dashboard). Loads .env if present. This is what the GitHub
# Actions workflow does too, minus the git commit/push at the end.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

python -m scrapers.run_all
python -m app.generate_dashboard

echo "Done. Open docs/index.html in a browser to view the dashboard."
