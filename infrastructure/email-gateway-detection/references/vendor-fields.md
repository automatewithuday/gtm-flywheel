# Vendor fields for Stages 0, 2 and 3

## Contents
- Two routes: own key or Deepline
- Prospeo (Stage 0 filter, Stage 2 enrich)
- LeadMagic (Stage 3 validation) and the conflict rule

## Two routes: own key or Deepline

`detect_gateway.py` picks the route per vendor. With `LEADMAGIC_API_KEY` or `PROSPEO_API_KEY` set (environment or `.env`), it calls the vendor directly. Otherwise it shells out to `deepline tools execute <tool> --input '{...}' --json`, which passes the vendor payload through unrenamed under `toolResponse.rawV2` with Deepline billing at `billing.credits_charged`. The parsers read the same field paths on both routes.

Direct endpoints, verified against vendor docs on 23 Sept 2026 (not yet exercised with a live key; the request and response shapes are what the docs show and match the Deepline pass-through):

| Vendor | Request | Auth header | Body | Cost on your account |
|---|---|---|---|---|
| Prospeo | `POST https://api.prospeo.io/enrich-company` | `X-KEY` | `{"data": {"company_website": "acme.com"}}` | 1 credit per match, 0 when not found or already enriched on the account |
| Prospeo bulk (not used yet) | `POST https://api.prospeo.io/bulk-enrich-company` | `X-KEY` | `{"data": [{"identifier": "1", "company_website": "acme.com"}, ...]}` max 50; response `matched[]` carries `identifier` and `company` | same |
| LeadMagic | `POST https://api.leadmagic.io/v1/people/email-validation` | `X-API-Key` | `{"email": "a@acme.com"}` | 0.25 credits for `valid` or `invalid`, 0 for `unknown`; the response carries `credits_consumed` |

Field names and paths below were verified against real Deepline responses on 22 Sept 2026 and match the vendor docs.

Value to `seg_vendor` mapping lives in `gateway-map.json` under each entry's `names` list (case-insensitive exact match). `names_verified` marks labels seen in a real response; the rest come from vendor docs and are unproven until the 1,000-domain run.

## Prospeo

**Stage 0, search filter:** `company_email_provider`
Accepted values: `Microsoft`, `Google`, `Proofpoint`, `Mimecast`, `Other`.
Anything else (Barracuda, Cisco, etc.) is grouped under `Other`. Filtering on an unlisted value returns nothing.

**Stage 2, tool `prospeo_enrich_company`.** Input `{"company_website": "acme.com"}`. Deepline compiles it onto Prospeo's bulk endpoint (max 50 per batch), rate limit 10 requests per second.

The gateway label is nested, not top-level:

```
toolResponse.rawV2.company.email_tech.mx_provider   ->  "Proofpoint"
toolResponse.rawV2.company.email_tech.domain        ->  "pfizer.com"
toolResponse.rawV2.error                            ->  false
toolResponse.rawV2.free_enrichment                  ->  false
```

Other keys on `company` (not used here): company_id, name, website, domain, industry, employee_count, employee_range, location, naics_codes, linkedin_url, founded, revenue_range, technology, job_postings, funding, keywords.

Prospeo documents ~105 case-sensitive `mx_provider` values. Labels currently mapped, all in `gateway-map.json`:
Proofpoint (verified), Mimecast, Barracuda, Cisco IronPort, MessageLabs, Symantec, Trend Micro, Sophos, Hornetsecurity, MailControl, FireEye, FortiMail, SpamTitan, TitanHQ, VadeSecure, SpamExperts, AntispamCloud, Mailguard, Google, Microsoft.

Any other value: the row stays `seg_vendor=unknown`, the value is kept in `vendor_raw` and printed at the end of the run as `unmapped_vendor_value`. Look up one real MX host for that domain, then add both the suffix and the label to `gateway-map.json`.

Observed cost: 0.55 Deepline credits per matched company (list price on the tool is the same). Only call for Stage 1 `unknown` rows.

## LeadMagic

**Stage 3, tool `leadmagic_email_validation`.** Input `{"email": "a@acme.com"}`. No batch endpoint on Deepline, one call per email.

Fields pass through as-is at `toolResponse.rawV2.*`:

| Field | Seen values | Use |
|---|---|---|
| `mx_record` | `mxb-00013f02.gslb.pphosted.com` | raw MX host, compare with Stage 1 `mx_hosts` |
| `mx_provider` | `Proofpoint`, `Microsoft 365`, `Google Workspace` | mailbox provider label; on a gateway domain it repeats the gateway name |
| `mx_gateway` | `Proofpoint`, `Microsoft 365`, `Google Workspace` | never null on a resolvable domain: it names the cloud host too |
| `mx_gateway_type` | `Email Security Gateway`, `Cloud Mailbox Host` | category |
| `mx_security_gateway` | `true`, `false` | the only reliable gateway signal, drives the conflict check |
| `email_status` | `valid`, `valid_catch_all`, `catch_all`, `invalid`, `unknown` | copied to the output |

Do not treat a non-null `mx_gateway` as "gateway present". Read `mx_gateway` only when `mx_security_gateway` is true.

Conflict rule (implemented in `scripts/detect_gateway.py`, `apply_leadmagic`):
- Stage 1 or 2 said `none` and `mx_security_gateway` is true: `seg_conflict=true`.
- Stage 1 or 2 named a gateway and `mx_security_gateway` is false: `seg_conflict=true`.
- Both name a gateway but different ones: `seg_conflict=true`.
- Row still `unknown`: LeadMagic fills it (`seg_source=leadmagic`), no conflict. `mx_security_gateway=false` alone is enough for `none`; the provider stays `other` when the label is unmapped (seen: `Other` on debian.org).
Never overwrite the DNS value automatically.

Observed cost: 0.09 credits per definitive result, 0 when `email_status=unknown`. List price on the tool page says the same 0.09.
