"""Import outcomes from a CSV for users without API access.

Expected columns (header row, any order; extra columns ignored):
  tool, campaign_id, campaign_name, step_no, variant, subject, body, sends, replies, positive, meetings
positive / meetings may be blank. One row per (campaign, step, variant). Export the per-variant numbers
from your sequencer's UI into this shape; see flywheel/README.md for where each tool exposes them.

Lead-level rows (optional, for the signal and ICP learners): add columns `email` and `status`, plus `replied`,
`positive`, `meeting` as 0/1. A row with an email is one lead; sends/replies may then be blank.

  uv run csv_import.py path/to/outcomes.csv --as-of 2026-10-26
"""
import argparse
import csv
import datetime as dt
import sys

import db

REQUIRED = {"tool", "campaign_id"}


def rows_from_csv(path, as_of):
    out = {"campaigns": {}, "steps": [], "stats": [], "leads": []}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            sys.exit(f"CSV is missing columns: {sorted(missing)}")
        for r in reader:
            key = (r["tool"], r["campaign_id"])
            out["campaigns"][key] = {"tool": r["tool"], "id": r["campaign_id"], "name": r.get("campaign_name") or r["campaign_id"]}
            base = {"tool": r["tool"], "campaign_id": r["campaign_id"], "step_no": int(r.get("step_no") or 0), "variant": r.get("variant") or "A"}
            if r.get("email"):
                flag = lambda k: int(r[k]) if r.get(k) not in (None, "") else None
                out["leads"].append({**base, "email": r["email"], "status": r.get("status"), "replied": flag("replied"),
                                     "positive": flag("positive"), "meeting": flag("meeting"), "as_of": as_of})
                if not r.get("sends"):
                    continue
            out["steps"].append({**base, "subject": r.get("subject"), "body": r.get("body")})
            out["stats"].append({**base, "as_of": as_of, "sends": int(r["sends"] or 0), "replies": int(r["replies"] or 0),
                                 "positive": int(r["positive"]) if r.get("positive") else None,
                                 "meetings": int(r["meetings"]) if r.get("meetings") else None})
    out["campaigns"] = list(out["campaigns"].values())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--db", default=db.DB_PATH)
    a = ap.parse_args(argv)
    rows = rows_from_csv(a.csv, a.as_of)
    db.upsert(db.connect(a.db), rows)
    print({k: len(v) for k, v in rows.items()})


if __name__ == "__main__":
    main()
