---
name: abm-measurement
description: Use when measuring, reporting on, or auditing an account-based marketing (ABM) program — choosing account-level metrics by funnel stage (coverage, awareness/reach, engagement, pipeline, revenue), picking an attribution model (weighted multi-touch, W-shaped, hybrid), calculating ABM ROI, pipeline ROI, cost per engaged account, cost per pipeline account, pipeline velocity, ABM CAC or LTV:CAC, comparing results to benchmarks, or checking measurement maturity before launch. Also use when someone reports ABM results with lead or MQL metrics — that is the wrong model and this skill corrects it.
license: MIT
metadata:
  author: automatewithuday
  source: martechs.io
  version: "1.0"
---

# How to measure ABM success

Metrics by stage, attribution models, ROI formulas, and benchmarks that actually work.

ABM measurement is fundamentally different from demand gen measurement. You're tracking accounts through a journey, not leads through a funnel.

**The core shift:**

- Demand gen asks: "How many leads did we generate?"
- ABM asks: "How many target accounts progressed through buying stages?"

If you're measuring ABM with lead metrics, you're doing it wrong.

## How to apply this skill

When asked to measure, report on, or audit an ABM program:

1. Gather inputs (ask for what's missing; work with what's available):
   - Total target accounts, accounts matched in LinkedIn + CRM, contacts per persona
   - Per-account impressions, clicks, engagements, website visits, content downloads
   - Engaged accounts, accounts in pipeline, pipeline value, closed-won revenue
   - Total ABM spend (ads + tools + team), number of opportunities, win rate, average deal size, sales cycle length
   - Which measurement maturity stage they are at (see below) — it bounds what can honestly be reported
2. Compute stage metrics first (coverage → awareness → engagement → pipeline), then ROI and efficiency metrics. Use the formulas exactly as written below.
3. Report each number next to its benchmark, name the weakest stage, and give one recommendation. Use W-shaped attribution for executive views and linear for optimization views.
4. If the program is under 90 days old, report leading indicators only and say so — pipeline lags 6–8 weeks.

Do not translate ABM results into lead or MQL counts. Every metric here is at the account level.

## Metrics by stage

### Coverage (target list)

```
Coverage Rate = (Accounts matched in LinkedIn + CRM) / Total Target Accounts
Persona Coverage = Contacts found per account across all target personas
```

### Awareness (reach)

An account is aware when it has 50+ impressions.

```
Account Reach Rate = accounts_with_50_plus_impressions / total_target_accounts

Example:
850 / 1500 = 56.7%
```

### Engagement

An account is engaged when it has 5+ clicks OR 10+ engagements.

```
Account Engagement Rate = engaged_accounts / aware_accounts

Example:
272 / 850 = 32%
```

Benchmark — Awareness to Engagement: 30% of aware accounts become engaged.

### Pipeline

```
Pipeline Influenced = sum of opportunity value for every opportunity whose account was touched by ABM
Influence Rate = Pipeline Influenced / Total Pipeline
```

Benchmark — Engagement to Pipeline: 20% (accounts that book demo/trial).

### Revenue

Closed-won revenue from ABM accounts. Feeds ABM ROI, ABM CAC, and LTV:CAC below.

## Attribution models

### Account-level weighted multi-touch

How it works:

1. Track all touchpoints at the account level (not lead level)
2. Credit is distributed across all marketing touches before opportunity creation
3. Sales activities tracked separately but contribute to velocity metrics

Credit distribution example (weighted multi-touch):

```
Account: Acme Corp
Touchpoints before opportunity:
- LinkedIn ad impression (25 touches) → 10% credit
- LinkedIn ad click (5 touches) → 20% credit
- Website visit (3 touches) → 15% credit
- Content download (1 touch) → 25% credit
- BDR email reply (1 touch) → 15% credit
- Demo booked → 15% credit

Pipeline value: $100,000
Marketing influence: $85,000 (all touches except demo)
```

### W-shaped

Best for ABM programs with clear stage gates.

When to use: B2B sales cycles >60 days with multiple decision-makers.

### Hybrid (multiple models in parallel)

Combines models for different questions.

Implementation:

1. Track all touchpoints with timestamps
2. Run multiple attribution models in parallel
3. Report different views for different stakeholders
4. Use W-shaped for executive reporting, linear for optimization

## ROI and efficiency formulas

### ABM ROI

```
ABM ROI = (Revenue from ABM Accounts - Total ABM Cost) / Total ABM Cost x 100

Example:
Revenue: $500,000
Total Cost: $150,000 (ads + tools + team)
ROI = ($500,000 - $150,000) / $150,000 x 100 = 233%
```

### Pipeline ROI

