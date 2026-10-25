---
name: email-waterfall
description: "Use when a list has people (first name, last name, company domain, LinkedIn URL) but missing or unverified work emails, before anything is uploaded to Smartlead; when a list builder (Blitz, Prospeo, competitor-engagers, disco-like, Google Maps) returned rows with an empty email column; when coverage from a single provider is stuck around 40%; or when someone wants to validate emails with MillionVerifier. Also use when someone is about to guess emails from a first.last@domain pattern, which this skill refuses to do."
license: MIT
compatibility: Python 3.11+ with httpx, python-dotenv and pyyaml (pip or uv). Needs GETLEADS_API_KEY in .env and a logged-in deepline CLI (LeadMagic, Prospeo, FullEnrich, MillionVerifier and BounceBan run through Deepline, no separate keys).
metadata:
  author: automatewithuday
  source: martechs.io
  version: "1.0"
  category: list-building
---

# Email Waterfall

Finds a verified work email for every row of a list by trying providers in order, cheapest first, and stopping at the first verified hit. It never builds an email from a name pattern, it never pays twice for the same person, and anything it cannot verify is kept with its status so it can go to a LinkedIn track instead of a live email sequence.

## How to apply this skill

When asked to fill in or verify emails for a list:

1. Gather inputs: a CSV with `first_name,last_name,company_domain,linkedin_url` (extra columns are kept), the per-run spend cap in USD, and whether the GetLeads daily allowance covers the row count (GetLeads MCP `get_fair_use`, free).
2. Run `scripts/outbound/waterfall.py` from the `scripts/` folder, dry run first, then for real in batches of 150. Do not hand-pick emails, do not reorder providers by habit, and do not add pattern guessing.
3. Report: the `<out>.report.md` numbers (% verified, % catch_all, % unknown, % not_found, hits per provider, spend), five sample rows per status, and which rows have `domain_match=no`. Only `verified` rows may go to Smartlead.

Do not: treat a catch-all or unknown address as sendable because the count looks small, or trust a verified email at a domain that is not the company on the list.

## Setup

```bash
cd skills/email-waterfall/scripts
pip install httpx python-dotenv pyyaml        # or: uv run --with httpx --with python-dotenv --with pyyaml python -m outbound.waterfall ...
python -m outbound.common --selftest          # prints OK; no network
python -m outbound.waterfall --selftest       # prints OK; no network
```

Keys: `GETLEADS_API_KEY` in the repo `.env` (the scripts search upward for it). Deepline: `deepline auth status` must show a workspace; install from https://code.deepline.com/INSTALL.md. Credit prices are constants at the top of `waterfall.py` and `common.py` (`DEEPLINE_CREDIT_USD`, `GETLEADS_CREDIT_USD`); edit them to your plans so the cap is honest.

## The waterfall

Default order, one line to change (`PROVIDERS` in `waterfall.py`, or `--providers`):

| Step | Provider | Input it gets | Cost | Notes |
|---|---|---|---|---|
| 1 | GetLeads `enrich/from-linkedin` | LinkedIn URL | 1 credit per hit, misses free | rows without a LinkedIn URL skip it |
| 2 | LeadMagic (via Deepline) | first name, last name, domain | 0.34 Deepline credits per result | skipped for rows with no domain |
| 3 | Prospeo (via Deepline) | LinkedIn URL + name + domain | 0.55 credits per result | also fills a blank company domain |
| 4 | FullEnrich (via Deepline, bulk async) | all four | variable, ~0.35 credits observed | polled with the free `get_result` call |

Verification: a provider that already returns `valid`/`VERIFIED` skips the verifier; everything else goes to MillionVerifier (0.06 credits), and a catch-all answer is re-checked once with BounceBan.

Stop rule per row, in this order:

```
verified   -> keep, stop
catch_all  -> keep with status, stop (a domain property: the next provider returns the same domain)
unknown    -> keep with status, stop
discard    -> drop the candidate (invalid, disposable, spam trap), try the next provider
exhausted  -> not_found
```

Output columns added to every input row: `email, email_status, email_provider, verifier, mx_class, domain_match, miss_reason`. Rows are never dropped; dedupe happens before any spend (LinkedIn URL first, then name + domain).

