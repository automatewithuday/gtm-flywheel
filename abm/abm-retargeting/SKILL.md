---
name: abm-retargeting
description: Use when planning, building, or troubleshooting retargeting campaigns for ABM target accounts — segmenting audiences by engagement level or page visited, setting ad frequency caps and creative rotation, sequencing a multi-channel play (LinkedIn, Meta, Google, email, BDR, direct mail) after a trigger like a pricing-page visit, setting up website or matched audiences in LinkedIn Campaign Manager, Meta, or Google Ads, syncing CRM (HubSpot) lists to ad audiences, or weighting multi-touch attribution for retargeting. Also use when someone treats ABM retargeting like generic display retargeting or is seeing ad fatigue on target accounts.
license: MIT
metadata:
  author: automatewithuday
  source: martechs.io
  version: "1.0"
---

# ABM retargeting

Audience segmentation, frequency management, and multi-channel orchestration for Account-Based Marketing retargeting campaigns.

ABM retargeting is not the same as generic display retargeting. ABM retargeting:

1. **Targets known accounts** — people at specific companies already in your ICP
2. **Respects the buying committee** — different messages for different roles
3. **Coordinates across channels** — ads + email + BDR outreach + direct mail in sync
4. **Accelerates pipeline** — re-engages warm accounts that stalled
5. **Wins back lost deals** — systematically reactivates churned or lost opportunities

Related: `abm-measurement` for program-level metrics, ROI, and reporting. The attribution weights in this skill are for optimizing retargeting touches, not for reporting program ROI.

## How to apply this skill

When asked to plan, build, or fix ABM retargeting:

