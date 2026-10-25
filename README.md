# GTM Flywheel

### 28 Claude Code Skills for GTM Teams

> **A free, open-source collection of structured Claude Code skills for GTM teams.**

Read it as a playbook on the web: [GTM Flywheel](https://martechs.io/playbooks/gtm-flywheel). The full library of 56 installable [GTM skills for Claude Code](https://martechs.io/gtm-skills) lives on the same site.

GTM Flywheel helps GTM teams apply repeatable frameworks to cold email, account qualification, campaign analysis, and sales intelligence.

Each skill is a structured operational framework that Claude Code can read and apply. They are more than standalone prompts: each includes scoring models, decision trees, templates, and quality benchmarks designed to make GTM work more consistent.

---

## What's Inside

### 7 Pillars. 28 Skills.

| # | Pillar | Skills | What You Get |
|---|--------|--------|-------------|
| 1 | **Cold Email** | Copy Frameworks, Sequence Architecture, Personalization Engine, B2B Cold Email Copywriting | SPARK framework with 6 proven copy archetypes. Multi-step sequences with variant strategies. Signal-based personalization at scale. |
| 2 | **ICP Research** | ICP Matrix Builder, Persona Development, Account Qualification, Buying Committee Mapper, List Quality Scorecard | 5-dimension scoring matrices. 8-component buyer personas built from data, not assumptions. The FITS qualification framework. |
| 3 | **Signal Scoring** | Intent Signals, Trigger Mapping, Lead Prioritization, Champion Move Detection, Closed-Won Replication | 4-category signal taxonomy with scoring formulas. 12 business event triggers mapped to outreach angles. Weighted priority queues. |
| 4 | **Campaign Analytics** | Performance Analysis, Winning Copy Extraction, Campaign Benchmarking, Positive Reply Scoring, Experiment Design, Deliverability Test | 6-layer diagnostic stack. Pattern extraction from your top campaigns. 3-layer benchmarking (industry, portfolio, segment). |
| 5 | **Sales Intelligence** | Transcript Analysis, Objection Mining, Deal Patterns | 7-layer transcript extraction. 6-category objection taxonomy with AER response framework. Win/loss pattern analysis. |
| 6 | **ABM** | ABM Target Accounts, ABM Retargeting, ABM Measurement | Account sizing, lookalikes and A/B/C/D tiering. Engagement-tiered retargeting with frequency rules. Stage-based account metrics, attribution and ABM ROI. |
| 7 | **Infrastructure** | Email Gateway Detection, Email Waterfall | MX-based detection of Proofpoint, Mimecast, Barracuda, Google and Microsoft. Multi-provider email finding and verification. |

**Total: ~4,200 lines of frameworks, templates, and actionable methodology.**

---

## The Flywheel

These skills aren't 28 independent documents. They're an interconnected system where each skill feeds and strengthens the others:

```
ICP Research     →  defines WHO to target
Signal Scoring   →  determines WHEN to reach out
Cold Email       →  crafts WHAT to say
Campaign Analytics → reveals what's WORKING
Sales Intelligence → feeds insights BACK into everything
```

```
            ┌─────────────────────────────┐
            │                             │
            ▼                             │
     ICP Research ──► Signal Scoring ──► Cold Email
            ▲                                 │
            │          COMPOUNDING            │
            │          FLYWHEEL               ▼
     Sales Intelligence ◄──────────── Campaign Analytics
```

Every campaign you run makes every future campaign better — but only if you have the systems to capture and apply the learnings. That's what these skills do.

### The loop actually closes

`flywheel/` makes the diagram real. It pulls outcomes from Smartlead, Instantly, lemlist or HeyReach (read-only, or from a CSV), labels each email with the taxonomy in these skills, ranks what wins with proper confidence intervals, measures which buying signals actually lift positive replies, and opens a pull request that proposes updates to the skills and signal weights with the evidence attached. You merge or reject. Nothing changes without a human. See [flywheel/README.md](flywheel/README.md) or run `/flywheel-learn`.

---

## How It Works

Each skill follows a consistent `SKILL.md` format:

```
SKILL.md
├── Metadata        →  Name + description (YAML frontmatter)
├── When to Use     →  Activation criteria
├── Framework       →  The full operational playbook
├── Templates       →  Fill-in-the-blank deliverable docs
└── Tips            →  Hard-won insights from real campaigns
```

Claude Code reads these files and applies the frameworks to YOUR data. You bring the context — your ICP, your campaign metrics, your call transcripts — and the skills provide the methodology.

**Example:**
```
You: "Read the ICP Matrix Builder skill. I sell marketing analytics
     to VP Marketing at Series B SaaS companies. Help me build
     an ICP matrix."

Claude Code: [Reads SKILL.md] → Walks you through the 6-step process
             → Produces a scored, tiered ICP matrix using YOUR inputs
```

---

## Quick Start

### 1. Clone this repo
```bash
git clone https://github.com/automatewithuday/gtm-flywheel.git
cd gtm-flywheel
```

### 2. Start Claude Code in the repo
```bash
claude
```
Claude Code auto-reads the `CLAUDE.md` and discovers all 28 skills.

### 3. Pick a skill and go
```
"Read the Copy Frameworks skill and help me write a cold email
campaign for [your persona] at [your target company type]."
```

That's it. No setup. No dependencies. No APIs to configure.

**Optional, to make the skills learn from your results:** `cd flywheel && cp .env.example .env`, add a sequencer API key, then `/flywheel-learn`.

**For a detailed walkthrough with 5 starter tasks:** [GETTING-STARTED.md](GETTING-STARTED.md)


**For the full system architecture and data flows:** [architecture/system-overview.md](architecture/system-overview.md)

---

## Repo Structure

```
gtm-flywheel/
│
├── README.md                              ← You are here
├── flywheel/                              ← Self-learning loop: read-only adapters, learner, PR proposer
├── .claude/skills/flywheel-learn/         ← /flywheel-learn command
├── CLAUDE.md                              ← Workspace config (Claude Code auto-reads this)
├── GETTING-STARTED.md                     ← Setup guide + 5 starter tasks
│
├── architecture/
│   └── system-overview.md                 ← Full system map + data flows
│
├── abm/
│   ├── abm-target-accounts/
│   │   └── SKILL.md                       ← Account sizing, lookalikes, scoring, A/B/C/D tiers
│   ├── abm-retargeting/
│   │   └── SKILL.md                       ← Audience tiers, frequency caps, multi-channel plays
│   └── abm-measurement/
│       └── SKILL.md                       ← Metrics by stage, attribution models, ABM ROI
│
├── infrastructure/
│   ├── email-gateway-detection/
│   │   └── SKILL.md                       ← MX lookup, SEG/provider routing rules
│   └── email-waterfall/
│       └── SKILL.md                       ← Multi-provider email waterfall and verification
│
├── cold-email/
│   ├── copy-frameworks/
│   │   └── SKILL.md                       ← SPARK framework, 6 copy archetypes, subject formulas
│   ├── sequence-architecture/
│   │   └── SKILL.md                       ← 4-step sequences, multi-channel, timing, variants
│   ├── personalization-engine/
│   │   └── SKILL.md                       ← 6-level hierarchy, signal categories, variable architecture
│   └── b2b-cold-email-copywriting/
│       └── SKILL.md                       ← Big-3 diagnosis, 5 email frameworks, openers, CTAs, follow-ups
│
├── icp-research/
│   ├── icp-matrix-builder/
│   │   └── SKILL.md                       ← 5-dimension scoring, tiering, 6-step build process
│   ├── persona-development/
│   │   └── SKILL.md                       ← 8-component personas, pain hierarchy, language mining
│   ├── account-qualification/
│   │   └── SKILL.md                       ← FITS framework, 3-level qualification, batch workflows
│   ├── buying-committee-mapper/
│   │   └── SKILL.md                       ← Four committee slots, title matrix by headcount band, coverage report
│   └── list-quality-scorecard/
│       └── SKILL.md                       ← 8 list-quality dimensions, letter grade mapping
│
├── signal-scoring/
│   ├── intent-signals/
│   │   └── SKILL.md                       ← 4-category taxonomy, scoring formula, stacking rules
│   ├── trigger-mapping/
│   │   └── SKILL.md                       ← 12 business event triggers, prioritization matrix
│   ├── lead-prioritization/
│   │   └── SKILL.md                       ← Weighted scoring model, priority queues, dynamic re-scoring
│   ├── champion-move-detection/
│   │   └── SKILL.md                       ← Champion watchlist, monthly move detection, churn flags
│   └── closed-won-replication-play/
│       └── SKILL.md                       ← Win profile, lookalike search, drafted outreach for review
│
├── campaign-analytics/
│   ├── performance-analysis/
│   │   └── SKILL.md                       ← 6-layer metrics stack, diagnostic trees, scale/optimize/kill
│   ├── winning-copy-extraction/
│   │   └── SKILL.md                       ← Copy anatomy, pattern recognition, playbook builder
│   ├── campaign-benchmarking/
│   │   └── SKILL.md                       ← 3-layer benchmarks, scorecards, cross-portfolio analysis
│   ├── positive-reply-scoring/
│   │   └── SKILL.md                       ← Reply classification schema, positive reply rate vs 1% bar
│   ├── experiment-design/
│   │   └── SKILL.md                       ← List/copy/combined experiments, sample size, success criteria
│   └── deliverability-test/
│       └── SKILL.md                       ← Reply and bounce rates by inbox type
│
└── sales-intelligence/
    ├── transcript-analysis/
    │   └── SKILL.md                       ← 7-extraction layers, language banking, operationalization
    ├── objection-mining/
    │   └── SKILL.md                       ← 6-category taxonomy, AER framework, pre-handling
    └── deal-patterns/
        └── SKILL.md                       ← 12 deal variables, 5 analyses, ideal deal profiling
```

---

## The Skills at a Glance

### Cold Email
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Copy Frameworks** | SPARK formula, 6 archetypes (Observation, Problem/Solution, Referral Ceiling, Creative Ideas, Benchmark, Whole Offer), subject line formulas, QA checklist | Writing cold emails that earn replies |
| **Sequence Architecture** | 4-step core sequence, 8-step multi-channel, variant strategy, timing optimization, escalation logic, campaign naming | Building campaigns that convert across multiple touches |
| **Personalization Engine** | 6-level personalization hierarchy, 6 signal categories, personalization formula (Observation + Implication + Bridge), variable architecture, bucket strategy | Personalizing at scale without manual research per lead |
| **B2B Cold Email Copywriting** | Big-3 diagnosis (list, offer, copy), deliverability prerequisites, 5 email frameworks, personalization ladder, interest-based CTAs, follow-up sequence, spintax | Writing cold email that lands in the primary inbox and earns replies |

### ICP Research
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **ICP Matrix Builder** | 5-dimension scoring (firmographic, technographic, intent, persona, engagement), tiering framework, 6-step build process | Defining exactly who to target with data-backed criteria |
| **Persona Development** | 8-component blueprint, pain hierarchy, motivation map, language profile, multi-persona account strategy | Understanding buyers deeply enough to write copy that resonates |
| **Account Qualification** | FITS framework (Firmographic, Intent, Technographic, Structural), 3-level qualification stack, batch processing workflow | Scoring and filtering accounts before spending outreach resources |
| **Buying Committee Mapper** | Four committee slots, title matrix by headcount band, dry-run approval loop, per-slot enrichment, coverage report | Multithreading accounts with the right people per role |
| **List Quality Scorecard** | 8 dimensions (verification, duplicates, title relevance, bad titles, catch-all density, ICP fit, name quality), letter grade mapping | Grading an enriched list before upload |

### Signal Scoring
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Intent Signals** | 4-category taxonomy (first-party, third-party, public, social), signal scoring formula, signal stacking rules | Detecting which accounts are in-market right now |
| **Trigger Mapping** | 12 core business event triggers, urgency windows, signal-to-message mapping, trigger campaign architecture | Knowing exactly when to reach out and what to say |
| **Lead Prioritization** | 3-dimension weighted scoring (fit 30% + intent 45% + engagement 25%), priority tiers P1-P5, daily queue system, signal decay | Ranking leads by conversion probability so your team works the best ones first |
| **Champion Move Detection** | Champion watchlist, monthly LinkedIn move check, confirmed-move routing to scoring, churn-risk flag, monthly digest | Catching customer champions who changed jobs |
| **Closed-Won Replication** | Win profile extraction, lookalike search profile, per-lookalike research, drafted outreach, CRM review task | Turning every Closed Won deal into new pipeline |

### Campaign Analytics
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Performance Analysis** | 6-layer metrics stack (deliverability → engagement → response → quality → conversion → revenue), diagnostic decision trees | Knowing if a campaign is good, broken, or needs optimization |
| **Winning Copy Extraction** | Copy anatomy framework, pattern recognition pipeline, copy playbook builder, decay detection | Extracting reusable patterns from your best-performing emails |
| **Campaign Benchmarking** | 3-layer benchmarks (industry, internal, segment), campaign scorecards, time series analysis | Putting performance in context — is 4% reply rate good or bad for THIS segment? |
| **Positive Reply Scoring** | Reply classification schema, positive reply rate vs 1% bar, action-item flags | Judging whether a campaign is really working |
| **Experiment Design** | List-only / copy-only / combined experiments, 7-step framework, minimum sample size, day-21 measurement, learning weights | Testing one variable at a time so you learn something |
| **Deliverability Test** | Reply, bounce and positive-reply rates by inbox type (SMTP, Gmail, Outlook) | Deciding which inbox provider to buy more of |

### Sales Intelligence
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Transcript Analysis** | 7-extraction layers (pain, triggers, language, objections, competitive, decision process, win/loss) | Turning recorded sales calls into actionable outbound intelligence |
| **Objection Mining** | 6-category taxonomy, AER response framework (Acknowledge → Explore → Redirect), pre-handling in outreach | Building an objection playbook from real prospect pushback |
| **Deal Patterns** | 12 deal variables, 5 pattern analyses (wins, losses, speed, size, ideal deal), feedback to outbound | Understanding what predicts revenue so you can target and sell more of it |

### ABM
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **ABM Target Accounts** | Account-count sizing, lookalikes from best customers, simple scoring, A/B/C/D tiers, CRM stage lists and progression automation | Building and tiering a target account list |
| **ABM Retargeting** | Engagement-based audience tiers, frequency management, pricing-page trigger play, LinkedIn/Meta/Google setup, CRM-to-ad data flow | Running retargeting on target accounts without ad fatigue |
| **ABM Measurement** | Metrics by stage (coverage to revenue), weighted multi-touch / W-shaped / hybrid attribution, ABM ROI and pipeline ROI formulas | Reporting ABM on account-level metrics instead of MQLs |

### Infrastructure
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Email Gateway Detection** | MX-record waterfall, SEG and mailbox provider routing rules, output schema, cost estimate | Splitting campaigns by gateway and fixing enterprise inbox placement |
| **Email Waterfall** | Multi-provider email finding, verification before upload, setup and common mistakes | Filling missing or unverified work emails before sending |

---

## Contributing

Found a pattern that works? A framework that's missing? Open a PR. The best GTM knowledge is built in the open.

---

## License

MIT. Use these however you want. Build on them. Ship them.

Four skills (positive-reply-scoring, experiment-design, deliverability-test, list-quality-scorecard) derive from GrowthEngineX/coldoutboundskills under MIT; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

## Maintainer

Maintained by [Uday Kang](https://www.instagram.com/automatewithuday/) (`@automatewithuday`).
