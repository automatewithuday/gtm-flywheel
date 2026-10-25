import contextlib, io, json, unittest
from pathlib import Path
from unittest import mock

import db
from adapters import _http, heyreach

FX = Path(__file__).parent / "fixtures" / "heyreach"
load = lambda n: json.loads((FX / n).read_text())


class Fake(_http.Client):
    def _send(self, method, url, body, retries=3):
        if url.endswith("/campaign/GetAll"):
            return load("campaign_GetAll.json")
        if "GetCampaignSequence" in url:
            return load(f"sequence_{url.split('campaignId=')[1]}.json")
        if url.endswith("/stats/GetOverallStatsByCampaign"):
            return load("stats_GetOverallStatsByCampaign.json")
        if url.endswith("/inbox/GetConversationsV3"):
            assert body["filters"]["latestAutoTagNames"] == ["Interested"]
            return load(f"conversations_interested_{body['filters']['campaignIds'][0]}.json")
        raise AssertionError(url)


def client():
    return Fake("heyreach", heyreach.BASE_URL, heyreach.ALLOW)


def run():
    return heyreach.pull(client(), "2026-09-01", "2026-10-26", "2026-10-26")


class T(unittest.TestCase):
    def test_counts_and_variants(self):
        r = run()
        self.assertEqual(len(r["campaigns"]), 2)
        self.assertEqual(len(r["steps"]), 8)   # per campaign: 2 message nodes x 2 variants
        self.assertEqual(len(r["stats"]), 2)
        s = {(x["campaign_id"], x["step_no"], x["variant"]): x for x in r["steps"]}
        self.assertEqual(set(s) , {(c, n, v) for c in ("274079", "274080") for n in (1, 2) for v in "AB"})
        x = s[("274079", 2, "B")]
        self.assertEqual((x["channel"], x["subject"]), ("linkedin", None))
        self.assertEqual(x["body"], "Great to be connected, {first_name} (274079B)")

    def test_pseudo_step_stats(self):
        st = {x["campaign_id"]: x for x in run()["stats"]}
        self.assertEqual((st["274079"]["step_no"], st["274079"]["variant"]), (0, "A"))
        self.assertEqual((st["274079"]["sends"], st["274079"]["replies"], st["274079"]["positive"]), (50, 8, 7))
        self.assertEqual(st["274080"]["positive"], 3)
        self.assertTrue(all(x["meetings"] is None for x in st.values()))

    def test_hash_stable_and_distinct(self):
        h = lambda: [db.content_hash(x["subject"], x["body"]) for x in run()["steps"]]
        self.assertEqual(h(), h())
        self.assertEqual(len(set(h())), 8)

    def test_upsert(self):
        con = db.connect(":memory:")
        db.upsert(con, run())
        self.assertEqual([con.execute(f"select count(*) from {t}").fetchone()[0] for t in ("campaign", "step", "stat")], [2, 8, 2])

    def test_allowlist(self):
        for call in (lambda c: c.post("/campaign/Delete"), lambda c: c.get("/campaign/GetAll"),
                     lambda c: c.post("/campaign/GetCampaignSequence")):
            with self.assertRaises(_http.NotAllowed):
                call(client())

    def test_auth_header(self):
        self.assertEqual(heyreach.make_client("k").headers["X-API-KEY"], "k")

    def test_dry_run_no_network(self):
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")), \
                contextlib.redirect_stdout(io.StringIO()):
            r = heyreach.pull(heyreach.make_client("k", dry_run=True), "2026-09-01", "2026-10-26", "2026-10-26")
        self.assertEqual(r, {"campaigns": [], "steps": [], "stats": []})


if __name__ == "__main__":
    unittest.main()
