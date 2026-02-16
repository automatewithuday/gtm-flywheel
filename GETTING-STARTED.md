# Getting Started with Claude Code for GTM

This guide walks you through setting up Claude Code as your GTM co-pilot using the skills in this repo.

---

## What You Need

1. **Claude Code** — Anthropic's CLI tool for Claude ([claude.ai/claude-code](https://claude.ai/claude-code))
2. **This repo** cloned locally
3. **Your business data** — campaign metrics, CRM exports, call transcripts, or lead lists

That's it. No APIs to configure. No dependencies to install. No servers to run.

---

## Setup (5 Minutes)

### Step 1: Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

### Step 2: Clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/gtm-blueprint.git
cd gtm-blueprint
```

### Step 3: Start Claude Code

```bash
claude
```

Claude Code automatically reads the `CLAUDE.md` file in your working directory. This gives it awareness of all 15 skills and how to use them.

### Step 4: Ask for what you need

```
"Help me build an ICP matrix for my company."
```

Claude Code will read the relevant skill file and walk you through the framework step by step.

---

## Your First 5 Tasks

Here are five high-impact tasks to start with, in order of value:

### Task 1: Build Your ICP Matrix
**Skill:** `icp-research/icp-matrix-builder/SKILL.md`

```
"Read the ICP Matrix Builder skill. I'm a [your product/service]
company selling to [your market]. Help me build an ICP matrix
using the 5-dimension framework."
```

**What you'll get:** A tiered scoring model that defines exactly who to target.

**Input needed:** Description of your best 5-10 customers and your worst 3-5 customers.

### Task 2: Write Your First Campaign
**Skill:** `cold-email/copy-frameworks/SKILL.md` + `cold-email/sequence-architecture/SKILL.md`

```
"Read the Copy Frameworks and Sequence Architecture skills.
Help me write a 4-step cold email sequence for [persona]
at [company type] using the [archetype] approach."
```

**What you'll get:** A complete 4-step sequence with 2-3 variants per step, subject lines, and a settings checklist.

**Input needed:** Target persona, their top pain point, and your strongest proof point.

### Task 3: Score Your Lead List
**Skill:** `signal-scoring/lead-prioritization/SKILL.md`

```
"Read the Lead Prioritization skill. Here's my lead list [attach CSV].
Help me build a scoring model and assign priority tiers."
```

**What you'll get:** A scored and tiered lead list with P1-P5 priority assignments.

**Input needed:** A CSV or list of target accounts with basic firmographic data.

### Task 4: Analyze a Campaign
**Skill:** `campaign-analytics/performance-analysis/SKILL.md`

```
"Read the Performance Analysis skill. Here are my campaign
metrics [paste or attach data]. Run a full 6-layer diagnostic."
```

**What you'll get:** A campaign scorecard identifying exactly what's working and what's broken, with specific fix recommendations.

**Input needed:** Campaign data — sends, opens, replies (positive/negative), bounces, meetings booked.

### Task 5: Mine Your Sales Calls
**Skill:** `sales-intelligence/transcript-analysis/SKILL.md`

```
"Read the Transcript Analysis skill. Here are 10 sales call
transcripts. Run the 7-layer extraction and give me a report."
```

**What you'll get:** Pain points ranked by frequency, trigger events, a language bank, objection catalog, and competitive intelligence — all from your own data.

**Input needed:** 10+ call transcripts (text format from Gong, Fireflies, Otter, or similar).

---

## How to Use Skills Effectively

### Be specific about your context

Instead of: "Help me with cold email"

Say: "I sell marketing analytics software to VP Marketing at Series B SaaS companies with 100-500 employees. Our main competitor is Mixpanel. Read the Copy Frameworks skill and help me write a Problem/Solution email using our main differentiator: real-time attribution."

The more context you provide, the better Claude Code applies the framework.

### Combine skills for complex tasks

Skills are designed to work together. For a full campaign launch:

```
1. "Read the ICP Matrix Builder skill. Help me define my ICP."
2. "Now read the Persona Development skill. Build personas for the top 2 titles in my ICP."
3. "Read the Intent Signals skill. Which signals should I monitor for this ICP?"
4. "Read the Copy Frameworks skill. Write Step 1 of my campaign using The Observation archetype."
5. "Read the Sequence Architecture skill. Build the full 4-step sequence with variants."
```

### Feed data back into the system

After running campaigns, use the analytics skills to extract learnings:

```
1. "Read Performance Analysis. Diagnose this campaign's results."
2. "Read Winning Copy Extraction. What patterns made the top variant win?"
3. "Read Campaign Benchmarking. How does this compare to industry standards?"
```

Then feed those insights back:

```
"Based on the winning copy patterns, update my next campaign's Step 1."
```

This creates the compounding flywheel — every campaign improves the next one.

---

## Connecting Your Data

Claude Code works best with your actual business data. Here's how to make your data available:

### Campaign Data
Export metrics from your sending platform (Instantly, Lemlist, SmartLead, Apollo, etc.) as CSV files. Place them in a `data/` folder.

### CRM Data
Export closed-won and closed-lost deals as CSV. Include: deal size, source channel, sales cycle length, champion title, and loss reason.

### Call Transcripts
Export transcripts from your call recording tool (Gong, Fireflies, Otter, Chorus, etc.) as text files. Place them in a `transcripts/` folder.

### Lead Lists
Any CSV with company name, employee count, industry, and contact information works.

---

## Tips for Power Users

1. **Start with one pillar.** Don't try to use all 15 skills at once. Pick the pillar that addresses your biggest current problem and go deep.

2. **Build your data library.** The skills become exponentially more powerful as you feed them real data — campaign metrics, call transcripts, CRM exports. Start collecting early.

3. **Create your own templates.** The templates in each skill are starting points. As you use them, customize the templates for your specific industry, product, and personas.

4. **Run the flywheel quarterly.** Every quarter: analyze campaigns → extract winning patterns → update your ICP → refresh your sequences → launch better campaigns. This is how outbound compounds.

5. **Combine with other tools.** Claude Code can connect to databases, APIs, and MCP servers. Pair these skills with live data feeds for real-time intelligence.

---

## FAQ

**Q: Do I need to be technical to use this?**
No. The skills are written in plain English. Claude Code handles any technical complexity. You just need to know your business and your data.

**Q: Can I modify the skills?**
Yes. Fork the repo and customize any skill to match your specific workflow, industry, or methodology.

**Q: How is this different from ChatGPT prompts?**
These aren't prompts — they're structured operational frameworks. Each skill contains scoring models, decision trees, templates, and quality benchmarks that Claude Code follows systematically. A prompt gives you a suggestion. A skill gives you a process.

**Q: What model works best?**
Claude Opus for deep analysis tasks (transcript analysis, deal patterns, ICP research). Claude Sonnet for execution tasks (writing copy, building sequences, scoring leads).

---

*Built by [ColdIQ](https://coldiq.com) — the GTM agency that runs on AI agents.*
