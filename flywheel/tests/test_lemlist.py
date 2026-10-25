import contextlib, io, json, sqlite3, unittest
from pathlib import Path
from unittest import mock

import db
from adapters import _http, lemlist

FX = Path(__file__).parent / "fixtures" / "lemlist"
load = lambda n: json.loads((FX / n).read_text())


class Fake(_http.Client):
    """Real allowlist + URL building; only the network send is replaced by fixtures."""
    def _send(self, method, url, body, retries=3):
        if url.endswith("/api/campaigns?version=v2&offset=0&limit=100"):
            return load("campaigns.json")
        if "/sequences/" in url and url.endswith("/ab-test"):
            return load(f"ab_test_{url.split('/steps/')[1].split('/')[0]}.json")
        if url.endswith("/sequences"):
            return load(f"sequences_{url.split('/campaigns/')[1].split('/')[0]}.json")
        if "/stats?" in url:
            cid = url.split("/campaigns/")[1].split("/")[0]
            return load(f"stats_{cid}_{'B' if 'ABSelected=B' in url else 'A'}.json")
        raise AssertionError(url)


def client():
    return Fake("lemlist", lemlist.BASE_URL, lemlist.ALLOW)


def run():
    return lemlist.pull(client(), "2026-09-01", "2026-10-26", "2026-10-26")


class T(unittest.TestCase):
    def test_counts_and_variants(self):
        r = run()
        self.assertEqual(len(r["campaigns"]), 2)
        self.assertEqual(len(r["steps"]), 6)   # per campaign: step1 A, step2 A, step2 B
        self.assertEqual(len(r["stats"]), 8)   # per campaign: 2 A + 1 B + pseudo
        s = {(x["campaign_id"], x["step_no"], x["variant"]): x for x in r["steps"]}
        k = "cam_7Hq2xKd9"
        self.assertEqual({v for (c, n, v) in s if c == k and n == 2}, {"A", "B"})
        self.assertEqual(s[(k, 1, "A")]["channel"], "linkedin")
        self.assertEqual(s[(k, 2, "A")]["channel"], "email")
        self.assertEqual(s[(k, 2, "B")]["subject"], "Idea for {{companyName}} (1B)")
        self.assertEqual(s[(k, 2, "A")]["body"], "Hi {{firstName}},\n\nWorth a chat about outbound?\nThanks & best,\nUday")

    def test_pseudo_step_and_variant_stats(self):
        st = {(x["campaign_id"], x["step_no"], x["variant"]): x for x in run()["stats"]}
        p = st[("cam_9Lm4pTz3", 0, "A")]
        self.assertEqual((p["positive"], p["meetings"], p["sends"], p["replies"]), (6, 2, 318, 22))
        self.assertEqual(st[("cam_7Hq2xKd9", 1, "A")]["sends"], 120)   # linkedin: 'invited'
        self.assertEqual(st[("cam_7Hq2xKd9", 2, "B")]["replies"], 8)
        self.assertIsNone(st[("cam_7Hq2xKd9", 2, "A")]["positive"])

    def test_hash_stable_and_distinct(self):
        a, b = run()["steps"], run()["steps"]
        h = lambda rows: [db.content_hash(x["subject"], x["body"]) for x in rows]
        self.assertEqual(h(a), h(b))
        self.assertEqual(len(set(h(a))), len(a))

    def test_upsert(self):
        con = db.connect(":memory:")
        db.upsert(con, run())
        self.assertEqual(con.execute("select count(*) from step").fetchone()[0], 6)
        self.assertEqual(con.execute("select count(*) from stat").fetchone()[0], 8)

    def test_allowlist(self):
        with self.assertRaises(_http.NotAllowed):
            client().post("/campaigns")
        with self.assertRaises(_http.NotAllowed):
            client().get("/campaigns/{cid}", cid="x")

    def test_auth_header(self):
        self.assertEqual(lemlist.make_client("k").headers["Authorization"], "Basic Oms=")

    def test_dry_run_no_network(self):
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")), \
                contextlib.redirect_stdout(io.StringIO()):
            c = lemlist.make_client("k", dry_run=True)
            r = lemlist.pull(c, "2026-09-01", "2026-10-26", "2026-10-26")
        self.assertEqual(r, {"campaigns": [], "steps": [], "stats": []})


if __name__ == "__main__":
    unittest.main()