`domain_match` is `yes` when the email's domain is the company domain or shares its main label (clorox.com and thecloroxcompany.com match), `no` otherwise. A verifier proves the mailbox exists, not that it is your prospect; `no` rows are usually a namesake at another company or a person who has moved. Review them by hand. Observed on a real 10-row run: 2 of 9 hits before the explicit provider order fixed it, 1 of 10 after.

## Steps

1. `get_fair_use` on the GetLeads MCP. Stop and say so if the allowance cannot cover the rows.
2. Plan: `python -m outbound.waterfall ../../../leads.csv --out out/leads_enriched.csv --dry-run`. A dry run writes only `<out>.dryrun.csv` and `<out>.dryrun.report.md`, never the real output, and spends nothing.
3. Test on 10 rows for real, read the output, then continue.
4. Real run: `python -m outbound.waterfall <csv> --out out/leads_enriched.csv --batch 150 --cap-usd N`. The cap is a total for the run; Deepline plays get a hard `--max-credits` derived from the remaining budget. A cap abort keeps every processed row and marks the rest `cap_aborted`. Re-runs replay cached calls at $0 (`.cache/calls.jsonl`, git-ignored, contains emails; delete it when a project ends).
5. Read `out/leads_enriched.csv.report.md`. If `not_found` is above 30%, say so and ask before adding `deepline-play` (Deepline's own prebuilt waterfall, which picks its own vendors) as a last leg of `--providers`.
6. Split: `verified` is the only set eligible for Smartlead. `catch_all`, `unknown` and `not_found` go to a LinkedIn-only track.
7. Show the table and wait for approval before any upload (`/cold-email-starter-kit` or `/smartlead-campaign-upload-public`).

## Quick reference

| Flag | Meaning | Default |
|---|---|---|
| `--out PATH` | output CSV; report lands at `<out>.report.md` | required |
| `--dry-run` | print planned calls and estimate, spend nothing, write `<out>.dryrun.*` only | off |
| `--cap-usd N` | total spend cap for the run; aborts before the call that would exceed it | rows × $0.15 |
| `--batch N` | rows per batch | 150 |
| `--providers a,b,c` | waterfall order from `getleads,leadmagic,prospeo,fullenrich,deepline-play` | `getleads,leadmagic,prospeo,fullenrich` |
| `--selftest` | offline self-check, prints `OK` | |

Measured on 10 real rows (Oct 2026): 10/10 verified, 7 by LeadMagic, 2 by GetLeads, 1 by Prospeo, $0.33 total; the earlier Deepline-picks-vendors run found 9/10 for $1.22 with two namesakes. The `hits per provider` line is the data for reordering.

## Common mistakes

- Guessing emails from a name pattern — the script refuses to; do not add it by hand.
- Reordering providers by habit instead of by the `hits per provider` line — the provider that carries your market should run first.
- Trusting `domain_match=no` rows — FullEnrich and Prospeo return a real mailbox for the person's *current* employer, which is not always the company on your list.
- Skipping dedupe, so the same person is paid for twice.
- Sending `catch_all` or `unknown` rows to Smartlead.
- Running the full list before looking at the first 10 rows.
- Setting `--cap-usd` from the estimate alone: real Deepline rows cost 1 to 5 credits each, and the hard cap now follows the remaining budget, so give the run the budget you actually mean.

## Related skills

- [`/blitz-list-builder`](../blitz-list-builder/SKILL.md), [`/competitor-engagers`](../competitor-engagers/SKILL.md), [`/disco-like`](../disco-like/SKILL.md), [`/google-maps-list-builder`](../google-maps-list-builder/SKILL.md) — produce the rows this skill fills in
- [`/list-quality-scorecard`](../list-quality-scorecard/SKILL.md) — grade the result
- [`/email-gateway-detection`](../email-gateway-detection/SKILL.md) — the `mx_class` column is a lighter version of what that skill does from DNS
- [`/cold-email-starter-kit`](../cold-email-starter-kit/SKILL.md) — upload the `verified` rows