```
Pipeline ROI = Pipeline Generated / Total ABM Spend

Example (illustrative):
Pipeline: $600,000
Spend: $50,000
Pipeline ROI = $600,000 / $50,000 = $12 per $1 spent
```

Benchmark: $10+ pipeline per $1 spent = healthy ABM program.

### Cost per Engaged Account

```
Cost per Engaged Account = Total ABM Spend / Engaged Accounts

Example:
Spend: $50,000
Engaged Accounts: 250
Cost per Engaged Account = $200
```

Use this to compare efficiency across campaigns, segments, and personas.

### Cost per Pipeline Account

```
Cost per Pipeline Account = Total ABM Spend / Accounts in Pipeline

Example:
Spend: $50,000
Accounts in Pipeline: 45
Cost per Pipeline Account = $1,111
```

### Pipeline Velocity

```
Pipeline Velocity = (# Opportunities x Win Rate x Avg Deal Size) / Sales Cycle Length

Example:
50 opps x 40% x $50,000 / 90 days = $11,111 per day
```

Track this over time to see if ABM is accelerating your pipeline.

### ABM CAC

```
ABM CAC = Total ABM Cost / New Customers from ABM

Example:
Total Cost: $150,000
New Customers: 12
CAC = $12,500
```

Compare to: demand gen CAC, outbound CAC, overall blended CAC.

### LTV:CAC

```
LTV:CAC = Customer Lifetime Value / Customer Acquisition Cost

Target: >3:1 for healthy economics
ABM programs often achieve 5:1+ due to better-fit customers
```

### Efficiency Score (composite)

```
Efficiency Score = (pipeline_per_dollar x 0.4) + (engagement_rate x 100 x 0.3) + (win_rate x 100 x 0.3)

Example:
(12.50 x 0.4) + (32 x 0.3) + (45 x 0.3) = 28.1
```

## Measurement maturity model

Before launching ABM, document which stage you are at. It determines which of the metrics above you can honestly report.

### Stage 1 — Ad platform only

What you can measure:

- Ad spend and basic metrics (impressions, clicks)
- Account match rates
- Basic engagement counts

Gaps:

- No account-level attribution
- No pipeline connection
- Manual reporting

### Stage 2 — Account-level engagement

What you can measure:

- Account-level engagement (via Fibbler)
- Stage progression
- Pipeline influenced by ABM
- Basic attribution

Gaps:

- Limited multi-touch attribution
- Manual ROI calculations

### Stage 3 — Integrated and automated

What you can measure:

- Full multi-touch attribution
- Automated ROI reporting
- Predictive account scoring
- Cross-channel attribution

Capabilities:

- Real-time dashboards
- Automated alerts for hot accounts
- Integration with sales workflows

### Stage 4 — Predictive and incrementality

What you can measure:

- Incrementality testing
- Account-level A/B testing
- Predictive pipeline modeling
- Full-funnel optimization

Capabilities:

- Machine learning for account scoring
- Automated budget reallocation
- Closed-loop revenue attribution

## Leading indicators

Focus on leading indicators (the coverage, awareness, and engagement metrics above) in the first 90 days. They predict future pipeline 6–8 weeks out.

## Quick reference

| Metric | Formula | Benchmark / target |
|---|---|---|
| Coverage Rate | matched accounts / target accounts | — |
| Account Reach Rate | accounts with 50+ impressions / target accounts | — |
| Awareness → Engagement | engaged accounts / aware accounts | 30% |
| Engagement → Pipeline | pipeline accounts / engaged accounts | 20% |
| Influence Rate | ABM-influenced pipeline / total pipeline | — |
| ABM ROI | (revenue − cost) / cost × 100 | — |
| Pipeline ROI | pipeline / spend | $10+ per $1 |
| Cost per Engaged Account | spend / engaged accounts | — |
| Cost per Pipeline Account | spend / pipeline accounts | — |
| Pipeline Velocity | (opps × win rate × avg deal) / cycle days | trend up over time |
| ABM CAC | cost / new customers | compare vs demand gen, outbound, blended |
| LTV:CAC | LTV / CAC | >3:1 (ABM often 5:1+) |
| Efficiency Score | 0.4 × pipeline/$ + 0.3 × engagement% + 0.3 × win% | — |

## Common mistakes

- Reporting ABM with lead or MQL metrics — count accounts progressing through stages instead.
- Tracking touchpoints at the lead level — roll every touch up to the account.
- Showing one attribution view to everyone — execs get W-shaped, optimizers get linear.
- Claiming pipeline ROI at Stage 1 maturity — without account-level attribution and a pipeline connection you can only report reach and engagement.
- Judging a program on pipeline in its first 90 days — use leading indicators; pipeline lags 6–8 weeks.
