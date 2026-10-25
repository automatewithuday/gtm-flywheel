---
name: abm-target-accounts
description: Use when building, sizing, scoring, tiering, or managing a target account list for ABM — working out how many accounts a revenue target needs, defining ICP criteria, building lookalikes from best customers, enriching and scoring accounts (Clay, BuiltWith, Apollo), setting A/B/C/D tiers, importing accounts into HubSpot with ABM stage properties, syncing company lists to LinkedIn Campaign Manager, or automating stage progression from ad engagement. Also use when a team is starting ABM from leads instead of accounts, or is over-engineering account scoring with intent and de-anonymization data.
license: MIT
metadata:
  author: automatewithuday
  source: martechs.io
  version: "1.0"
---

# ABM target account lists

How to build, score, stage, and manage target account lists for ABM campaigns.

ABM starts with accounts, not leads. You're choosing who to pursue before anything else. Every dollar of ad spend and every BDR hour gets concentrated on accounts that actually fit your ICP.

Related: `abm-measurement` (program metrics and ROI) and `abm-retargeting` (what to do with accounts once they engage). The stage thresholds below — 50 impressions, 5 clicks or 10 engagements — are the same ones those skills use.

## How to apply this skill

When asked to build or fix a target account list:

1. Gather inputs (ask for what's missing):
   - Revenue target, ACV, close rate, qualification rate — if the user has no stage rates, use the doc's benchmark rates in the sizing example
   - Best-customer list from the CRM (for lookalikes) and any win-loss analysis
   - Tools available: Clay, BuiltWith, Apollo, HubSpot, LinkedIn Campaign Manager, a HubSpot↔LinkedIn connector
   - Whether the list is for 1:1, 1:few, or 1:many plays (decides which tiers are in scope)
2. Work in this order: size the list → build and enrich → score and tier → import to CRM with stage properties → set up stage lists and automation → sync to LinkedIn.
3. Report: required account count with the math shown, the build steps in order, tier cut-offs, the five stage lists with their thresholds, and the automation rules. Say what the program should look like at 90 days and at maturity using the illustrative figures.

Do not add website-visit or intent-based scoring on top of this. Score from ad engagement pushed to the CRM; keep the model simple enough to execute.

## How many accounts you need

The math matters: to close $1M in ARR from ABM with a $50K ACV, 25% close rate, and 75% qualification rate, you need ~3,250 target accounts in your campaigns (working backwards through stage conversion benchmarks).

```
Revenue Target ÷ ACV = Deals Needed
Deals ÷ Close Rate ÷ Qualification Rate ÷ Considering Rate ÷ Interested Rate ÷ Aware Rate
= Total Target Accounts
```

Example:

```
$1,000,000 ÷ $50,000 = 20 deals
20 ÷ 0.25 ÷ 0.75 ÷ 0.20 ÷ 0.30 ÷ 0.55 = ~3,250 accounts
```

The headline number: across these stages, roughly 2.5% of targeted accounts convert to pipeline (an open, qualified opportunity) and about 0.6% close. So a ~3,250-account program produces ~80 opportunities and ~20 deals at a $50K deal size.

## Building the list

### Lookalikes from your best customers

1. Export top enterprise/growth customers from CRM
2. Identify shared attributes (industry, size, tech stack, funding stage)
3. Use Clay to find similar companies that match the pattern
4. Cross-reference with BuiltWith for technographic match

### Build pipeline

```
1. Define ICP criteria (firmographic + technographic)
   → Use win-loss analysis from CRM to identify patterns

2. Build initial account list
   → Clay + BuiltWith API for technographic targeting
   → Apollo for firmographic + contact discovery
   → CRM export for recycled/closed-lost accounts

3. Enrich accounts
   → Clay enrichment (revenue, tech stack, funding, headcount)
   → BuiltWith for technology detection
   → ICP scoring (0-100)

4. Score and tier
   → A-tier (80-100): Perfect fit + strong signals
   → B-tier (60-79): Good fit
   → C-tier (40-59): Okay fit - maybe for 1:many only
   → D-tier (<40): Exclude

5. Import to CRM (HubSpot)
   → Create company records
   → Set ABM Campaign Name property
   → Set ABM Stage = "Identified"
   → Add to ABM campaign active list

6. Sync to LinkedIn Campaign Manager
   → Push company lists from HubSpot to LinkedIn
   → Filter by persona using LinkedIn's native targeting
   → Wait ~48 hours for audience to be ready
   → Minimum 300 LinkedIn members required to start a campaign
```

## Scoring: keep it simple

Critical lesson from real ABM programs: teams that overcomplicate scoring by adding website visits, page-level intent signals, and weighted scores across multiple data sources struggle to execute because:

- Website visitor de-anonymization is unreliable (in one test, a de-anonymization tool identified only 1 company out of 300 visitors — itself)
- Complex scoring models break in practice

What actually works: use quantitative ad engagement data from LinkedIn pushed to CRM, plus qualitative campaign engagement data for personalizing outreach.

## Stage lists in the CRM

Create separate active lists for each stage of each campaign:

- `[Campaign Name] - Identified` — ICP score ≥ threshold, ABM Campaign = X
- `[Campaign Name] - Aware` — cumulative impressions ≥ 50
- `[Campaign Name] - Interested` — cumulative clicks ≥ 5 OR engagements ≥ 10
- `[Campaign Name] - Considering` — demo booked OR trial signup
- `[Campaign Name] - Selecting` — deal stage = open

## Stage progression automation

```
Trigger: Company property "LinkedIn Ad Clicks - 30d" changes

IF Clicks ≥ 5 AND ABM Stage = "Aware":
  → Update ABM Stage = "Interested"
  → Remove from Aware LinkedIn audience
  → Add to Interested LinkedIn audience
  → Trigger BDR notification workflow

IF Impressions ≥ 50 AND ABM Stage = "Identified":
  → Update ABM Stage = "Aware"
  → Content changes automatically via audience list updates
```

Note: as of early 2025, HubSpot cannot natively pull company-level engagement data from LinkedIn Campaign Manager. You need a connector tool (ZenABM, Fibbler, or custom API).

## What a well-run program looks like

The figures below are illustrative of a well-run program. They show the shape of ABM economics over time rather than a guaranteed result.

### First campaign (roughly 90 days)

| Metric | Illustrative result |
|---|---|
| Accounts touched | ~1,400 |
| Total cost | ~$52K (ads + tools) |
| Pipeline generated | ~$655K |
| Pipeline per $ spent | ~$12 |
| Team | ~4.5 FTE |

### Mature program (cumulative, 12–18 months)

| Metric | Illustrative result |
|---|---|
| Accounts touched | ~26,000 |
| Total LinkedIn ad spend | ~$490K |
| Pipeline generated | ~$5.3M |
| Pipeline per $ spent | ~$11 |
| ROAS (closed won) | ~2x |
| Team | ~4.5 FTE |

Versus cold outbound: a mature ABM program typically reaches the same pipeline faster and at a lower cost than cold outbound alone.

## Quick reference

| Item | Rule / number |
|---|---|
| List size | Deals ÷ close ÷ qualification ÷ considering ÷ interested ÷ aware |
| Benchmark stage rates | Aware 55% · Interested 30% · Considering 20% · Qualified 75% · Close 25% |
| Headline conversion | ~2.5% of targeted accounts → pipeline · ~0.6% close |
| Worked example | $1M ARR at $50K ACV → 20 deals → ~3,250 accounts → ~80 opps |
| Tiers (ICP score 0–100) | A 80–100 · B 60–79 · C 40–59 (1:many only) · D <40 exclude |
| Stage thresholds | Aware ≥50 impressions · Interested ≥5 clicks or ≥10 engagements · Considering demo/trial · Selecting open deal |
| LinkedIn audience | Min 300 members · ~48h to be ready |
| HubSpot ↔ LinkedIn engagement | Needs a connector (ZenABM, Fibbler, custom API) |
| 90-day shape | ~1,400 accounts · ~$52K · ~$655K pipeline · ~$12 per $1 |
| Mature shape | ~26,000 accounts · ~$490K ads · ~$5.3M pipeline · ~$11 per $1 · ~2x ROAS |

## Common mistakes

- Starting from leads — pick the accounts first; every dollar and BDR hour concentrates on them.
- Guessing list size — work backwards from the revenue target through the stage rates.
- Over-engineering scoring — website visits, intent feeds, and multi-source weighted scores break in practice. Score from LinkedIn ad engagement pushed to the CRM.
- Trusting de-anonymization — one test identified 1 company out of 300 visitors, itself.
- Putting C-tier accounts into 1:1 plays — C-tier is 1:many only; D-tier is excluded.
- Launching under 300 LinkedIn members, or before the ~48h audience sync completes.
- Expecting stage automation to work out of the box in HubSpot — company-level LinkedIn engagement needs a connector.
