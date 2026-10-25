"""Which signals actually convert? Report-only calibration of signals.toml against lead-level outcomes.

For each signal type: leads at domains where that signal was fresh during the pull window vs. all leads.
Positive-reply rate with Beta posteriors (reused from learn.py). Verdicts mirror the martechs public-accounts
calibrator: raise if lift >= 1.3, lower if lift <= 0.7, both only at P >= WIN_PROB; otherwise hold / insufficient.
Never edits signals.toml.
"""
import argparse
import datetime as dt
import random
from pathlib import Path

import db
import learn
import score_signals as ss

RAISE, LOWER = 1.3, 0.7


def lead_rows(con, since, until):
    """One pseudo-stat row per lead with a known positive label and a joinable (non-freemail) domain."""
    rows = con.execute("SELECT domain, replied, positive FROM lead_outcome WHERE positive IS NOT NULL AND domain IS NOT NULL "
                       "AND as_of BETWEEN ? AND ?", (since, until)).fetchall()
    return [{"domain": r["domain"], "sends": 1, "replies": max(r["replied"] or 0, r["positive"] or 0), "positive": r["positive"]}
            for r in rows if r["domain"] not in db.FREEMAIL]


def active_domains(con, cfg, since, until):
    """{signal_type: set(domains)} where the signal was inside its freshness window on some day of [since, until].
    # ponytail: window-level freshness, not per-send snapshots; upgrade if campaigns outlive the shortest window."""
    s, u = dt.date.fromisoformat(since), dt.date.fromisoformat(until)
    out = {}
    for r in con.execute("SELECT domain, type, event_date FROM signal").fetchall():
        try:
            ev = dt.date.fromisoformat(r["event_date"])
        except ValueError:
            continue
        if r["type"] in ss.NO_WINDOW:
            lo, hi = 0, 10**6
        elif r["type"] in cfg["freshness_days"]:
            lo, hi = cfg["freshness_days"][r["type"]]
        else:
            continue
        # fresh on day d iff lo <= (d - ev).days <= hi; intersect with [s, u]
        if (u - ev).days >= lo and (s - ev).days <= hi:
            out.setdefault(r["type"], set()).add(r["domain"])
    return out


def evaluate(leads, active, rng):
    base = learn.Cell()
    for l in leads:
        base.add(l)
    results = []
    for typ, doms in sorted(active.items()):
        c = learn.Cell()
        for l in leads:
            if l["domain"] in doms:
                c.add(l)
        if not (c.qualified and base.qualified) or base.rate == 0:
            verdict, lift, p = "insufficient", None, None
        else:
            lift = c.rate / base.rate
            p_up, p_down = learn.p_greater(c, base, rng), learn.p_greater(base, c, rng)
            verdict = ("raise" if lift >= RAISE and p_up >= learn.WIN_PROB else
                       "lower" if lift <= LOWER and p_down >= learn.WIN_PROB else "hold")
            p = p_up if lift >= 1 else p_down
        results.append({"type": typ, "domains": len(doms), "cell": c, "lift": lift, "p": p, "verdict": verdict})
    return base, results


def render(base, results, as_of, since, until, rng):
    f = learn.fmt_pct
    lines = [f"# Signal learnings — {as_of}", "",
             f"Leads with a positive-reply label, pull window {since} → {until}. Baseline: {base.hits}/{base.basis} "
             f"= {f(base.rate)}{'' if base.use_positive else '†'}. A signal is credited to every lead whose company domain had it "
             f"fresh (per `flywheel/signals.toml`) during the window. Verdicts need lift ≥ {RAISE} / ≤ {LOWER} at P ≥ {learn.WIN_PROB:.0%}; "
             f"cells under {learn.MIN_SENDS} leads or {learn.MIN_REPLIES} replies are `insufficient`. Report only: edit signals.toml by hand.", "",
             "| Signal | Domains | Leads | Replies | Positive | Rate | 90% CI | Lift | P | Verdict |", "|---|---:|---:|---:|---:|---:|---|---:|---:|---|"]
    for r in results:
        c, lo_hi = r["cell"], r["cell"].interval(rng) if r["cell"].basis else (0, 0)
        lines.append(f"| {r['type']} | {r['domains']} | {c.basis} | {c.replies} | {c.positive} | {f(c.rate)} | {f(lo_hi[0])}–{f(lo_hi[1])} | "
                     f"{'' if r['lift'] is None else f'{r[chr(108)+chr(105)+chr(102)+chr(116)]:.2f}'} | {'' if r['p'] is None else f'{r[chr(112)]:.2f}'} | **{r['verdict']}** |")
    if not results:
        lines.append("| _no signals overlap the window_ | | | | | | | | | |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=db.DB_PATH)
    ap.add_argument("--config", default=ss.CONFIG)
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--out-dir", default=learn.ROOT)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    con, cfg, rng = db.connect(a.db), ss.load_config(a.config), random.Random(a.seed)
    until = a.until or (con.execute("SELECT MAX(as_of) FROM lead_outcome").fetchone()[0] or a.as_of)
    since = a.since or (dt.date.fromisoformat(until) - dt.timedelta(days=90)).isoformat()
    leads = lead_rows(con, since, until)
    base, results = evaluate(leads, active_domains(con, cfg, since, until), rng)
    out = Path(a.out_dir) / "reports" / f"{a.as_of}-signal-learnings.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(base, results, a.as_of, since, until, rng))
    print(f"wrote {out} ({len(leads)} leads, {len(results)} signal types)")
    return out


if __name__ == "__main__":
    main()
