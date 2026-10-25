---
name: email-gateway-detection
description: "Use when building, cleaning or enriching an outbound list and you need to know which secure email gateway (Proofpoint, Mimecast, Barracuda, Cisco IronPort) or mailbox provider (Google, Microsoft) sits behind each domain; when enterprise emails are not landing; or when the user mentions SEGs, MX records, ESP matching, inbox placement at large companies, or splitting campaigns by email provider, even if they never say gateway. Also use when someone is about to pay a data vendor for the MX provider, since DNS gives it free."
license: MIT
compatibility: Python 3.10+ with dnspython. Paid gap-fill needs LEADMAGIC_API_KEY or PROSPEO_API_KEY in .env, or a logged-in deepline CLI.
metadata:
  author: automatewithuday
  source: martechs.io
  version: "1.0"
  category: infrastructure
---

# Email Gateway Detection

Domains in, security gateway and mailbox provider out. Tag every lead with what sits in front of its inbox (Proofpoint, Mimecast, Barracuda, Cisco, nothing) so outbound can be routed per gateway instead of blasted blind.

## How to apply this skill

When asked which gateway or mail provider sits behind a list of domains, or why enterprise emails are not landing:

1. Gather inputs: a CSV with a `domain` or `email` column; whether the user has a LeadMagic or Prospeo key or a logged-in Deepline CLI; whether they want only the unknowns filled (default) or every row cross-checked (`--all`).
2. Run `python scripts/detect_gateway.py --in <csv> --out <csv>` from this folder. Do not classify MX hosts by hand or in prose; the script and `references/gateway-map.json` are the source of truth.
3. Report: the per-vendor counts and credits from stderr, how many rows have `seg_conflict=true`, any `unmapped_vendor_value` lines (add those to the map), and the routing table below applied to the result.

Do not: treat LeadMagic `mx_gateway` as a gateway signal, or pay a vendor for every row when DNS already answered most of them.

## Quick start

One command. Input is any CSV with a `domain` or `email` column.
```bash
pip install dnspython
python scripts/detect_gateway.py --in domains.csv --out final.csv
```
It runs the free DNS lookup on every row, then LeadMagic only on the rows DNS could not classify. `final.csv` keeps every input column and adds `seg_vendor` and `mailbox_provider`, which is all downstream needs. The stderr summary lists counts per vendor, which route each vendor used, and credits spent.

**Keys.** The paid gap-fill needs one of two things. An own key always wins when both are present:
- Your own vendor key: `LEADMAGIC_API_KEY` (and `PROSPEO_API_KEY` if you use Stage 2) in the environment or a `.env` file in the working directory. Calls go straight to the vendor on your account.
- Otherwise the Deepline CLI: `deepline auth status` must be green, and Deepline bills its own credits.
Keys are never printed or written to the output.

When the list came from a Prospeo export that already has `mx_provider`, or you want a second opinion on every row, see the waterfall below. Otherwise the quick start is the whole workflow.

## Output schema

Every lead leaves this skill with these fields appended. Nothing else is required downstream.

| Field | Values | Notes |
|---|---|---|
| `domain` | `acme.com` | lowercased, `www.` stripped |
| `seg_vendor` | `proofpoint`, `mimecast`, `barracuda`, `cisco`, other names from `gateway-map.json`, `none`, `unknown` | `none` = direct to Google/Microsoft/Zoho. `unknown` = unmapped host, needs Stage 2. Empty if `seg_status` is not `ok` |
| `mailbox_provider` | `google`, `microsoft`, `zoho`, `other` | behind a gateway this comes from SPF |
| `seg_source` | `dns`, `prospeo`, `leadmagic` | which stage set `seg_vendor` |
| `mailbox_source` | `dns_mx`, `dns_spf`, `prospeo`, `leadmagic`, empty | which signal set `mailbox_provider` |
| `seg_status` | `ok`, `nxdomain`, `no_mx`, `null_mx`, `timeout`, `servfail` | see `references/errors.md` |
| `mx_hosts` | `mx0a.pphosted.com\|mx0b.pphosted.com` | preference order |
| `seg_checked_at` | ISO 8601 UTC | cache expiry is based on this |
| `seg_conflict` | `true`, `false` | Stage 3 disagreed with DNS; review, do not auto-fix |
| `vendor_raw` | `prospeo:Proofpoint leadmagic:Proofpoint/Proofpoint/gateway=True` | raw vendor labels from Stages 2 and 3, for reviewing conflicts and unmapped values. Empty until a paid stage runs |
| `email_status` | `valid`, `valid_catch_all`, `catch_all`, `invalid`, `unknown`, empty | LeadMagic verdict from Stage 3, free byproduct of the gateway check |

