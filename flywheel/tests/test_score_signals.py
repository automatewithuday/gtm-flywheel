"""Selftest cases carried over from the original score_signals.py."""
import unittest
from datetime import date, timedelta

import score_signals as ss

T = date(2026, 6, 30)
cfg = ss.load_config()
ago = lambda n: (T - timedelta(days=n)).isoformat()
tam = [{"company_domain": f"{x}.com", "company_name": x.upper()} for x in "abcdefgh"]


def sig(d, t, p, n, u="", ev=None):
    return {"company_domain": d, "signal_type": t, "party": p, "event_date": ev or ago(n), "source_url": u}


def run(sigs):
    rows, w = ss.score(tam, sigs, cfg, T)
    return {r["company_domain"]: r for r in rows}, w


class ScoreSignalsTest(unittest.TestCase):
    def test_window_boundaries_inclusive(self):
        r, w = run([sig("a.com", "funding", "third", n) for n in (-1, 0)] + [sig("b.com", "funding", "third", n) for n in (28, 29)])
        self.assertEqual(r["a.com"]["signal_count"], 1)
        self.assertTrue(r["a.com"]["signals"].startswith(f"funding@{ago(0)}"))
        self.assertEqual(r["b.com"]["signal_count"], 1)
        self.assertEqual(w["outside freshness window"], 2)
        r, w = run([sig("c.com", "hiring", "third", n) for n in (0, 14, 15)])
        self.assertEqual((r["c.com"]["signal_count"], w["outside freshness window"]), (2, 1))
        self.assertEqual(run([sig("a.com", "news", "third", -1)])[0]["a.com"]["signal_count"], 0)

    def test_dedupe_prefers_source_url(self):
        r, _ = run([sig("c.com", "funding", "third", 20, ""), sig("c.com", "funding", "third", 20, "http://x/1"), sig("c.com", "funding", "third", 20, "http://x/2")])
        self.assertEqual((r["c.com"]["signal_count"], r["c.com"]["score"]), (1, 10))
        self.assertEqual(r["c.com"]["signals"], f"funding@{ago(20)}<http://x/1>")

    def test_cap_and_bands(self):
        r, _ = run([sig("d.com", "engagement", "first", n) for n in (1, 2, 3)] + [sig("d.com", "news", "third", 1)])
        self.assertEqual((r["d.com"]["score"], r["d.com"]["signal_count"], r["d.com"]["band"]), (100, 4, "work_today"))
        r, _ = run([sig("e.com", "engagement", "first", 1), sig("e.com", "website_visit", "first", 1), sig("f.com", "engagement", "first", 1)])
        self.assertEqual((r["e.com"]["score"], r["e.com"]["band"]), (80, "work_today"))
        self.assertEqual((r["f.com"]["score"], r["f.com"]["band"]), (40, "sequence_this_week"))
        r, _ = run([sig("g.com", "news", "second", 1), sig("g.com", "hiring", "third", 8), sig("g.com", "news", "third", 2)])
        self.assertEqual((r["g.com"]["score"], r["g.com"]["band"]), (45, "sequence_this_week"))

    def test_unknown_and_out_of_tam(self):
        _, w = run([sig("zzz.com", "funding", "third", 1), sig("a.com", "bogus", "third", 1), sig("a.com", "funding", "fourth", 1)])
        self.assertEqual((w["domain not in TAM"], w["unknown signal_type"], w["unknown party"]), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
