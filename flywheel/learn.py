"""Rank what wins. Reads outcomes.sqlite (+ classification), writes a dated learnings report and PLAYBOOK.md.

Stats: Beta posterior on positive-reply rate per cell (fallback: reply rate when a tool has no positive label).
Winner is declared only when P(best > runner-up) >= WIN_PROB and both cells meet the skill's minimum sample.
"""
import argparse
import datetime as dt
import random
import sqlite3
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

import db

ROOT = Path(__file__).resolve().parent.parent
MIN_SENDS, MIN_REPLIES, WIN_PROB, SAMPLES = 200, 10, 0.90, 4000   # minimums from winning-copy-extraction/SKILL.md step 1
DIMENSIONS = ["archetype", "subject_formula", "opener", "cta_pattern", "length_bucket"]
LENGTH_BUCKETS = [(60, "<60 words"), (90, "60-90 words"), (120, "90-120 words"), (150, "120-150 words"), (10**9, ">150 words")]


def length_bucket(words):
    if words is None:
        return None
    return next(label for limit, label in LENGTH_BUCKETS if words < limit)


def load_tags(path):
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text())
    return {(tool, str(cid)): meta for tool, camps in data.items() for cid, meta in camps.items()}


def latest_rows(con):
    """One row per (tool, campaign, step, variant) at its latest as_of, joined with copy + classification."""
    return con.execute("""
        SELECT s.tool, s.campaign_id, s.step_no, s.variant, s.as_of, s.sends, s.replies, s.positive, s.meetings,
               st.subject, st.content_hash, c.archetype, c.subject_formula, c.opener, c.cta_pattern, c.word_count
        FROM stat s
        JOIN (SELECT tool, campaign_id, step_no, variant, MAX(as_of) AS as_of FROM stat
              GROUP BY tool, campaign_id, step_no, variant) m
          ON (s.tool, s.campaign_id, s.step_no, s.variant, s.as_of) = (m.tool, m.campaign_id, m.step_no, m.variant, m.as_of)
        LEFT JOIN step st ON (st.tool, st.campaign_id, st.step_no, st.variant) = (s.tool, s.campaign_id, s.step_no, s.variant)
        LEFT JOIN classification c ON c.content_hash = st.content_hash
        WHERE s.step_no > 0 AND s.sends > 0""").fetchall()


class Cell:
    """Aggregates rows. Metric basis: positive replies over the rows that report them; if those rows are too few
    to rank, falls back to total replies over all rows (marked † in reports)."""

    def __init__(self):
        self.sends = self.replies = 0            # all rows
        self.positive = self.pos_sends = self.pos_replies = 0   # rows whose tool exposes a positive label
        self.n = 0

    def add(self, r):
        self.n += 1
        self.sends += r["sends"] or 0
        self.replies += r["replies"] or 0
        if r["positive"] is not None:
            self.positive += r["positive"]
            self.pos_sends += r["sends"] or 0
            self.pos_replies += r["replies"] or 0

    @property
    def use_positive(self):
        return self.pos_sends >= MIN_SENDS and self.pos_replies >= MIN_REPLIES

    @property
    def hits(self):
        return self.positive if self.use_positive else self.replies

    @property
    def basis(self):          # sends the rate is computed over
        return self.pos_sends if self.use_positive else self.sends

    @property
    def rate(self):
        return self.hits / self.basis if self.basis else 0.0

    @property
    def qualified(self):
        return self.basis >= MIN_SENDS and (self.pos_replies if self.use_positive else self.replies) >= MIN_REPLIES

    def draws(self, rng, k=SAMPLES):
        return [rng.betavariate(self.hits + 1, self.basis - self.hits + 1) for _ in range(k)]

    def interval(self, rng, lo=0.05, hi=0.95):
        d = sorted(self.draws(rng))
        return d[int(lo * len(d))], d[int(hi * len(d)) - 1]


def p_greater(a, b, rng):
    da, dbb = a.draws(rng), b.draws(rng)
    return sum(x > y for x, y in zip(da, dbb)) / len(da)


def aggregate(rows, tags, by_persona=False):
    """{dimension: {(persona, value): Cell}}; persona is '*' unless by_persona."""
    out = {d: defaultdict(Cell) for d in DIMENSIONS + ["step"]}
    for r in rows:
        meta = tags.get((r["tool"], r["campaign_id"]), {})
        if meta.get("include") is False:
            continue
        persona = meta.get("persona", "unknown") if by_persona else "*"
        values = {d: r[d] for d in DIMENSIONS if d != "length_bucket"}
        values["length_bucket"] = length_bucket(r["word_count"])
        values["step"] = f"Step {r['step_no']}"
        for d, v in values.items():
            if v:
                out[d][(persona, v)].add(r)
    return out


def rank(cells, rng):
    """Sorted qualified cells, plus a winner statement if top beats second at WIN_PROB."""
    q = [c for c in cells.items() if c[1].qualified]
    if any(c.use_positive for _, c in q):        # never compare a reply-rate cell against positive-rate cells
        q = [c for c in q if c[1].use_positive]
    q.sort(key=lambda kv: kv[1].rate, reverse=True)
    winner = None
    if len(q) >= 2:
        p = p_greater(q[0][1], q[1][1], rng)
        if p >= WIN_PROB:
            winner = (q[0][0], q[1][0], p)
    elif len(q) == 1:
        winner = None
    return q, winner


