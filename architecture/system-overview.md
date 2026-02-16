# System Architecture: How the 15 Skills Connect

## Overview

The GTM Blueprint is not 15 independent skills — it's an interconnected system where each skill feeds into and strengthens the others. This document maps the connections, data flows, and recommended execution sequences.

---

## The System Map

```
┌─────────────────────────────────────────────────────────────────┐
│                        GTM BLUEPRINT                            │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ ICP RESEARCH │    │   SIGNAL    │    │  COLD EMAIL │        │
│  │             │    │  SCORING    │    │             │        │
│  │ • ICP Matrix├───►│ • Intent    ├───►│ • Copy      │        │
│  │ • Personas  │    │   Signals   │    │   Frameworks│        │
│  │ • Account   │    │ • Trigger   │    │ • Sequence  │        │
│  │   Qualific. │    │   Mapping   │    │   Architect.│        │
│  │             │    │ • Lead      │    │ • Personal. │        │
│  │             │    │   Priority  │    │   Engine    │        │
│  └──────▲──────┘    └─────────────┘    └──────┬──────┘        │
│         │                                      │               │
│         │         FEEDBACK LOOP                │               │
│         │                                      ▼               │
│  ┌──────┴──────┐                      ┌─────────────┐        │
│  │   SALES     │◄─────────────────────│  CAMPAIGN   │        │
│  │ INTELLIGENCE│                      │  ANALYTICS  │        │
│  │             │                      │             │        │
│  │ • Transcript│    ┌────────────────►│ • Perform.  │        │
│  │   Analysis  │    │                 │   Analysis  │        │
│  │ • Objection │    │                 │ • Winning   │        │
│  │   Mining    ├────┘                 │   Copy Extr.│        │
│  │ • Deal      │                      │ • Campaign  │        │
│  │   Patterns  │                      │   Benchmark.│        │
│  └─────────────┘                      └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Between Skills

### Forward Flow (Building → Launching)

```
Step 1: RESEARCH
ICP Matrix Builder
    → Defines target company criteria (size, industry, stage, tech)
    → Outputs: Tiered account list with scoring model
        ↓
Persona Development
    → Defines target people within qualified companies
    → Outputs: Buyer personas with pain maps and language banks
        ↓
Account Qualification
    → Scores and filters accounts against ICP + persona criteria
    → Outputs: Qualified, tiered account list ready for outreach

Step 2: TARGETING
Intent Signals
    → Monitors qualified accounts for buying signals
    → Outputs: Signal-enriched accounts with intent scores
        ↓
Trigger Mapping
    → Maps detected signals to outreach triggers and timing
    → Outputs: Trigger-action playbook
        ↓
Lead Prioritization
    → Combines fit + intent + engagement into priority scores
    → Outputs: Ranked lead queue (P1-P5)

Step 3: EXECUTION
Copy Frameworks
    → Applies archetype + persona language to write emails
    → Outputs: Email copy (subject + body + CTA, multiple variants)
        ↓
Sequence Architecture
    → Structures copy into multi-step cadences with timing
    → Outputs: Complete campaign sequence with variant strategy
        ↓
Personalization Engine
    → Layers signal-based personalization onto templates
    → Outputs: Personalized email variables per lead or bucket
```

### Feedback Flow (Analyzing → Improving)

```
Step 4: MEASUREMENT
Performance Analysis
    → Diagnoses campaign results across 6 metric layers
    → Outputs: Campaign scorecard, diagnostic report
        ↓
Winning Copy Extraction
    → Identifies patterns in top-performing copy
    → Outputs: Copy playbook, winning patterns
        ↓
Campaign Benchmarking
    → Contextualizes results against baselines
    → Outputs: Benchmark report, target adjustments

Step 5: INTELLIGENCE
Transcript Analysis
    → Mines sales calls for language, triggers, and objections
    → Outputs: Language bank, trigger list, objection catalog
        ↓
Objection Mining
    → Categorizes and builds responses for common pushback
    → Outputs: Objection playbook, pre-handling copy
        ↓
Deal Patterns
    → Analyzes win/loss data for predictive patterns
    → Outputs: Ideal deal profile, targeting adjustments

