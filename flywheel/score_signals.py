"""Score accounts from dated signals. Ported from martechs agentic-outbound-plays/outbound/score_signals.py (stdlib + tomllib).

score(tam, signals, cfg, today) -> (rows, warnings)
  tam:     [{company_domain, company_name?}]
  signals: [{company_domain, signal_type, party: first|second|third, event_date: YYYY-MM-DD, source_url?}]
  cfg:     parsed signals.toml
"""
import tomllib
from collections import Counter
from datetime import date
from pathlib import Path

CONFIG = Path(__file__).parent / "signals.toml"
NO_WINDOW = ("crm_closed_lost", "transcript_mention")   # never go stale on their own
PARTIES = {"first": "first_party", "second": "second_party", "third": "third_party"}


def load_config(path=CONFIG):
    return tomllib.loads(Path(path).read_text())


def _dom(s):
    return (s or "").strip().lower()


def fresh_signals(signals, cfg, today):
    """Dedupe + freshness-filter. Returns ({domain: [signal, ...]}, warnings)."""
    warn, seen, by = Counter(), {}, {}
    for s in signals:
        d, t, p = _dom(s.get("company_domain") or s.get("domain")), (s.get("signal_type") or s.get("type") or "").strip(), (s.get("party") or "").strip()
        if t not in cfg["freshness_days"] and t not in NO_WINDOW:
            warn["unknown signal_type"] += 1
            continue
        if p not in PARTIES:
            warn["unknown party"] += 1
            continue
        try:
            ev = date.fromisoformat((s.get("event_date") or "").strip())
        except ValueError:
            warn["blank/malformed event_date"] += 1
            continue
        age = (today - ev).days
        if t not in NO_WINDOW and not cfg["freshness_days"][t][0] <= age <= cfg["freshness_days"][t][1]:
            warn["outside freshness window"] += 1
            continue
        key = (d, t, ev.isoformat())
        if key in seen:                       # same event from another source: keep first, prefer one with a url
            warn["duplicate"] += 1
            if not seen[key]["source_url"] and s.get("source_url"):
                seen[key]["source_url"] = s["source_url"]
            continue
        seen[key] = {"d": d, "type": t, "party": p, "date": ev.isoformat(), "source_url": (s.get("source_url") or "").strip()}
        by.setdefault(d, []).append(seen[key])
    return by, warn


def score(tam, signals, cfg, today):
    tam_doms = {_dom(r["company_domain"]) for r in tam}
    by, warn = fresh_signals(signals, cfg, today)
    for d in list(by):
        if d not in tam_doms:
            warn["domain not in TAM"] += len(by.pop(d))
    b, out = cfg["bands"], []
    for r in tam:
        fs = by.get(_dom(r["company_domain"]), [])
        sc = min(cfg["max_score"], sum(cfg["weights"][PARTIES[f["party"]]] for f in fs))
        band = "work_today" if sc >= b["work_today"] else "sequence_this_week" if sc >= b["sequence_this_week"] else "nurture"
        out.append({"company_domain": r["company_domain"], "company_name": r.get("company_name", ""), "score": sc, "band": band,
                    "signal_count": len(fs), "signals": " | ".join(f"{f['type']}@{f['date']}<{f['source_url']}>" for f in fs)})
    return out, warn
