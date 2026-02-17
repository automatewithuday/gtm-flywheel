# GTM Flywheel

### 15 AI-Powered Skills That Turn Claude Code Into Your GTM Co-Pilot

> **The same frameworks used by a $7M ARR agency managing 70+ client campaigns. Now open source.**

Most GTM teams waste 15+ hours a week on work that should be automated — writing cold emails from scratch, manually scoring leads, guessing which campaigns to scale, and reporting on stale data. The GTM Blueprint changes that.

Each skill is a battle-tested operational framework that Claude Code can read, understand, and execute. They're not prompts. They're **systems** — complete with scoring models, decision trees, templates, and quality benchmarks that produce consistent, deployable results.

---

## What's Inside

### 5 Pillars. 15 Skills.

| # | Pillar | Skills | What You Get |
|---|--------|--------|-------------|
| 1 | **Cold Email** | Copy Frameworks, Sequence Architecture, Personalization Engine | SPARK framework with 6 proven copy archetypes. Multi-step sequences with variant strategies. Signal-based personalization at scale. |
| 2 | **ICP Research** | ICP Matrix Builder, Persona Development, Account Qualification | 5-dimension scoring matrices. 8-component buyer personas built from data, not assumptions. The FITS qualification framework. |
| 3 | **Signal Scoring** | Intent Signals, Trigger Mapping, Lead Prioritization | 4-category signal taxonomy with scoring formulas. 12 business event triggers mapped to outreach angles. Weighted priority queues. |
| 4 | **Campaign Analytics** | Performance Analysis, Winning Copy Extraction, Campaign Benchmarking | 6-layer diagnostic stack. Pattern extraction from your top campaigns. 3-layer benchmarking (industry, portfolio, segment). |
| 5 | **Sales Intelligence** | Transcript Analysis, Objection Mining, Deal Patterns | 7-layer transcript extraction. 6-category objection taxonomy with AER response framework. Win/loss pattern analysis. |

**Total: ~4,200 lines of frameworks, templates, and actionable methodology.**

---

## The Flywheel

These skills aren't 15 independent documents. They're an interconnected system where each skill feeds and strengthens the others:

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
git clone https://github.com/kenny589/gtm-blueprint.git
cd gtm-blueprint
```

### 2. Start Claude Code in the repo
```bash
claude
```
Claude Code auto-reads the `CLAUDE.md` and discovers all 15 skills.

### 3. Pick a skill and go
```
"Read the Copy Frameworks skill and help me write a cold email
campaign for [your persona] at [your target company type]."
```

That's it. No setup. No dependencies. No APIs to configure.

**For a detailed walkthrough with 5 starter tasks:** [GETTING-STARTED.md](GETTING-STARTED.md)

**For how Claude Code and GTM work together:** [claude-code-and-gtm.md](claude-code-and-gtm.md)

**For the full system architecture and data flows:** [architecture/system-overview.md](architecture/system-overview.md)

---

## Repo Structure

```
gtm-blueprint/
│
├── README.md                              ← You are here
├── CLAUDE.md                              ← Workspace config (Claude Code auto-reads this)
├── GETTING-STARTED.md                     ← Setup guide + 5 starter tasks
├── claude-code-and-gtm.md                 ← Why AI agents change GTM forever
│
├── architecture/
│   └── system-overview.md                 ← Full system map + data flows
│
├── cold-email/
│   ├── copy-frameworks/
│   │   └── SKILL.md                       ← SPARK framework, 6 copy archetypes, subject formulas
│   ├── sequence-architecture/
│   │   └── SKILL.md                       ← 4-step sequences, multi-channel, timing, variants
│   └── personalization-engine/
│       └── SKILL.md                       ← 6-level hierarchy, signal categories, variable architecture
│
├── icp-research/
│   ├── icp-matrix-builder/
│   │   └── SKILL.md                       ← 5-dimension scoring, tiering, 6-step build process
│   ├── persona-development/
│   │   └── SKILL.md                       ← 8-component personas, pain hierarchy, language mining
│   └── account-qualification/
│       └── SKILL.md                       ← FITS framework, 3-level qualification, batch workflows
│
├── signal-scoring/
│   ├── intent-signals/
│   │   └── SKILL.md                       ← 4-category taxonomy, scoring formula, stacking rules
│   ├── trigger-mapping/
│   │   └── SKILL.md                       ← 12 business event triggers, prioritization matrix
│   └── lead-prioritization/
│       └── SKILL.md                       ← Weighted scoring model, priority queues, dynamic re-scoring
│
├── campaign-analytics/
│   ├── performance-analysis/
│   │   └── SKILL.md                       ← 6-layer metrics stack, diagnostic trees, scale/optimize/kill
│   ├── winning-copy-extraction/
│   │   └── SKILL.md                       ← Copy anatomy, pattern recognition, playbook builder
│   └── campaign-benchmarking/
│       └── SKILL.md                       ← 3-layer benchmarks, scorecards, cross-portfolio analysis
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

