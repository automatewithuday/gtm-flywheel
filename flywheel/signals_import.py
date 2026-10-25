"""Load dated signals into outcomes.sqlite from a CSV with columns:
  company_domain, signal_type, party (first|second|third), event_date (YYYY-MM-DD), source_url (optional)
This is the same shape the martechs outbound plays write to signals.csv. Collection stays outside the flywheel.

  uv run signals_import.py signals.csv
"""
import argparse
import csv
import sys

import db
from score_signals import PARTIES


def rows_from_csv(path):
    out, skipped = [], 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        need = {"company_domain", "signal_type", "party", "event_date"} - set(reader.fieldnames or [])
        if need:
            sys.exit(f"CSV is missing columns: {sorted(need)}")
        for r in reader:
            if r["party"].strip() not in PARTIES or len(r["event_date"].strip()) != 10 or not r["company_domain"].strip():
                skipped += 1
                continue
            out.append({"domain": r["company_domain"], "type": r["signal_type"].strip(), "party": r["party"].strip(),
                        "event_date": r["event_date"].strip(), "source_url": (r.get("source_url") or "").strip() or None})
    return out, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--db", default=db.DB_PATH)
    a = ap.parse_args(argv)
    rows, skipped = rows_from_csv(a.csv)
    db.upsert(db.connect(a.db), {"signals": rows})
    print(f"imported {len(rows)} signals, skipped {skipped} malformed rows")


if __name__ == "__main__":
    main()
