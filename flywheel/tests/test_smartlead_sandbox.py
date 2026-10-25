"""Runs adapters/smartlead.py over real HTTP against sandbox/smartlead_mock.py. No account, no network beyond localhost."""
import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

import db
import pull_outcomes
from adapters import _http, smartlead
from sandbox import smartlead_mock
from tests import test_smartlead as fixture_test


class SandboxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = smartlead_mock.serve(port=0, api_key="sandbox-key", rate_limit_every=4, echo=False)
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def client(self, key="sandbox-key"):
        c = smartlead.make_client(key, base_url=self.srv.base_url)
        c.min_interval, c.backoff = 0, 0.01          # fast in tests; production keeps 1 req/s and 5 s backoff
        return c

    def test_http_pull_matches_fixture_pull(self):
        over_http = smartlead.pull(self.client(), "2026-09-01T00:00:00Z", "2026-10-26T00:00:00Z", "2026-10-26")
        in_memory = smartlead.pull(fixture_test.FakeClient(), "2026-09-01T00:00:00Z", "2026-10-26T00:00:00Z", "2026-10-26")
        for k in ("campaigns", "steps", "stats", "leads"):
            self.assertEqual(len(over_http[k]), len(in_memory[k]), k)
        self.assertEqual(sorted(json.dumps(r, sort_keys=True) for r in over_http["stats"]),
                         sorted(json.dumps(r, sort_keys=True) for r in in_memory["stats"]))
        con = db.connect(":memory:")
        db.upsert(con, over_http)
        self.assertEqual(con.execute("select count(*) from lead_outcome").fetchone()[0], len(over_http["leads"]))
        self.assertEqual(con.execute("select count(*) from lead_outcome where email_hash like '%@%'").fetchone()[0], 0)

    def test_server_saw_only_authenticated_gets_and_retry_survived_429(self):
        n0 = len(self.srv.log)
        smartlead.pull(self.client(), "2026-09-01T00:00:00Z", "2026-10-26T00:00:00Z", "2026-10-26")
        log = self.srv.log[n0:]
        self.assertTrue(log)
        self.assertTrue(all(e["method"] == "GET" for e in log))
        self.assertTrue(all(e["query"].get("api_key") == "***" for e in log if e["status"] != 429))
        self.assertTrue(any(e["status"] == 429 for e in log), "rate limit was never injected")
        self.assertTrue(all(e["status"] in (200, 429) for e in log))
        self.assertEqual(log[-1]["status"], 200)

    def test_write_is_refused_client_side_before_any_request(self):
        n0 = len(self.srv.log)
        with self.assertRaises(_http.NotAllowed):
            self.client().post("/campaigns/")
        with self.assertRaises(_http.NotAllowed):
            self.client().get("/campaigns/{id}/leads-export", id=101)
        self.assertEqual(len(self.srv.log), n0)

    def test_write_is_refused_server_side_too(self):
        req = urllib.request.Request(self.srv.base_url + "/campaigns/?api_key=sandbox-key", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(cm.exception.code, 405)
        self.assertEqual(self.srv.log[-1]["note"], "WRITE ATTEMPT refused by sandbox")

    def test_bad_key_is_401(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.client("wrong").get("/campaigns/")
        self.assertEqual(cm.exception.code, 401)

    def test_pull_outcomes_cli_uses_sandbox_env(self):
        dbp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "flywheel-sandbox-test.sqlite")
        if os.path.exists(dbp):
            os.remove(dbp)
        env = {"SMARTLEAD_API_KEY": "sandbox-key", "SMARTLEAD_BASE_URL": self.srv.base_url}
        with mock.patch.dict(os.environ, env), mock.patch.object(_http.Client, "__init__", _fast_init):
            pull_outcomes.main(["--tools", "smartlead", "--db", dbp])
        con = db.connect(dbp)
        self.assertGreater(con.execute("select count(*) from stat").fetchone()[0], 0)
        self.assertGreater(con.execute("select count(*) from lead_outcome").fetchone()[0], 0)
        os.remove(dbp)


_orig_init = _http.Client.__init__


def _fast_init(self, *a, **kw):
    kw["min_interval"], kw["backoff"] = 0, 0.01
    _orig_init(self, *a, **kw)


if __name__ == "__main__":
    unittest.main()
