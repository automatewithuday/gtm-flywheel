"""Pull outreach outcomes (read-only) from every tool that has a key in flywheel/.env into outcomes.sqlite.

  uv run pull_outcomes.py --dry-run                 # print the exact requests, no network
  uv run pull_outcomes.py --tools smartlead --campaign-ids 12345   # one campaign first
  uv run pull_outcomes.py --since 2026-01-01
"""
import argparse
import datetime as dt
import importlib
import os
import sys
from pathlib import Path

import db

TOOLS = ["smartlead", "instantly", "lemlist", "heyreach"]


def load_env(path=Path(__file__).parent / ".env"):
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tools", nargs="*", default=TOOLS)
    ap.add_argument("--since", default=(dt.date.today() - dt.timedelta(days=90)).isoformat())
    ap.add_argument("--until", default=dt.date.today().isoformat())
    ap.add_argument("--campaign-ids", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db", default=db.DB_PATH)
    a = ap.parse_args(argv)
    load_env()
    con = None if a.dry_run else db.connect(a.db)
    ran = 0
    for tool in a.tools:
        key = os.environ.get(f"{tool.upper()}_API_KEY")
        if not key:
            print(f"skip {tool}: no {tool.upper()}_API_KEY in flywheel/.env")
            continue
        mod = importlib.import_module(f"adapters.{tool}")
        client = mod.make_client(key, dry_run=a.dry_run)
        rows = mod.pull(client, a.since, a.until, a.until, campaign_ids=a.campaign_ids)
        ran += 1
        n = {k: len(v) for k, v in rows.items()}
        if a.dry_run:
            print(f"{tool}: {len(client.calls)} read requests planned; would upsert {n}")
        else:
            db.upsert(con, rows)
            print(f"{tool}: {len(client.calls)} read requests; upserted {n}")
    if not ran:
        sys.exit("nothing pulled: add at least one API key to flywheel/.env (see .env.example)")


if __name__ == "__main__":
    main()
