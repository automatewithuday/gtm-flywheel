# GTM Flywheel — Claude Code Workspace

## How to Use This System

When you need to perform any GTM task, follow this process:

1. **Identify the relevant skill** from the 5 pillars below
2. **Read the SKILL.md** at the path listed
3. **Apply the framework** to the user's specific data and context
4. **Produce deliverables** using the templates provided in the skill
5. **Save outputs** to the appropriate folder

## Skill Map (7 Pillars, 28 Skills)

### Cold Email
| Skill | Path | Use When |
|-------|------|----------|
| Copy Frameworks | `cold-email/copy-frameworks/SKILL.md` | Writing cold email campaigns for any persona |
| Sequence Architecture | `cold-email/sequence-architecture/SKILL.md` | Designing multi-step outbound sequences |
| Personalization Engine | `cold-email/personalization-engine/SKILL.md` | Building personalization workflows at scale |
| B2B Cold Email Copywriting | `cold-email/b2b-cold-email-copywriting/SKILL.md` | Writing or fixing cold email that must reach the primary inbox and get replies |

### ICP Research
| Skill | Path | Use When |
|-------|------|----------|
| ICP Matrix Builder | `icp-research/icp-matrix-builder/SKILL.md` | Defining target accounts with scoring models |
| Persona Development | `icp-research/persona-development/SKILL.md` | Building detailed buyer personas from data |
| Account Qualification | `icp-research/account-qualification/SKILL.md` | Evaluating and scoring target accounts |
| Buying Committee Mapper | `icp-research/buying-committee-mapper/SKILL.md` | Mapping multiple contacts per account (multithreading) |
| List Quality Scorecard | `icp-research/list-quality-scorecard/SKILL.md` | Grading an enriched lead list before upload |

### Signal Scoring
| Skill | Path | Use When |
|-------|------|----------|
| Intent Signals | `signal-scoring/intent-signals/SKILL.md` | Detecting and scoring buying intent |
| Trigger Mapping | `signal-scoring/trigger-mapping/SKILL.md` | Mapping business events to outreach triggers |
| Lead Prioritization | `signal-scoring/lead-prioritization/SKILL.md` | Ranking leads by conversion probability |
| Champion Move Detection | `signal-scoring/champion-move-detection/SKILL.md` | Monthly sweep for customer champions who changed jobs |
| Closed-Won Replication | `signal-scoring/closed-won-replication-play/SKILL.md` | Turning a Closed Won deal into lookalike pipeline |

### Campaign Analytics
| Skill | Path | Use When |
|-------|------|----------|
| Performance Analysis | `campaign-analytics/performance-analysis/SKILL.md` | Analyzing campaign metrics and diagnosing issues |
| Winning Copy Extraction | `campaign-analytics/winning-copy-extraction/SKILL.md` | Extracting patterns from top-performing emails |
| Campaign Benchmarking | `campaign-analytics/campaign-benchmarking/SKILL.md` | Benchmarking performance against baselines |
| Positive Reply Scoring | `campaign-analytics/positive-reply-scoring/SKILL.md` | Classifying replies and measuring positive reply rate vs the 1% bar |
| Experiment Design | `campaign-analytics/experiment-design/SKILL.md` | Isolating one variable per cold email test |
| Deliverability Test | `campaign-analytics/deliverability-test/SKILL.md` | Comparing reply/bounce rates by inbox type (SMTP, Gmail, Outlook) |

### Sales Intelligence
| Skill | Path | Use When |
|-------|------|----------|
| Transcript Analysis | `sales-intelligence/transcript-analysis/SKILL.md` | Mining sales call transcripts for insights |
| Objection Mining | `sales-intelligence/objection-mining/SKILL.md` | Cataloging and pre-handling prospect objections |
| Deal Patterns | `sales-intelligence/deal-patterns/SKILL.md` | Analyzing win/loss patterns in closed deals |

### ABM
| Skill | Path | Use When |
|-------|------|----------|
| ABM Target Accounts | `abm/abm-target-accounts/SKILL.md` | Building, sizing, scoring and tiering an ABM target account list |
| ABM Retargeting | `abm/abm-retargeting/SKILL.md` | Planning retargeting and multi-channel plays for target accounts |
| ABM Measurement | `abm/abm-measurement/SKILL.md` | Choosing account-level metrics, attribution and ROI for ABM |

### Infrastructure
| Skill | Path | Use When |
|-------|------|----------|
| Email Gateway Detection | `infrastructure/email-gateway-detection/SKILL.md` | Finding the secure email gateway or mailbox provider behind each domain |
| Email Waterfall | `infrastructure/email-waterfall/SKILL.md` | Finding and verifying work emails for people missing them |

## Workflow Connections

The skills are designed to be used together:

```
ICP Matrix Builder → Account Qualification → Lead Prioritization
Persona Development → Copy Frameworks → Personalization Engine
Intent Signals → Trigger Mapping → Sequence Architecture
Performance Analysis → Winning Copy Extraction → Campaign Benchmarking
Transcript Analysis → Objection Mining → Deal Patterns
```

Cross-pillar connections:
- **Deal Patterns** findings should update **ICP Matrix Builder** criteria
- **Transcript Analysis** language should feed into **Copy Frameworks** and **Personalization Engine**
- **Winning Copy Extraction** patterns should inform **Sequence Architecture** designs
- **Lead Prioritization** scores should route leads to different **Sequence Architecture** tiers
- **Objection Mining** insights should be pre-handled in **Copy Frameworks** step 2-3
- **ABM Measurement** results feed **Campaign Benchmarking**
- **Champion Move Detection** and **Closed-Won Replication** are triggers for **Trigger Mapping**
- **Buying Committee Mapper** extends **Persona Development** to multithreaded accounts

## Flywheel (self-learning loop)

`flywheel/` turns campaign outcomes into proposed skill updates. Run it with `/flywheel-learn`.
- Read-only by construction: adapters can only call allowlisted read endpoints. Never add a write endpoint without asking.
- `cold-email/copy-frameworks/PLAYBOOK.md` is generated; edit the skill, not the playbook.
- Skill changes arrive as PRs on `flywheel/<date>` branches with evidence. Humans merge.
- Human-owned: `flywheel/campaigns.toml`, `flywheel/signals.toml` and all threshold tables. Propose changes, never apply them silently.
- `.claude/hooks/safety-guard.sh` blocks outbound sends, campaign lifecycle calls and destructive shell commands. If it blocks you, ask; do not route around it.

## Output Folders

Save deliverables to the appropriate location:

| Deliverable | Save To |
|-------------|---------|
| ICP matrices and persona docs | `research/` |
| Lead lists and scoring sheets | `leads/` |
| Campaign copy and sequences | `campaigns/` |
| Performance reports and benchmarks | `reports/` |
| Transcripts and sales analysis | `transcripts/` |
| Flywheel learnings (generated) | `reports/`, `learnings/` |

## Working Conventions

- Use lowercase-kebab-case for file and folder names
- Prefix reports with dates: `2026-02-16-campaign-report.md`
- Save CSV exports with descriptive names, not generic ones
- Keep one version of truth — don't duplicate skill files
