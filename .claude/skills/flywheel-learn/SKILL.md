---
name: flywheel-learn
description: Run the self-learning loop. Pulls outreach outcomes read-only (Smartlead, Instantly, lemlist, HeyReach, or a CSV), classifies copy with the skill taxonomy, ranks what wins, and opens a PR proposing skill updates. Use when the user says "/flywheel-learn", "what's winning", "update the playbook from results", or "run the flywheel".
---

# Flywheel: learn from outcomes

Everything runs from `flywheel/` with `uv run`. No step writes to any outreach tool; `_http.py` rejects
any request that is not on the adapter's read allowlist.

## Steps

0. **Sandbox** (first time, or after changing an adapter): `uv run sandbox/smartlead_mock.py` in one terminal, then export
   `SMARTLEAD_BASE_URL=http://127.0.0.1:8787/api/v1 SMARTLEAD_API_KEY=sandbox` and run steps 1-3 against `--db sandbox.sqlite`.
   Unset `SMARTLEAD_BASE_URL` before touching the real account.
1. **Pull** (first time on a new account: dry-run, then one campaign, then all). Smartlead is the default tool.
   ```bash
   cd flywheel
   uv run pull_outcomes.py --dry-run
   uv run pull_outcomes.py --tools smartlead --campaign-ids <one id>
   uv run pull_outcomes.py
   ```
   No API keys? `uv run csv_import.py outcomes.csv` (columns in `csv_import.py`).
1b. **Signals** (optional): if your plays or skills produced a `signals.csv` (`company_domain, signal_type, party, event_date, source_url`), load it so the signal learner has something to join:
   ```bash
   uv run signals_import.py path/to/signals.csv
   ```
2. **Classify** new copy (cached by content hash; a rerun costs nothing)
   ```bash
   uv run classify_copy.py --dry-run && uv run classify_copy.py
   ```
3. **Learn + propose** (branch, copy report + PLAYBOOK, signal report when signals exist, Claude-drafted cited edits, PR)
   ```bash
   uv run propose.py            # add --by-persona once campaigns.toml is filled in
   ```
4. Report the PR link and the headline winners from `reports/<date>-copy-learnings.md` and, if present, the raise/lower verdicts from `reports/<date>-signal-learnings.md`. Say plainly when
   the report declares no winner: that means the sample is too small, not that nothing works.

## Human-owned

`flywheel/campaigns.toml` (persona/segment tags), `flywheel/signals.toml` (signal weights and windows) and every threshold table in the skills. Propose, never edit.
