# Flywheel: make the skills learn from your results

The 28 skills are the "weights". This folder pulls real outcomes from your outreach tools (read-only),
measures which copy wins, and opens a pull request that proposes updates to the skills with the evidence
attached. You merge or reject. Nothing changes without you.

```
outreach tool APIs / CSV ─► outcomes.sqlite ─► classify (Claude Haiku) ─► learn.py ────────┐
      read-only                 local               cached by hash          copy report + PLAYBOOK ├─► PR, you review
signals.csv ──────────────► signal table ──► learn_signals.py (vs lead-level outcomes) ── signal report ┘
```

Two learners share one database. Copy: which archetypes, subject formulas, CTAs and lengths win. Signals: which
dated buying signals (funding, hiring, job change, …) actually lift positive-reply rate, measured on lead-level outcomes
joined by company domain. Both are report-only; the PR proposes, you merge.

## Setup

```bash
cd flywheel
cp .env.example .env            # add keys only for tools you use; all calls are read-only
cp campaigns.example.toml campaigns.toml   # optional: tag campaigns with persona/segment
uv run python -m unittest discover -s tests -t .   # no network
```

## Sandbox first (no account needed)

Smartlead has no public sandbox, so this repo ships one: a local mock of the read endpoints the adapter uses,
serving the documented payload shapes over real HTTP. Use it the way you would use Postman: watch every request,
inject rate limits, confirm that writes are refused.

```bash
uv run sandbox/smartlead_mock.py --rate-limit-every 6        # terminal 1: logs one JSON line per request
export SMARTLEAD_BASE_URL=http://127.0.0.1:8787/api/v1 SMARTLEAD_API_KEY=sandbox
uv run pull_outcomes.py --db sandbox.sqlite                  # terminal 2: the real adapter, real urllib, mock server
uv run learn.py --db sandbox.sqlite --out-dir /tmp/sandbox-out
```

`tests/test_smartlead_sandbox.py` runs the same thing in-process: pull over HTTP equals the fixture pull, every
request is an authenticated GET, the adapter survives injected 429s, a POST is refused by the client before any
network call and by the mock if forced. Unset `SMARTLEAD_BASE_URL` to go back to the production URL.

## Run

Smartlead is the default and only tool pulled unless you pass `--tools`. See `.claude/skills/flywheel-learn/SKILL.md`
or type `/flywheel-learn` in Claude Code.

## Safety

- `adapters/_http.py` allowlists exact `(method, path)` pairs per tool. A write endpoint cannot be called by accident; the client raises before any network I/O.
- `--dry-run` prints the requests it would make and makes none.
- None of the four tools offer read-only API keys, so this allowlist is the guard. Review `ALLOW` in each adapter before adding endpoints.

## What each tool exposes

| | Smartlead | Instantly v2 | lemlist | HeyReach |
|---|---|---|---|---|
| Variant-level sends/replies | yes | yes | yes | no (campaign only) |
| Positive-reply label | native per variant | native per lead, attributed to variant | campaign level | native auto-tag, campaign level |
| Meetings | no | yes | campaign level | no |

Unverified field assumptions per tool are listed in `adapters/NOTES.md`. Check them on your first real pull.

## Files

| File | Role |
|---|---|
| `pull_outcomes.py` | runs enabled adapters into `outcomes.sqlite` (default: Smartlead only; `<TOOL>_BASE_URL` points at a sandbox) |
| `sandbox/smartlead_mock.py` | local read-only Smartlead API serving fixture payloads; request log, 429 injection, 405 on writes |
| `csv_import.py` | same, from a CSV, for users without API access; lead rows via `email` + `status` columns |
| `signals_import.py` | loads dated signals (`company_domain, signal_type, party, event_date, source_url`) from the CSV your plays or skills produce |
| `score_signals.py` | party-weight + freshness-window account scorer (ported from martechs outbound plays); reads `signals.toml` |
| `learn_signals.py` | per signal type: positive-reply lift vs baseline on lead-level outcomes, Beta posteriors, verdict raise / lower / hold / insufficient |
| `signals.toml` | human-owned signal weights, freshness windows and bands; the learner only proposes `# proposed:` comments |
| `classify_copy.py` | labels each unique email with the archetype / subject / opener / CTA taxonomy parsed from the skill files |
| `learn.py` | Beta-posterior ranking per cell, skill minimums (200 sends, 10 replies), winner only at P ≥ 0.90; writes `reports/` and `PLAYBOOK.md` |
| `propose.py` | branch + Claude-drafted cited edits (allowlisted files only) + frontmatter check + `gh pr create` |
| `campaigns.toml` | human-owned persona/segment tags |
| `db.py` | sqlite schema: campaign, step, stat, classification, lead_outcome (hashed emails + domain), signal |

## Lead-level data and privacy

Smartlead and Instantly adapters also pull per-lead outcomes so signals and ICP features can be joined by company domain.
Emails are hashed before they reach the database (`db.lead_key`); only the hash and the domain are stored. lemlist and HeyReach
expose campaign-level data only, so they contribute no lead rows in v1.

## Deliberately not here (yet)

Write-back to sequencers, ICP-weight learning, half-life decay and signal stacks, send-time snapshots, transcript mining, bandit allocation, memory servers.
Each is a small addition to the same pipeline once the copy loop has proven useful.