def fmt_pct(x):
    return f"{100 * x:.1f}%"


def render_report(agg, rng, as_of, n_rows):
    lines = [f"# Copy learnings — {as_of}", "",
             f"Based on {n_rows} step/variant cells at their latest snapshot. Metric: positive-reply rate "
             f"(reply rate where a tool has no positive label, marked †). Cells below {MIN_SENDS} sends or "
             f"{MIN_REPLIES} replies are listed but not ranked. 90% credible intervals; a winner is declared only when "
             f"P(best > runner-up) ≥ {WIN_PROB:.0%}.", ""]
    for dim in DIMENSIONS + ["step"]:
        cells = agg[dim]
        if not cells:
            continue
        lines += [f"## By {dim.replace('_', ' ')}", "", "| Value | Persona | Sends | Replies | Positive | Rate | 90% CI | Ranked |",
                  "|---|---|---:|---:|---:|---:|---|---|"]
        ranked_keys = {k for k, _ in rank(cells, rng)[0]}
        for (persona, value), c in sorted(cells.items(), key=lambda kv: kv[1].rate, reverse=True):
            lo, hi = c.interval(rng)
            mark = "" if c.use_positive else "†"
            lines.append(f"| {value} | {persona} | {c.basis} | {c.replies} | {c.positive if c.use_positive else '—'} | "
                         f"{fmt_pct(c.rate)}{mark} | {fmt_pct(lo)}–{fmt_pct(hi)} | {'yes' if (persona, value) in ranked_keys else 'no'} |")
        ranked, winner = rank(cells, rng)
        if any(c.qualified and not c.use_positive for c in cells.values()) and any(c.use_positive for c in cells.values()):
            lines += ["", "† cells are shown for context but excluded from ranking: reply rate and positive-reply rate are not comparable."]
        if winner:
            (p1, v1), (p2, v2), p = winner
            lines += ["", f"**Winner:** {v1} beats {v2} with P={p:.2f} "
                          f"({fmt_pct(cells[(p1, v1)].rate)} vs {fmt_pct(cells[(p2, v2)].rate)})."]
        elif len(ranked) >= 2:
            lines += ["", f"No winner yet: top two are not separated at {WIN_PROB:.0%} confidence."]
        elif not ranked:
            lines += ["", "No cell meets the minimum sample yet."]
        lines.append("")
    return "\n".join(lines)


def render_playbook(agg, rng, as_of, n_rows, n_campaigns):
    def top(dim, k=3):
        ranked, _ = rank(agg[dim], rng)
        return [f"{i + 1}. {v} — {fmt_pct(c.rate)}{'' if c.use_positive else '†'} ({c.basis} sends)" for i, ((_, v), c) in enumerate(ranked[:k])] \
            or ["_insufficient data_"]

    def avoid(dim):
        ranked, _ = rank(agg[dim], rng)
        return ranked[-1][0][1] if len(ranked) >= 3 else "_insufficient data_"

    lb, _ = rank(agg["length_bucket"], rng)
    target = lb[0][0][1] if lb else "_insufficient data_"
    return "\n".join([
        "<!-- GENERATED by flywheel/learn.py. Do not edit by hand; edit the skill instead. -->",
        f"# COPY PLAYBOOK — learned from your campaigns", "",
        f"Last Updated: {as_of}  ", f"Based on: {n_campaigns} campaigns, {n_rows} step/variant cells", "",
        "Template: campaign-analytics/winning-copy-extraction/SKILL.md → Step 4. "
        "Archetypes: cold-email/copy-frameworks/SKILL.md.", "",
        "## Subject lines", *top("subject_formula"), f"\nAvoid: {avoid('subject_formula')}", "",
        "## Opening lines", *top("opener"), "",
        "## Body copy — winning archetypes (ranked)", *top("archetype"), "",
        "## CTAs", *top("cta_pattern"), "",
        "## Email length", f"Target: {target}", "", "† = reply rate (tool has no positive-reply label for enough sends)", "",
        "## Steps", *top("step", 8), "",
        f"_Full tables with credible intervals: reports/{as_of}-copy-learnings.md_", ""])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=db.DB_PATH)
    ap.add_argument("--tags", default=Path(__file__).parent / "campaigns.toml")
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--by-persona", action="store_true")
    ap.add_argument("--out-dir", default=ROOT)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)
    con = db.connect(a.db)
    rows = latest_rows(con)
    if not rows:
        sys.exit("no stats in db; run pull_outcomes.py first")
    tags = load_tags(Path(a.tags))
    agg = aggregate(rows, tags, a.by_persona)
    n_campaigns = len({(r["tool"], r["campaign_id"]) for r in rows})
    out = Path(a.out_dir)
    report = out / "reports" / f"{a.as_of}-copy-learnings.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_report(agg, rng, a.as_of, len(rows)))
    playbook = out / "cold-email" / "copy-frameworks" / "PLAYBOOK.md"
    playbook.parent.mkdir(parents=True, exist_ok=True); playbook.write_text(render_playbook(agg, rng, a.as_of, len(rows), n_campaigns))
    print(f"wrote {report}\nwrote {playbook}")


if __name__ == "__main__":
    main()
