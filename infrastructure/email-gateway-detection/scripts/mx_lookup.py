#!/usr/bin/env python3
"""Stage 1 of the gateway waterfall: free DNS classification per domain.

Usage:
  python mx_lookup.py --in leads.csv --out tagged.csv [--cache .seg_cache.json] [--ttl-days 45]

Input CSV needs an `email` or `domain` column. Output keeps every input column
and appends the schema fields documented in SKILL.md. One DNS lookup per unique
domain; results are cached so reruns and big lists stay cheap.

Requires: pip install dnspython
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import dns.exception
import dns.resolver

MAP_PATH = Path(__file__).resolve().parent.parent / "references" / "gateway-map.json"
FIELDS = [
    "domain", "seg_vendor", "mailbox_provider", "seg_source", "mailbox_source",
    "seg_status", "mx_hosts", "seg_checked_at", "seg_conflict",
]


def load_map(path: Path = MAP_PATH) -> dict:
    return json.loads(path.read_text())


def _match_suffix(host: str, table: dict, key: str) -> str | None:
    """Return the table entry whose suffix matches host, longest suffix wins."""
    best, best_len = None, 0
    for name, entry in table.items():
        for suffix in entry[key]:
            if (host == suffix or host.endswith("." + suffix)) and len(suffix) > best_len:
                best, best_len = name, len(suffix)
    return best


class DnsClient:
    """Thin wrapper so tests can inject fake answers."""

    def __init__(self, timeout: float = 4.0):
        self.r = dns.resolver.Resolver()
        self.r.lifetime = timeout

    def mx(self, domain: str) -> list[tuple[int, str]]:
        ans = self.r.resolve(domain, "MX")
        return sorted((a.preference, str(a.exchange).rstrip(".").lower()) for a in ans)

    def txt(self, domain: str) -> list[str]:
        try:
            ans = self.r.resolve(domain, "TXT")
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout,
                dns.resolver.NoNameservers):
            return []
        return [b"".join(a.strings).decode(errors="ignore").lower() for a in ans]


def classify(domain: str, client: DnsClient, gmap: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    row = {"domain": domain, "seg_vendor": "", "mailbox_provider": "", "seg_source": "dns",
           "mailbox_source": "", "seg_status": "ok", "mx_hosts": "",
           "seg_checked_at": now, "seg_conflict": "false"}
    try:
        mx = client.mx(domain)
    except dns.resolver.NXDOMAIN:
        row["seg_status"] = "nxdomain"
        return row
    except dns.resolver.NoAnswer:
        row["seg_status"] = "no_mx"  # RFC 5321 A-record fallback exists, but treat as unsendable
        return row
    except dns.exception.Timeout:
        row["seg_status"] = "timeout"  # retry later, do NOT cache
        return row
    except dns.resolver.NoNameservers:
        row["seg_status"] = "servfail"
        return row

    hosts = [h for _, h in mx]
    row["mx_hosts"] = "|".join(hosts)
    if hosts == [""] or hosts == ["."]:
        row["seg_status"] = "null_mx"  # RFC 7505: domain explicitly accepts no mail
        return row

    # Gateway: first host in preference order that matches wins.
    for h in hosts:
        vendor = _match_suffix(h, gmap["gateways"], "suffixes")
        if vendor:
            row["seg_vendor"] = vendor
            break

    # Mailbox provider: direct from MX when no gateway, else infer from SPF.
    if not row["seg_vendor"]:
        for h in hosts:
            prov = _match_suffix(h, gmap["mailbox_providers"], "mx_suffixes")
            if prov:
                row["mailbox_provider"], row["mailbox_source"] = prov, "dns_mx"
                row["seg_vendor"] = "none"
                break
    if not row["mailbox_provider"]:
        spf = next((t for t in client.txt(domain) if t.startswith("v=spf1")), "")
        for prov, entry in gmap["mailbox_providers"].items():
            if any(f"include:{inc}" in spf for inc in entry["spf_includes"]):
                row["mailbox_provider"], row["mailbox_source"] = prov, "dns_spf"
                break
    if not row["mailbox_provider"]:
        row["mailbox_provider"] = "other"
    if not row["seg_vendor"]:
        row["seg_vendor"] = "unknown"  # self-hosted or unmapped host: send to Stage 2
    return row


def domain_of(rec: dict) -> str:
    raw = (rec.get("domain") or rec.get("email") or "").strip().lower()
    return raw.split("@")[-1].removeprefix("www.")


def tag_rows(rows: list[dict], cache: dict, ttl_days: int = 45, client: DnsClient | None = None,
             gmap: dict | None = None) -> int:
    """Stage 1 over a list of dict rows, in place. Fills `cache`. Returns number of DNS lookups made."""
    gmap = gmap or load_map()
    client = client or DnsClient()
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    looked_up = 0
    for rec in rows:
        d = domain_of(rec)
        hit = cache.get(d)
        if not hit or datetime.fromisoformat(hit["seg_checked_at"]) < cutoff:
            hit = classify(d, client, gmap)
            looked_up += 1
            if hit["seg_status"] not in ("timeout", "servfail"):
                cache[d] = hit
        rec.update({k: v for k, v in hit.items() if k != "domain"})
        rec["domain"] = d
    return looked_up


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=".seg_cache.json")
    ap.add_argument("--ttl-days", type=int, default=45)
    a = ap.parse_args(argv)

    cache_path = Path(a.cache)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    with open(a.inp, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("empty input", file=sys.stderr)
        return 1

    looked_up = tag_rows(rows, cache, a.ttl_days)

    cache_path.write_text(json.dumps(cache, indent=1))
    out_fields = list(dict.fromkeys(list(rows[0].keys()) + FIELDS))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        w.writerows(rows)

    unknown = sum(1 for r in rows if r["seg_vendor"] == "unknown")
    print(f"rows={len(rows)} dns_lookups={looked_up} unknown_for_stage2={unknown}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
