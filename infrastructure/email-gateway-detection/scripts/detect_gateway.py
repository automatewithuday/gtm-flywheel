#!/usr/bin/env python3
"""Domains in, security gateway and mailbox provider out. One command.

  python detect_gateway.py --in domains.csv --out final.csv

Input needs a `domain` or `email` column. Every row gets seg_vendor (proofpoint, mimecast,
barracuda, cisco, ..., none, unknown) and mailbox_provider (google, microsoft, zoho, other).

What runs, in order:
  Stage 1  free DNS on every row (skipped if the CSV already has seg_vendor from mx_lookup.py).
  Stage 3  LeadMagic (0.09 credits) on rows DNS left `unknown`, one call per domain, info@domain
           when there is no email. --all runs it on every row as a cross-check instead.
  Stage 2  Prospeo (0.55 credits) only with --stage 2 or 23; not worth it unless the label is free.

Rules (see SKILL.md): paid stages never overwrite a DNS answer; disagreement sets seg_conflict=true.

Keys: set LEADMAGIC_API_KEY and/or PROSPEO_API_KEY (environment or a .env file in the working
directory) to call the vendors directly with your own account. Without a key the call goes
through the deepline CLI, which must be on PATH and authenticated (deepline auth status).
Requires: dnspython.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mx_lookup import FIELDS, load_map, tag_rows  # noqa: E402

EXTRA_FIELDS = ["vendor_raw", "email_status"]
NAMED = lambda v: v not in ("", "none", "unknown")  # noqa: E731


def name_lookup(value: str | None, gmap: dict) -> tuple[str | None, str | None]:
    """Vendor label to (seg_vendor, mailbox_provider). Either side may be None."""
    if not value:
        return None, None
    v = value.strip().lower()
    for name, entry in gmap["gateways"].items():
        if v in (n.lower() for n in entry.get("names", [])):
            return name, None
    for name, entry in gmap["mailbox_providers"].items():
        if v in (n.lower() for n in entry.get("names", [])):
            return "none", name
    return None, None


def payload_of(resp: dict) -> dict:
    """Accept either the full `deepline tools execute --json` output or the bare vendor object."""
    return resp.get("toolResponse", {}).get("rawV2") or resp.get("toolResponse", {}).get("raw") or resp


def parse_prospeo(resp: dict) -> str | None:
    """Prospeo puts the gateway label at company.email_tech.mx_provider (verified Sept 2026)."""
    p = payload_of(resp)
    if p.get("error"):
        return None
    return ((p.get("company") or {}).get("email_tech") or {}).get("mx_provider")


def parse_leadmagic(resp: dict) -> dict:
    """Fields verified against real Deepline responses, Sept 2026. mx_gateway is NOT null on
    plain mailbox hosts; it repeats the provider with mx_gateway_type=Cloud Mailbox Host."""
    p = payload_of(resp)
    return {k: p.get(k) for k in
            ("mx_record", "mx_provider", "mx_gateway", "mx_gateway_type", "mx_security_gateway", "email_status")}


def apply_prospeo(row: dict, value: str | None, gmap: dict) -> None:
    row["vendor_raw"] = f"prospeo:{value or '-'}"
    if row["seg_vendor"] != "unknown":
        return
    vendor, prov = name_lookup(value, gmap)
    if vendor:
        row["seg_vendor"], row["seg_source"] = vendor, "prospeo"
    if prov and row.get("mailbox_provider") in ("", "other"):
        row["mailbox_provider"], row["mailbox_source"] = prov, "prospeo"


def apply_leadmagic(row: dict, lm: dict, gmap: dict) -> None:
    sec = lm.get("mx_security_gateway")
    gw_vendor, _ = name_lookup(lm.get("mx_gateway"), gmap) if sec else (None, None)
    _, prov = name_lookup(lm.get("mx_provider"), gmap)
    row["email_status"] = lm.get("email_status") or ""
    raw = f"leadmagic:{lm.get('mx_gateway') or '-'}/{lm.get('mx_provider') or '-'}/gateway={sec}"
    row["vendor_raw"] = f"{row['vendor_raw']} {raw}".strip() if row.get("vendor_raw") else raw

    cur = row["seg_vendor"]
    if cur == "unknown":  # Stage 2 did not resolve it: LeadMagic may fill
        if sec and gw_vendor:
            row["seg_vendor"], row["seg_source"] = gw_vendor, "leadmagic"
        elif sec is False:  # explicit "no gateway", even when the host is self-hosted (provider stays other)
            row["seg_vendor"], row["seg_source"] = "none", "leadmagic"
    elif cur == "none":
        if sec is True:
            row["seg_conflict"] = "true"
    elif NAMED(cur):
        if sec is False or (gw_vendor and gw_vendor != cur):
            row["seg_conflict"] = "true"
    if prov and row.get("mailbox_provider") in ("", "other"):
        row["mailbox_provider"], row["mailbox_source"] = prov, "leadmagic"


# Direct vendor endpoints, verified against vendor docs Sept 2026 (references/vendor-fields.md).
# Same response bodies as Deepline passes through, so the parsers above work on both.
DIRECT = {
    "prospeo_enrich_company": ("PROSPEO_API_KEY", "https://api.prospeo.io/enrich-company", "X-KEY",
                               lambda inp: {"data": inp}),
    "leadmagic_email_validation": ("LEADMAGIC_API_KEY", "https://api.leadmagic.io/v1/people/email-validation",
                                   "X-API-Key", lambda inp: inp),
}


def load_env(path: Path = Path(".env")) -> None:
    """Minimal .env loader: KEY=VALUE lines, no export, no interpolation. Never prints values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def direct(tool: str, inp: dict, key: str) -> tuple[dict | None, float]:
    """Call the vendor API with the user's own key. Credits are in the vendor's units."""
    _, url, header, body = DIRECT[tool]
    req = urllib.request.Request(url, data=json.dumps(body(inp)).encode(), method="POST",
                                 headers={header: key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"vendor_error tool={tool} input={inp} http={e.code}", file=sys.stderr)  # body may echo the key; not logged
        return None, 0.0
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"vendor_error tool={tool} input={inp} err={e}", file=sys.stderr)
        return None, 0.0
    if tool == "prospeo_enrich_company":
        credits = 0.0 if resp.get("error") or resp.get("free_enrichment") or not resp.get("company") else 1.0
    else:
        credits = float(resp.get("credits_consumed") or 0)
    return resp, credits


