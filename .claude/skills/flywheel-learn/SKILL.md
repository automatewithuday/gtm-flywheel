---
name: flywheel-learn
description: Run the self-learning loop. Pulls outreach outcomes read-only (Smartlead, Instantly, lemlist, HeyReach, or a CSV), classifies copy with the skill taxonomy, ranks what wins, and opens a PR proposing skill updates. Use when the user says "/flywheel-learn", "what's winning", "update the playbook from results", or "run the flywheel".
---

# Flywheel: learn from outcomes

Everything runs from `flywheel/` with `uv run`. No step writes to any outreach tool; `_http.py` rejects
any request that is not on the adapter's read allowlist.

## Steps

1. **Pull** (first time on a new account: dry-run, then one campaign, then all)
   ```bash
   cd flywheel
   uv run pull_outcomes.py --dry-run
   uv run pull_outcomes.py --tools smartlead --campaign-ids <one id>
   uv run pull_outcomes.py
   ```
   No API keys? `uv run csv_import.py outcomes.csv` (columns in `csv_import.py`).
2. **Classify** new copy (cached by content hash; a rerun costs nothing)
   ```bash
   uv run classify_copy.py --dry-run && uv run classify_copy.py
   ```
3. **Learn + propose** (branch, report, PLAYBOOK, Claude-drafted cited edits, PR)
   ```bash
   uv run propose.py            # add --by-persona once campaigns.toml is filled in
   ```
4. Report the PR link and the headline winners from `reports/<date>-copy-learnings.md`. Say plainly when
   the report declares no winner: that means the sample is too small, not that nothing works.

## Human-owned

`flywheel/campaigns.toml` (persona/segment tags) and every threshold table in the skills. Propose, never edit.
