---
name: deliverability-test
description: "Use when comparing reply, bounce, and positive-reply rates by inbox type (SMTP vs Gmail vs Outlook) across a Smartlead account, or deciding which inbox provider to buy more of. Also use when a mixed inbox fleet shows inconsistent results and the provider is the suspected variable."
license: MIT
metadata:
  author: automatewithuday
  source: growthenginenowoslawski/coldoutboundskills
  curator: automatewithuday
  version: "1.0"
  category: iterate-and-automate
---

# Deliverability Test — Inbox Type Comparison

Compare reply rates, bounce rates, and positive reply rates broken down by inbox type (SMTP, Gmail / G Suite, Outlook / Office365) across your Smartlead account. Use it to answer "are my Gmail inboxes performing better than my SMTP ones?" or "why is one inbox type bouncing more than the others?"

## Why this exists

Different inbox types have different deliverability characteristics:
- **Gmail / G Suite** — highest trust, fewest bounces, often best reply rates
- **Office365** — good reputation, but stricter spam filtering
- **SMTP** (Zapmail, Maildoso, Mailforge, custom) — varies wildly by provider, often has higher bounces in the first 30 days of domain life

If your campaigns mix inbox types, this skill shows which type is earning its keep.

## What you need

- `SMARTLEAD_API_KEY` in env
- Optional: `--client-id=<id>` for sub-clients
- Optional: `--days=<N>` lookback (default 7)

## Steps

Pull outcomes with `flywheel/pull_outcomes.py`; rates and rankings come from `flywheel/learn.py` (see flywheel/README.md).

## Output

```
Inbox Type Comparison — last 7 days

Type              Inboxes    Sent     Replies   Bounces    Reply %   Bounce %
---------------   ------   -------   -------   -------    -------   --------
G Suite               12    3,120       42        12        1.35%      0.38%
Office365             24    6,440       65        28        1.01%      0.43%
SMTP                  44   10,780       55        98        0.51%      0.91%
---------------   ------   -------   -------   -------    -------   --------
TOTAL                 80   20,340      162       138        0.80%      0.68%

Takeaways:
- G Suite has the highest reply rate (1.35%) and lowest bounce rate.
- SMTP reply rate is 60% lower than G Suite — investigate domain reputation.
- SMTP bounce rate is 2x average — run /email-deliverability-audit on SMTP domains.
```

## How it works

1. Pulls all email accounts via `/email-accounts` API paginated
2. Groups by `type` field (GMAIL, OUTLOOK, SMTP, etc.)
3. For each campaign that uses these inboxes, pulls per-inbox stats from `/campaigns/{id}/analytics` and `/campaigns/{id}/sequence-analytics-by-email-account`
4. Aggregates sent/replies/bounces within each type group
5. Prints formatted table

## Common gotchas

- **Reply rate here is RAW, not positive.** For positive reply rate (the more important metric), use [`/positive-reply-scoring`](../positive-reply-scoring/SKILL.md).
- **Small inbox counts are noisy.** If you only have 2 Gmail inboxes and 40 SMTP ones, the Gmail numbers aren't statistically meaningful.
- **Inbox type labels can be surprising.** Some providers register as "SMTP" even when they're technically Gmail-proxied. Trust the label Smartlead gave them.

## What to do next

**If one inbox type is underperforming:** [`/smartlead-inbox-manager`](https://github.com/automatewithuday/GTM-Skills/tree/main/skills/smartlead-inbox-manager/) to retire the bad ones (tag `retired`, disable warmup). If replacements are needed, [`/zapmail-domain-setup-public`](https://github.com/automatewithuday/GTM-Skills/tree/main/skills/zapmail-domain-setup-public/) to provision new domains on a different provider type.

**If all types are healthy:** back to the weekly rhythm via [`/cold-email-weekly-rhythm`](https://github.com/automatewithuday/GTM-Skills/tree/main/skills/cold-email-weekly-rhythm/).

**Or wait:** small sample sizes (<500 sends per type) are noisy. If your results are inconclusive, run again in 7 days with more data.

## Related skills

- [`/email-deliverability-audit`](https://github.com/automatewithuday/GTM-Skills/tree/main/skills/email-deliverability-audit/) — full audit (SPF/DKIM/DMARC + reputation + spam placement)
- [`/positive-reply-scoring`](../positive-reply-scoring/SKILL.md) — the metric that matters, not just reply rate
- [`/smartlead-inbox-manager`](https://github.com/automatewithuday/GTM-Skills/tree/main/skills/smartlead-inbox-manager/) — rotate out bad inboxes, tag by performance