Step 6: FEEDBACK (Closes the Loop)
Deal Patterns → ICP Matrix Builder (update scoring criteria)
Transcript Analysis → Persona Development (update language and pain)
Winning Copy Extraction → Copy Frameworks (update winning patterns)
Objection Mining → Sequence Architecture (pre-handle in steps 2-3)
Campaign Benchmarking → Lead Prioritization (adjust tier thresholds)
```

---

## Cross-Skill Dependencies

### Which skills feed which:

| Source Skill | Feeds Into | What It Provides |
|-------------|-----------|-----------------|
| ICP Matrix Builder | Account Qualification | Scoring criteria and tier thresholds |
| ICP Matrix Builder | Lead Prioritization | Fit score components |
| Persona Development | Copy Frameworks | Pain language, motivation hooks |
| Persona Development | Personalization Engine | Persona-specific variable strategies |
| Account Qualification | Lead Prioritization | Qualified account pool |
| Intent Signals | Trigger Mapping | Raw signals to map to actions |
| Intent Signals | Lead Prioritization | Intent score components |
| Trigger Mapping | Sequence Architecture | Trigger-specific campaign designs |
| Trigger Mapping | Personalization Engine | Signal-to-message mappings |
| Lead Prioritization | Sequence Architecture | Tier-based sequence routing |
| Copy Frameworks | Sequence Architecture | Per-step copy following archetypes |
| Copy Frameworks | Personalization Engine | Templates requiring personalization |
| Performance Analysis | Winning Copy Extraction | Identified top campaigns to analyze |
| Performance Analysis | Campaign Benchmarking | Raw metrics for benchmarking |
| Winning Copy Extraction | Copy Frameworks | Updated winning patterns |
| Campaign Benchmarking | Lead Prioritization | Adjusted scoring weights |
| Transcript Analysis | Persona Development | Updated language and pain data |
| Transcript Analysis | Copy Frameworks | Prospect language for email copy |
| Objection Mining | Copy Frameworks | Pre-handling for steps 2-3 |
| Objection Mining | Sequence Architecture | Objection-aware sequence design |
| Deal Patterns | ICP Matrix Builder | Updated ICP criteria from closed data |
| Deal Patterns | Account Qualification | Adjusted qualification thresholds |

---

## Recommended Execution Sequences

### Sequence A: First Campaign (New Product/Market)

For teams launching outbound for the first time:

```
Week 1: Foundation
├── ICP Matrix Builder (define who to target)
├── Persona Development (define who to contact)
└── Account Qualification (score initial list)

Week 2: Targeting
├── Intent Signals (set up signal monitoring)
├── Lead Prioritization (score and tier the list)
└── Trigger Mapping (map signals to timing)

Week 3: Execution
├── Copy Frameworks (write campaign copy)
├── Sequence Architecture (build the sequence)
└── Personalization Engine (personalize at scale)

Week 4+: Measurement
├── Performance Analysis (diagnose results at day 14)
├── Campaign Benchmarking (contextualize performance)
└── Winning Copy Extraction (extract patterns from data)
```

### Sequence B: Campaign Optimization (Existing Data)

For teams with campaign history who want to improve:

```
Phase 1: Analyze
├── Performance Analysis (diagnose current campaigns)
├── Winning Copy Extraction (find winning patterns)
└── Campaign Benchmarking (identify gaps)

Phase 2: Refine
├── ICP Matrix Builder (update scoring from deal data)
├── Lead Prioritization (re-score with new weights)
└── Copy Frameworks (apply winning patterns to new copy)

Phase 3: Launch improved campaigns
├── Sequence Architecture (redesigned sequences)
├── Personalization Engine (signal-based personalization)
└── Monitor with Performance Analysis
```

### Sequence C: Sales Intelligence Audit

For teams wanting to leverage their sales call data:

```
Phase 1: Extract
├── Transcript Analysis (full 7-layer extraction)
├── Objection Mining (catalog all objections)
└── Deal Patterns (analyze win/loss data)

Phase 2: Apply
├── Persona Development (update with real language)
├── Copy Frameworks (rewrite using prospect vocabulary)
├── ICP Matrix Builder (update criteria from deal patterns)
└── Trigger Mapping (add triggers from transcript data)

Phase 3: Measure
├── Campaign Benchmarking (before/after comparison)
└── Performance Analysis (track improvement)
```

---

## Skill Maturity Model

As you use the system, your mastery progresses through stages:

| Stage | What You're Doing | Skills Active | Typical Timeline |
|-------|------------------|---------------|-----------------|
| **1. Foundation** | Building first ICP and campaign | 5-6 core skills | Week 1-2 |
| **2. Optimization** | Analyzing results, testing variants | 8-10 skills | Month 1-2 |
| **3. Intelligence** | Mining calls, extracting patterns | All 15 skills | Month 2-4 |
| **4. Compounding** | Full flywheel running, every campaign builds on the last | All 15 skills in continuous loop | Month 4+ |

Most teams see the biggest ROI jump between Stage 2 and Stage 3 — when sales intelligence starts feeding back into outbound execution.

---

*This architecture overview is maintained alongside the skill files. As skills are updated or added, this document should be updated to reflect new connections and data flows.*