## Who This Is For

| You Are | What This Gives You |
|---------|-------------------|
| **CMO / VP Sales** | A structured system for AI-assisted outbound that your team can deploy this week |
| **Agency Operator** | Repeatable frameworks that work across every client without reinventing the wheel |
| **RevOps / Sales Ops** | Scoring models, qualification frameworks, and benchmarking systems you can plug into your stack |
| **SDR Team Lead** | Training material and operational playbooks backed by real performance data |
| **Solo Founder** | Enterprise-grade GTM methodology without needing an enterprise-grade team |

---

## What Makes This Different

| | ChatGPT Prompts | GTM Blueprint Skills |
|---|---|---|
| **Structure** | Freeform text | YAML metadata + consistent sections |
| **Depth** | Surface-level suggestions | Scoring models, decision trees, diagnostic frameworks |
| **Reusability** | Copy-paste, tweak each time | Read once, apply to any context |
| **Consistency** | Different output every run | Same methodology, adapted to your inputs |
| **Composability** | Standalone | 15 skills that reference and build on each other |
| **Maintainability** | Scattered across chat history | Versioned in a repo, updated over time |

---

## The Skills at a Glance

### Cold Email
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Copy Frameworks** | SPARK formula, 6 archetypes (Observation, Problem/Solution, Referral Ceiling, Creative Ideas, Benchmark, Whole Offer), subject line formulas, QA checklist | Writing cold emails that earn replies |
| **Sequence Architecture** | 4-step core sequence, 8-step multi-channel, variant strategy, timing optimization, escalation logic, campaign naming | Building campaigns that convert across multiple touches |
| **Personalization Engine** | 6-level personalization hierarchy, 6 signal categories, personalization formula (Observation + Implication + Bridge), variable architecture, bucket strategy | Personalizing at scale without manual research per lead |

### ICP Research
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **ICP Matrix Builder** | 5-dimension scoring (firmographic, technographic, intent, persona, engagement), tiering framework, 6-step build process | Defining exactly who to target with data-backed criteria |
| **Persona Development** | 8-component blueprint, pain hierarchy, motivation map, language profile, multi-persona account strategy | Understanding buyers deeply enough to write copy that resonates |
| **Account Qualification** | FITS framework (Firmographic, Intent, Technographic, Structural), 3-level qualification stack, batch processing workflow | Scoring and filtering accounts before spending outreach resources |

### Signal Scoring
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Intent Signals** | 4-category taxonomy (first-party, third-party, public, social), signal scoring formula, signal stacking rules | Detecting which accounts are in-market right now |
| **Trigger Mapping** | 12 core business event triggers, urgency windows, signal-to-message mapping, trigger campaign architecture | Knowing exactly when to reach out and what to say |
| **Lead Prioritization** | 3-dimension weighted scoring (fit 30% + intent 45% + engagement 25%), priority tiers P1-P5, daily queue system, signal decay | Ranking leads by conversion probability so your team works the best ones first |

### Campaign Analytics
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Performance Analysis** | 6-layer metrics stack (deliverability → engagement → response → quality → conversion → revenue), diagnostic decision trees | Knowing if a campaign is good, broken, or needs optimization |
| **Winning Copy Extraction** | Copy anatomy framework, pattern recognition pipeline, copy playbook builder, decay detection | Extracting reusable patterns from your best-performing emails |
| **Campaign Benchmarking** | 3-layer benchmarks (industry, internal, segment), campaign scorecards, time series analysis | Putting performance in context — is 4% reply rate good or bad for THIS segment? |

### Sales Intelligence
| Skill | Key Frameworks | Best For |
|-------|---------------|----------|
| **Transcript Analysis** | 7-extraction layers (pain, triggers, language, objections, competitive, decision process, win/loss) | Turning recorded sales calls into actionable outbound intelligence |
| **Objection Mining** | 6-category taxonomy, AER response framework (Acknowledge → Explore → Redirect), pre-handling in outreach | Building an objection playbook from real prospect pushback |
| **Deal Patterns** | 12 deal variables, 5 pattern analyses (wins, losses, speed, size, ideal deal), feedback to outbound | Understanding what predicts revenue so you can target and sell more of it |

---

## Contributing

Found a pattern that works? A framework that's missing? Open a PR. The best GTM knowledge is built in the open.

---

## License

MIT — Use these however you want. Build on them. Adapt them. Ship them.

---

**Built by [ColdIQ](https://coldiq.com)** — the GTM agency that runs on AI agents.

*If you want help implementing these frameworks for your business — or you want the full system with automated dashboards, Slack bots, and AI-powered onboarding — [reach out](https://www.linkedin.com/in/kenny-damian-90aba221a/).*