def vendor_call(tool: str, inp: dict) -> tuple[dict | None, float]:
    """Own key set for this vendor: call it directly. Otherwise go through Deepline."""
    key = os.environ.get(DIRECT[tool][0])
    return direct(tool, inp, key) if key else deepline(tool, inp)


def deepline(tool: str, inp: dict) -> tuple[dict | None, float]:
    """One Deepline tool call. Returns (response json, credits charged). None on failure."""
    # ponytail: one subprocess per call, sequential. Move to a Deepline play or the bulk endpoint past ~5k rows.
    cmd = ["deepline", "tools", "execute", tool, "--input", json.dumps(inp), "--json"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                             env={**os.environ, "DEEPLINE_SKIP_SELF_UPDATE": "1"})
        text = out.stdout[out.stdout.index("{"):]
        resp = json.loads(text)
    except (subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as e:
        print(f"deepline_error tool={tool} input={inp} err={e}", file=sys.stderr)
        return None, 0.0
    if resp.get("status") not in (None, "completed"):
        print(f"deepline_error tool={tool} input={inp} status={resp.get('status')}", file=sys.stderr)
        return None, 0.0
    return resp, float((resp.get("billing") or {}).get("credits_charged") or 0)


def run(rows: list[dict], stage: str, gmap: dict, call=None, cache: dict | None = None,
        only_unknown: bool = True) -> dict:
    """Mutates rows in place. Returns a stats dict. `call` is injectable for offline tests."""
    call = call or vendor_call
    stats = {"credits": Counter(), "calls": Counter(), "unmapped": Counter(), "conflicts": 0}
    for r in rows:
        r.setdefault("vendor_raw", "")
        r.setdefault("email_status", "")

    if "2" in stage:
        todo = {r["domain"] for r in rows if r.get("seg_vendor") == "unknown" and r.get("seg_status") == "ok"}
        results: dict[str, str | None] = {}
        for d in sorted(todo):
            resp, credits = call("prospeo_enrich_company", {"company_website": d})
            stats["calls"]["prospeo"] += 1
            stats["credits"]["prospeo"] += credits
            results[d] = parse_prospeo(resp) if resp else None
            if resp and results[d] and name_lookup(results[d], gmap) == (None, None):
                stats["unmapped"][f"prospeo:{results[d]}"] += 1
        for r in rows:
            if r["domain"] in results:
                apply_prospeo(r, results[r["domain"]], gmap)
                if cache is not None and r["seg_vendor"] != "unknown" and r["domain"] in cache:
                    cache[r["domain"]].update({k: r[k] for k in FIELDS if k != "domain"})

    if "3" in stage:
        seen: dict[str, dict | None] = {}  # one call per real email, or per domain when using info@ fallback
        for r in rows:
            if r.get("seg_status") != "ok" or (only_unknown and r.get("seg_vendor") != "unknown"):
                continue
            email = (r.get("email") or "").strip() or f"info@{r['domain']}"
            if email not in seen:
                resp, credits = call("leadmagic_email_validation", {"email": email})
                stats["calls"]["leadmagic"] += 1
                stats["credits"]["leadmagic"] += credits
                seen[email] = parse_leadmagic(resp) if resp else None
                lm = seen[email]
                if lm and lm.get("mx_security_gateway") and name_lookup(lm.get("mx_gateway"), gmap) == (None, None):
                    stats["unmapped"][f"leadmagic:{lm.get('mx_gateway')}"] += 1
            if seen[email]:
                apply_leadmagic(r, seen[email], gmap)
                if not r.get("email"):
                    r["email_status"] = ""  # verdict for a made-up info@ address means nothing

    stats["conflicts"] = sum(1 for r in rows if r.get("seg_conflict") == "true")
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="CSV with a domain or email column")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", default="3", choices=["2", "3", "23"], help="paid stages to run after DNS")
    ap.add_argument("--all", action="store_true", help="Stage 3 on every row (cross-check), not just unknowns")
    ap.add_argument("--cache", default=".seg_cache.json", help="DNS cache; paid answers are written back too")
    ap.add_argument("--ttl-days", type=int, default=45)
    a = ap.parse_args(argv)

    with open(a.inp, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or not ({"domain", "email"} & set(rows[0])):
        print("input needs a domain or email column", file=sys.stderr)
        return 1
    cache_path = Path(a.cache)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    gmap = load_map()
    load_env()
    via = {v.split("_")[0]: ("own key" if os.environ.get(env) else "deepline") for v, (env, *_) in DIRECT.items()}
    print(f"vendor route: {via}", file=sys.stderr)

    dns_lookups = 0
    if "seg_vendor" not in rows[0]:
        dns_lookups = tag_rows(rows, cache, a.ttl_days, gmap=gmap)
    unknown_before = sum(1 for r in rows if r["seg_vendor"] == "unknown")

    stats = run(rows, a.stage, gmap, cache=cache, only_unknown=not a.all)
    for r in rows:  # write paid answers back so the next run gets them free
        if r["seg_source"] != "dns" and r["domain"] in cache:
            cache[r["domain"]].update({k: r[k] for k in FIELDS if k != "domain"})
    cache_path.write_text(json.dumps(cache, indent=1))
    out_fields = list(dict.fromkeys(list(rows[0].keys()) + FIELDS + EXTRA_FIELDS))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        w.writerows(rows)

    unknown = sum(1 for r in rows if r["seg_vendor"] == "unknown")
    by_vendor = Counter(r["seg_vendor"] for r in rows)
    print(f"rows={len(rows)} dns_lookups={dns_lookups} unknown_after_dns={unknown_before} "
          f"calls={dict(stats['calls'])} credits={ {k: round(v, 2) for k, v in stats['credits'].items()} } "
          f"conflicts={stats['conflicts']} still_unknown={unknown}", file=sys.stderr)
    print("seg_vendor: " + ", ".join(f"{k}={n}" for k, n in by_vendor.most_common()), file=sys.stderr)
    for k, n in stats["unmapped"].most_common():
        print(f"unmapped_vendor_value {k} x{n}  (add to gateway-map.json names)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
