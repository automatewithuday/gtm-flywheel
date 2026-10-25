import json
import sqlite3
import unittest
from pathlib import Path

import db
from adapters import _http, smartlead as sl

FX = Path(__file__).parent / "fixtures" / "smartlead"
load = lambda n: json.loads((FX / n).read_text())


class FakeClient:
    def __init__(self):
        self.calls = []

    def get(self, template, params=None, **kw):
        self.calls.append(template)
        if template == "/campaigns/":
            return load("campaigns.json")
        f = {"/campaigns/{id}/sequences": "sequences_%s.json",
             "/campaigns/{id}/sequence-analytics": "sequence_analytics_%s.json"}[template]
        return load(f % kw["id"])


class T(unittest.TestCase):
    def setUp(self):
        self.out = sl.pull(FakeClient(), "2026-09-01T00:00:00Z", "2026-10-26T00:00:00Z", "2026-10-26")

    def test_counts(self):
        self.assertEqual([len(self.out[k]) for k in ("campaigns", "steps", "stats")], [2, 6, 6])

    def test_variants_and_positive(self):
        s = {(r["campaign_id"], r["step_no"], r["variant"]): r for r in self.out["stats"]}
        self.assertEqual({v for (c, n, v) in s if c == "101" and n == 1}, {"A", "B"})
        self.assertEqual(s[("101", 1, "B")]["positive"], 5)
        self.assertEqual(s[("101", 1, "B")]["sends"], 100)
        self.assertEqual(s[("101", 2, "A")]["positive"], 1)   # no variants -> total_stats as "A"
        self.assertIsNone(s[("101", 1, "A")]["meetings"])

    def test_steps_text(self):
        st = {(r["campaign_id"], r["step_no"], r["variant"]): r for r in self.out["steps"]}
        self.assertEqual(st[("101", 1, "A")]["body"], "Hi {{first_name}},\nSaw you run RevOps at {{company}}.\nWorth a chat?")
        self.assertEqual(st[("101", 2, "A")]["subject"], "Re: Quick question")
        self.assertIn("is pipeline reporting a pain?", st[("101", 1, "B")]["body"])
        self.assertTrue(all(r["channel"] == "email" for r in st.values()))

    def test_hash_stable(self):
        again = sl.pull(FakeClient(), "a", "b", "c")
        h = lambda o: [db.content_hash(r["subject"], r["body"]) for r in o["steps"]]
        self.assertEqual(h(self.out), h(again))
        self.assertEqual(len(set(h(self.out))), 6)

    def test_upsert(self):
        con = sqlite3.connect(":memory:")
        con.executescript(db.SCHEMA)
        db.upsert(con, self.out)
        n = lambda t: con.execute(f"select count(*) from {t}").fetchone()[0]
        self.assertEqual((n("campaign"), n("step"), n("stat")), (2, 6, 6))

    def test_allowlist(self):
        with self.assertRaises(_http.NotAllowed):
            sl.make_client("k", dry_run=True).post("/campaigns/")

    def test_dry_run(self):
        c = sl.make_client("k", dry_run=True)
        out = sl.pull(c, "a", "b", "c")
        self.assertEqual(out, {"campaigns": [], "steps": [], "stats": []})
        self.assertEqual(len(c.calls), 1)  # dry-run: logged, never sent


if __name__ == "__main__":
    unittest.main()
