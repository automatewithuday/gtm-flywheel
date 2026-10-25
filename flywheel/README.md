# Flywheel: make the skills learn from your results

The 15 skills are the "weights". This folder pulls real outcomes from your outreach tools (read-only),
measures which copy wins, and opens a pull request that proposes updates to the skills with the evidence
attached. You merge or reject. Nothing changes without you.

```
outreach tool APIs / CSV ─► outcomes.sqlite ─► classify (Claude Haiku) ─► learn.py ─► PR
      read-only                 local               cached by hash          report + PLAYBOOK   you review
```

## Setup

```bash
cd flywheel
cp .env.example .env            # add keys only for tools you use; all calls are read-only
cp campaigns.example.toml campaigns.toml   # optional: tag campaigns with persona/segment
uv run python -m unittest discover -s tests -t .   # no network
```

## Run

See `.claude/skills/flywheel-learn/SKILL.md` or type `/flywheel-learn` in Claude Code.

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
| `pull_outcomes.py` | runs enabled adapters into `outcomes.sqlite` |
| `csv_import.py` | same, from a CSV, for users without API access |
| `classify_copy.py` | labels each unique email with the archetype / subject / opener / CTA taxonomy parsed from the skill files |
| `learn.py` | Beta-posterior ranking per cell, skill minimums (200 sends, 10 replies), winner only at P ≥ 0.90; writes `reports/` and `PLAYBOOK.md` |
| `propose.py` | branch + Claude-drafted cited edits (allowlisted files only) + frontmatter check + `gh pr create` |
| `campaigns.toml` | human-owned persona/segment tags |

## Deliberately not here (yet)

Write-back to sequencers, ICP-weight learning, transcript mining, bandit allocation, memory servers.
Each is a small addition to the same pipeline once the copy loop has proven useful.
