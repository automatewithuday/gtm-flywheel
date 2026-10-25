import json
import sqlite3
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

import db
from adapters import _http, instantly

FX = Path(__file__).parent / "fixtures" / "instantly"
C1, C2 = "c1111111-0000-4000-8000-000000000001", "c2222222-0000-4000-8000-000000000002"


def fx(name):
    return json.loads((FX / name).read_text())


def served(self, method, url, body):
    """Stand-in for Client._send: serve fixtures by URL, no network."""
    if "/campaigns/analytics/steps" in url:
        return fx("analytics_steps_c1.json" if C1 in url else "analytics_steps_c2.json")
    if "/campaigns/" in url:
        return fx("campaign_c1.json" if C1 in url else "campaign_c2.json")
    if url.split("?")[0].endswith("/campaigns"):
        return fx("campaigns_list.json")
    if url.endswith("/leads/list"):
        assert method == "POST"
        if body["campaign"] == C2:
            return fx("leads_c2.json")
        return fx("leads_c1_page2.json" if body.get("starting_after") else "leads_c1_page1.json")
    raise AssertionError(url)


def run_pull(**kw):
    with mock.patch.object(_http.Client, "_send", served):
        return instantly.pull(instantly.make_client("k"), "2026-01-01", "2026-02-01", "2026-02-01", **kw)


class T(unittest.TestCase):
    def test_counts(self):
        r = run_pull()
        self.assertEqual(len(r["campaigns"]), 2)
        self.assertEqual(len(r["steps"]), 6)   # disabled variant skipped
        self.assertEqual(len(r["stats"]), 6)

    def test_campaign_filter(self):
        self.assertEqual(len(run_pull(campaign_ids=[C2])["campaigns"]), 1)

    def test_labels_and_html(self):
        s = {(x["campaign_id"], x["step_no"], x["variant"]): x for x in run_pull()["steps"]}
        self.assertEqual(sorted(k[1:] for k in s if k[0] == C1), [(1, "A"), (1, "B"), (2, "A")])
        self.assertEqual(s[(C1, 1, "A")]["body"], "Hi {{firstName}},\nSaw you are hiring SDRs\nWorth a chat?")
        self.assertNotIn((C2, 2, "B"), s)

    def test_attribution(self):
        st = {(x["campaign_id"], x["step_no"], x["variant"]): x for x in run_pull()["stats"]}
        got = lambda c, n, v: (st[(c, n, v)]["sends"], st[(c, n, v)]["replies"],
                               st[(c, n, v)]["positive"], st[(c, n, v)]["meetings"])
        self.assertEqual(got(C1, 1, "A"), (100, 5, 2, 1))   # statuses 1,2 positive; -1 ignored
        self.assertEqual(got(C1, 1, "B"), (100, 3, 1, 1))   # 0 ignored, 3 counts
        self.assertEqual(got(C1, 2, "A"), (80, 2, 1, 1))    # 4 counts, -2 ignored, null lead skipped
        self.assertEqual(got(C2, 2, "A"), (50, 1, 1, 0))
        self.assertEqual(got(C2, 1, "A"), (60, 2, 0, 0))    # -3 ignored

    def test_zero_based_steps(self):
        an = [{"step": "0", "variant": "0", "sent": 1, "unique_replies": 0}]
        lead = [{"email_replied_step": 0, "email_replied_variant": 0, "lt_interest_status": 1}]
        r = instantly.norm_stats("c", an, lead, "d")[0]
        self.assertEqual((r["step_no"], r["variant"], r["positive"]), (1, "A", 1))

    def test_hash_stable(self):
        a, b = run_pull()["steps"], run_pull()["steps"]
        ha = [db.content_hash(x["subject"], x["body"]) for x in a]
        self.assertEqual(ha, [db.content_hash(x["subject"], x["body"]) for x in b])
        self.assertEqual(len(set(ha)), len(ha))

    def test_upsert(self):
        con = db.connect(":memory:")
        r = run_pull()
        db.upsert(con, r)
        db.upsert(con, r)   # idempotent
        self.assertEqual(con.execute("select count(*) from campaign").fetchone()[0], 2)
        self.assertEqual(con.execute("select count(*) from step").fetchone()[0], 6)
        self.assertEqual(con.execute("select sum(positive) from stat").fetchone()[0], 5)

    def test_leads(self):
        r = run_pull()
        by = lambda c: [x for x in r["leads"] if x["campaign_id"] == c]
        self.assertEqual((len(by(C1)), len(by(C2))), (10, 3))   # all contacted, not only repliers
        L = {x["email"]: x for x in r["leads"]}
        k = lambda e: (L[e]["status"], L[e]["replied"], L[e]["positive"], L[e]["meeting"], L[e]["step_no"], L[e]["variant"])
        self.assertEqual(k("b@example.com"), ("2", 1, 1, 1, 1, "A"))
        self.assertEqual(k("a@example.com"), ("1", 1, 1, 0, 1, "A"))
        self.assertEqual(k("c@example.com"), ("-1", 1, 0, 0, 1, "A"))
        self.assertEqual(k("f@example.com"), ("4", 1, 1, 1, 2, "A"))
        self.assertEqual(k("h@example.com"), (None, 1, None, None, None, None))   # replied, status unknown
        self.assertEqual(k("i@example.com"), (None, 0, None, None, None, None))   # contacted only

    def test_lead_pagination(self):
        calls = []
        def spy(self, method, url, body):
            if url.endswith("/leads/list"):
                calls.append(body)
            return served(self, method, url, body)
        with mock.patch.object(_http.Client, "_send", spy):
            instantly.pull(instantly.make_client("k"), "a", "b", "c")
        self.assertEqual(len(calls), 3)   # c1: 2 pages, c2: 1
        self.assertTrue(all("filter" not in b and b["limit"] == 100 for b in calls))

    def test_lead_upsert_no_raw_email(self):
        con = db.connect(":memory:")
        db.upsert(con, run_pull())
        self.assertEqual(con.execute("select count(*) from lead_outcome").fetchone()[0], 13)
        dump = repr([r for t in ("lead_outcome", "stat", "step", "campaign")
                     for r in con.execute(f"select * from {t}")])
        self.assertNotIn("a@example.com", dump)
        self.assertNotIn("@example.com", dump)   # bare domain only

    def test_allowlist(self):
        c = instantly.make_client("k", dry_run=True)
        with self.assertRaises(_http.NotAllowed):
            c.post("/campaigns")
        with self.assertRaises(_http.NotAllowed):
            c.get("/leads/list")
        self.assertEqual(c.calls, [])

    def test_dry_run_no_network(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")):
            r = instantly.pull(instantly.make_client("k", dry_run=True), "a", "b", "c")
        self.assertEqual(r, {"campaigns": [], "steps": [], "stats": [], "leads": []})


if __name__ == "__main__":
    unittest.main()