## The waterfall

DNS goes first because MX records are the ground truth the paid tools read too. Paid stages only fill gaps or cross-check.

**Stage 0, at list build (Prospeo search), optional.** If the list is being pulled from Prospeo anyway, use the `company_email_provider` filter to split `Proofpoint` and `Mimecast` accounts out before pulling contacts. Barracuda and Cisco are not filterable here; they fall under `Other` and get caught in Stage 1.

**Stage 1, free (DNS).** Runs inside `detect_gateway.py`, or on its own with `scripts/mx_lookup.py --in leads.csv --out tagged.csv`. One lookup per unique domain, cached with a TTL (default 45 days). Classification:
1. Walk MX hosts in preference order; first host matching a gateway suffix sets `seg_vendor`.
2. No gateway and a host matches Google/Microsoft/Zoho: `seg_vendor=none`, provider from MX.
3. Otherwise read the SPF TXT record: `include:spf.protection.outlook.com` means Microsoft, `include:_spf.google.com` means Google. This is how M365 behind Proofpoint gets detected.
4. Nothing matched: `seg_vendor=unknown`, go to Stage 2.

**Stage 3, gap-fill and cross-check (LeadMagic, 0.09 Deepline credits or 0.25 LeadMagic credits on your own key).** The default paid stage in `detect_gateway.py`. It calls `leadmagic_email_validation` once per `unknown` domain (the row's email, or `info@domain` when there is none) and reads `mx_security_gateway`. `mx_gateway` is never null: on a plain Google or Microsoft domain it holds the mailbox host name, so only the boolean decides. Rows still `unknown` are filled with `seg_source=leadmagic`; a self-hosted domain with `mx_security_gateway=false` becomes `none` with `mailbox_provider=other`. With `--all` it runs on every row instead: a disagreement with DNS then sets `seg_conflict=true` and keeps the DNS value. Conflicts usually mean a hybrid setup or a stale cache entry.
```bash
python scripts/detect_gateway.py --in leads.csv --out final.csv --all   # cross-check every row
```

**Stage 2, optional (Prospeo, 0.55 Deepline credits or 1 Prospeo credit on your own key).** Same signal as LeadMagic at six times the price, so only worth it when the label is already in a Prospeo export you have (`company.email_tech.mx_provider`). `--stage 2` or `--stage 23` turns it on for `unknown` rows. Labels map to `seg_vendor` through the `names` lists in `references/gateway-map.json`.

**Feeding the map.** Any run prints `unmapped_vendor_value` when a vendor names a gateway the map lacks. Look up one real MX host for that domain and add both suffix and label to `references/gateway-map.json`, so DNS catches it free next time. Paid answers are written back to the cache, so no domain is bought twice.

Vendors are called through the Deepline CLI (`deepline auth status` must be green). Field paths and the full conflict rule are in `references/vendor-fields.md`.

## Routing rules

| seg_vendor | Route |
|---|---|
| `none` | standard campaigns, ESP-matched by `mailbox_provider` |
| `proofpoint` | its own campaign |
| `mimecast` | its own campaign, shortest copy variant, no links in step 1 |
| `barracuda` | its own campaign |
| other named gateway | pooled `seg_other` campaign |
| `unknown` after Stage 2 | standard campaign, flagged for review |
| any gateway on a Tier 1 account | multichannel track, not email-only |
| `seg_status` not `ok` | drop, except `timeout`/`servfail` which rerun |
| `seg_conflict` = `true` | send as tagged, but pull these rows (`vendor_raw` shows both answers) and check one MX record by hand before the next list |

One campaign per major gateway is the point of the whole skill: it is the only way to learn what actually lands per gateway instead of reading one blended reply rate.

## Cost estimate

Per 10,000 leads across roughly 2,500 unique domains. Deepline credit prices observed on real calls, 22 Sept 2026 (1 credit is roughly $0.10):

| Stage | Calls | Cost |
|---|---|---|
| 0 Prospeo filter | part of search | no extra |
| 1 DNS | ~2,500 lookups, fewer on rerun | $0 |
| 2 Prospeo enrich | only unknowns, typically a small share | 0.55 credits per matched company; a repeat call on the same domain was charged 0 |
| 3 LeadMagic validation, default | only unknown domains, typically a small share | 0.09 Deepline credits (0.25 on your own key) per definitive result, 0 for `unknown` |
| 3 LeadMagic validation, `--all` | one call per domain, ~2,500 | ~225 Deepline credits or ~625 LeadMagic credits, no extra for gateway fields |

`detect_gateway.py` prints credits per stage at the end of every run; use those numbers, not this table, when reporting spend. Runtime for Stage 1 is dominated by DNS latency; 2,500 domains sequentially is a few minutes. Stages 2 and 3 are one CLI call each, sequential; move to a Deepline play past ~5k rows.

## Common mistakes

- Reading LeadMagic `mx_gateway` as "gateway present". It names Google or Microsoft too. Only `mx_security_gateway=true` means a gateway.
- Running the paid stage on every row by default. DNS already answers most domains; keep `--all` for a deliberate cross-check.
- Starting each list with a fresh cache. Reuse one `.seg_cache.json` across lists so no domain is looked up or bought twice.
- Adding a gateway host or vendor label in code. Both belong in `references/gateway-map.json`; the script reads it.
- Paying Prospeo for the label when LeadMagic returns the same signal for less. Use Stage 2 only when the label is already in an export you have.
- Editing `seg_vendor` on a conflict row. `seg_conflict=true` is a review flag; the DNS value stays until a human checks.

## Errors

Full table in `references/errors.md`. Key rules: never cache `timeout` or `servfail`; drop `nxdomain`, `no_mx`, `null_mx`; log post-send bounce strings against `seg_vendor` so failures can be attributed to the right layer.

## Learnings

Carry these into copy and sending decisions. Update this section as campaign data comes in.

- Gateways accept most mail and then quarantine it. Bounce rates understate the problem; measure replies per `seg_vendor`.
- Mimecast behaved differently from Proofpoint and Barracuda in field tests: 1:1 outreach from an established domain was blocked while the same copy landed at the other two. Ultra-short copy (under 7 words) got through. Treat Mimecast as its own experiment.
- Links, especially scheduling links and new tracking domains, are a common block reason. Keep step 1 link-free for gateway campaigns.
- ESP matching (Gmail to Gmail) and deliberately mixing providers are both argued for. Test per gateway, do not assume.
- Aged or expired domains do not fix gateway filtering; an established main domain still got blocked by Mimecast.
- LeadMagic labels cloud mailbox hosts in `mx_gateway` too (`Microsoft 365`, `Google Workspace` with `mx_gateway_type=Cloud Mailbox Host`). Trusting that field alone would flag every M365 tenant as gateway-protected; only `mx_security_gateway` counts.
- MX only sees inline gateways. Post-delivery API tools (Abnormal and similar) never appear in DNS, and no vendor field will reveal them either.

## Files

- `scripts/mx_lookup.py`: Stage 1 on its own, stdlib plus `dnspython`. `detect_gateway.py` imports it.
- `scripts/detect_gateway.py`: the one-command entry point. Runs Stage 1 inline, then Stage 3 (and 2 on request), applies the conflict rule. Stdlib only, shells out to the `deepline` CLI.
- `references/gateway-map.json`: MX suffixes and vendor labels (`names`) per gateway and provider. Extend it; do not hardcode hosts or labels elsewhere.
- `references/vendor-fields.md`: verified Deepline response paths for Prospeo and LeadMagic and the conflict rule. Read before touching Stage 0, 2 or 3.
- `references/errors.md`: DNS statuses and gateway bounce strings. Read when handling failures.