1. Gather inputs (ask for what's missing):
   - Target account list and each account's CRM/ABM stage
   - Which site pages are tagged (LinkedIn Insight Tag, Meta Pixel, Google Tag) and which pages matter (pricing, demo, case studies, blog)
   - Cumulative touchpoints per account (to place it in a tier)
   - Channels available: LinkedIn, Meta, Google, email, BDR, direct mail
   - Current frequency and number of active creatives
   - Which accounts are high-value and which contacts are executives
2. Build in this order: segment tiers → frequency and rotation plan by audience temperature → day-by-day multi-channel play → platform audience setup → CRM sync loop.
3. Report: the tier each account falls into and the content it should get, the frequency cap and rotation cadence per segment, the play as a day-by-day schedule, and the exact setup steps for each platform in use.

Do not run one ad on repeat, use lookalike audiences for ABM, or prospect on Meta — retargeting only. Every audience is known accounts who visited, never anonymous traffic.

## Audience segmentation

### Engagement-based tiers

Score accounts by cumulative engagement:

```
1-2 touchpoints  → Light engagement    → Awareness content
3-5 touchpoints  → Moderate engagement → Solution content
6-10 touchpoints → Heavy engagement    → Conversion content
10+ touchpoints  → Hot account         → BDR outreach + direct offers
```

### Website retargeting setup

```
1. Install LinkedIn Insight Tag on all pages
2. Create URL-based audiences for key pages:
   - /pricing → "Pricing Page Visitors"
   - /demo → "Demo Page Visitors"
   - /case-studies/* → "Case Study Readers"
   - /blog/* → "Blog Readers"
3. Set lookback windows (7, 30, 90, 180 days)
4. Exclude converted leads to avoid waste
```

## Frequency management

- **Too low:** account never remembers you, no brand recall, wasted impressions.
- **Too high:** ad fatigue, negative brand perception, wasted budget, annoying buyers.

**Target: about 4 impressions per person per week.** Bottom-of-funnel accounts can run higher — up to roughly 15 per 30 days — because they are close to a decision and the reinforcement is intentional.

Creative rotation is what makes this work. Run several distinct ads, not one ad on repeat. At about 4 per week with 3–4 active creatives, each person sees variety, so the frequency stays productive rather than fatiguing.

### Rotation schedule by audience temperature

```
HOT audiences (0-14 days):
  → Rotate creative every 2 weeks
  → 3-4 active variants minimum
  → Test different CTAs aggressively

WARM audiences (15-45 days):
  → Rotate creative every 3-4 weeks
  → 2-3 active variants
  → Test different angles/proof points

COOL audiences (46-90 days):
  → Rotate creative monthly
  → 2 active variants sufficient
  → Focus on reactivation messaging
```

## Multi-channel orchestration: pricing-page trigger play

```
Day 0:  Account visits pricing page (trigger)
        → Add to "Hot" retargeting segment

Day 1:  LinkedIn ad (case study)
        Email: "Saw you checking us out..."

Day 3:  Meta retargeting ad (social proof)

Day 5:  LinkedIn ad (product demo)
        BDR LinkedIn connection request

Day 7:  Email: Value proposition reminder
        LinkedIn ad (comparison content)

Day 10: BDR outreach email
        Meta ad (urgency/offer)

Day 14: Direct mail (if high-value account)
        LinkedIn InMail (if executive)

Day 21: If no response → move to "Warm" segment
        Reduce frequency, change messaging angle
```

## Attribution for retargeting

```
Multi-Touch Attribution for ABM:

First Touch (20%):    What channel introduced the account?
Last Touch (20%):     What channel got the meeting/conversion?
Linear (60%):         Distributed across all touchpoints

Weight adjustments:
  - BDR meeting booked: 2x weight
  - Content download: 1.5x weight
  - Ad click: 1x weight
  - Ad impression: 0.5x weight
  - Email open: 0.25x weight
```

## Platform setup

### LinkedIn Campaign Manager

```
1. Audience > Create Audience > Website
2. Select pages to retarget (use OR logic for multiple URLs)
3. Set lookback window (7/30/90/180 days)
4. Create matched audience from company list (separate)
5. Combine: Website visitors AND Company list
   → This retargets only known accounts who visited
```

### Meta Business Manager

```
1. Install Meta Pixel on ABM landing pages
2. Create Custom Audience from website traffic
3. Upload company email domains (limited match rate)
4. Use Lookalike audiences sparingly (dilutes ABM precision)
5. Focus on retargeting, not prospecting on Meta
```

### Google Ads

```
1. Create remarketing lists from Google Tag
2. Target specific pages (pricing, demo request)
3. Use RLSA for search intent + retargeting combo
4. Combine with company IP targeting (DemandBase, RollWorks)
5. Note: Match rates are low for B2B - use as supplement only
```

## CRM → ad platform data flow

```
HubSpot Company Lists (by ABM stage)
  ↓
Active list filters (e.g., "ABM Stage = Interested")
  ↓
HubSpot Ad Audiences (auto-sync to LinkedIn)
  ↓
LinkedIn Matched Audiences (~48 hour sync)
  ↓
Campaign Manager targets audience
  ↓
Engagement data flows back via Fibbler
  ↓
HubSpot updates account stage
  ↓
List membership changes automatically
  ↓
LinkedIn audience updates (removes old, adds new)
```

## Quick reference

| Decision | Rule |
|---|---|
| Content by engagement | 1–2 touches: awareness · 3–5: solution · 6–10: conversion · 10+: BDR outreach + direct offers |
| Frequency cap | ~4 impressions / person / week; bottom-of-funnel up to ~15 per 30 days |
| Creatives active | HOT 3–4 · WARM 2–3 · COOL 2 |
| Rotation cadence | HOT every 2 weeks · WARM every 3–4 weeks · COOL monthly |
| Audience temperature | HOT 0–14 days · WARM 15–45 · COOL 46–90 |
| Lookback windows | 7 / 30 / 90 / 180 days |
| Play exit | Day 21 with no response → move to Warm, reduce frequency, change angle |
| Attribution split | First 20% · Last 20% · Linear 60%; BDR meeting 2x, download 1.5x, click 1x, impression 0.5x, email open 0.25x |
| LinkedIn audience logic | Website visitors AND company list |
| CRM → LinkedIn sync | ~48 hours |

## Common mistakes

- Running one ad on repeat — frequency without rotation is fatigue. Keep 3–4 variants live for hot audiences.
- Retargeting anonymous traffic — always intersect website visitors with the company list so only known accounts see ads.
- Using lookalike audiences — they dilute ABM precision. Use sparingly or not at all.
- Prospecting on Meta — Meta is for retargeting in ABM, not net-new.
- Leaning on Google remarketing — B2B match rates are low; use it as a supplement to LinkedIn, not the core.
- Not excluding converted leads — wasted spend and an annoyed customer.
- Leaving accounts in the Hot segment forever — no response by Day 21 means move to Warm and change the angle.
