# GTM Blueprint — Claude Code Workspace

## How to Use This System

When you need to perform any GTM task, follow this process:

1. **Identify the relevant skill** from the 5 pillars below
2. **Read the SKILL.md** at the path listed
3. **Apply the framework** to the user's specific data and context
4. **Produce deliverables** using the templates provided in the skill
5. **Save outputs** to the appropriate folder

## Skill Map (5 Pillars, 15 Skills)

### Cold Email
| Skill | Path | Use When |
|-------|------|----------|
| Copy Frameworks | `cold-email/copy-frameworks/SKILL.md` | Writing cold email campaigns for any persona |
| Sequence Architecture | `cold-email/sequence-architecture/SKILL.md` | Designing multi-step outbound sequences |
| Personalization Engine | `cold-email/personalization-engine/SKILL.md` | Building personalization workflows at scale |

### ICP Research
| Skill | Path | Use When |
|-------|------|----------|
| ICP Matrix Builder | `icp-research/icp-matrix-builder/SKILL.md` | Defining target accounts with scoring models |
| Persona Development | `icp-research/persona-development/SKILL.md` | Building detailed buyer personas from data |
| Account Qualification | `icp-research/account-qualification/SKILL.md` | Evaluating and scoring target accounts |

### Signal Scoring
| Skill | Path | Use When |
|-------|------|----------|
| Intent Signals | `signal-scoring/intent-signals/SKILL.md` | Detecting and scoring buying intent |
| Trigger Mapping | `signal-scoring/trigger-mapping/SKILL.md` | Mapping business events to outreach triggers |
| Lead Prioritization | `signal-scoring/lead-prioritization/SKILL.md` | Ranking leads by conversion probability |

### Campaign Analytics
| Skill | Path | Use When |
|-------|------|----------|
| Performance Analysis | `campaign-analytics/performance-analysis/SKILL.md` | Analyzing campaign metrics and diagnosing issues |
| Winning Copy Extraction | `campaign-analytics/winning-copy-extraction/SKILL.md` | Extracting patterns from top-performing emails |
| Campaign Benchmarking | `campaign-analytics/campaign-benchmarking/SKILL.md` | Benchmarking performance against baselines |

### Sales Intelligence
| Skill | Path | Use When |
|-------|------|----------|
| Transcript Analysis | `sales-intelligence/transcript-analysis/SKILL.md` | Mining sales call transcripts for insights |
| Objection Mining | `sales-intelligence/objection-mining/SKILL.md` | Cataloging and pre-handling prospect objections |
| Deal Patterns | `sales-intelligence/deal-patterns/SKILL.md` | Analyzing win/loss patterns in closed deals |

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

## Output Folders

Save deliverables to the appropriate location:

| Deliverable | Save To |
|-------------|---------|
| ICP matrices and persona docs | `research/` |
| Lead lists and scoring sheets | `leads/` |
| Campaign copy and sequences | `campaigns/` |
| Performance reports and benchmarks | `reports/` |
| Transcripts and sales analysis | `transcripts/` |

## Working Conventions

- Use lowercase-kebab-case for file and folder names
- Prefix reports with dates: `2026-02-16-campaign-report.md`
- Save CSV exports with descriptive names, not generic ones
- Keep one version of truth — don't duplicate skill files
