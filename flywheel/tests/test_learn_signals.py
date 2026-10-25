import random
import unittest

import db
import learn_signals as ls
import score_signals as ss


def seed(con, with_sig_pos, with_sig_n, base_pos, base_n, sig_type="funding", event_date="2026-10-10"):
    leads = []
    for i in range(with_sig_n):
        leads.append({"tool": "t", "campaign_id": "c", "email": f"p{i}@hot{i % 40}.com", "status": "x",
                      "replied": 1 if i < with_sig_pos + 5 else 0, "positive": 1 if i < with_sig_pos else 0, "as_of": "2026-10-26"})
    for i in range(base_n):
        leads.append({"tool": "t", "campaign_id": "c", "email": f"q{i}@cold{i % 200}.com", "status": "x",
                      "replied": 1 if i < base_pos + 5 else 0, "positive": 1 if i < base_pos else 0, "as_of": "2026-10-26"})
    signals = [{"domain": f"hot{j}.com", "type": sig_type, "party": "third", "event_date": event_date} for j in range(40)]
    db.upsert(con, {"leads": leads, "signals": signals})


class LearnSignalsTest(unittest.TestCase):
    def setUp(self):
        self.con, self.cfg, self.rng = db.connect(":memory:"), ss.load_config(), random.Random(0)

    def run_eval(self):
        leads = ls.lead_rows(self.con, "2026-08-01", "2026-10-26")
        return ls.evaluate(leads, ls.active_domains(self.con, self.cfg, "2026-08-01", "2026-10-26"), self.rng)

    def test_raise_when_signal_lifts(self):
        seed(self.con, with_sig_pos=40, with_sig_n=400, base_pos=20, base_n=1000)
        base, res = self.run_eval()
        self.assertEqual(res[0]["type"], "funding")
        self.assertEqual(res[0]["verdict"], "raise")
        self.assertGreater(res[0]["lift"], 1.3)

    def test_hold_when_no_difference(self):
        seed(self.con, 12, 400, 30, 1000)
        _, res = self.run_eval()
        self.assertEqual(res[0]["verdict"], "hold")

    def test_insufficient_under_min_sample(self):
        seed(self.con, 10, 50, 30, 1000)
        _, res = self.run_eval()
        self.assertEqual(res[0]["verdict"], "insufficient")

    def test_stale_signal_not_credited_and_freemail_excluded(self):
        seed(self.con, 40, 400, 20, 1000, event_date="2026-01-01")   # funding window is 0-28 days: stale
        db.upsert(self.con, {"leads": [{"tool": "t", "campaign_id": "c", "email": "x@gmail.com", "status": "x", "positive": 1, "as_of": "2026-10-26"}]})
        leads = ls.lead_rows(self.con, "2026-08-01", "2026-10-26")
        self.assertFalse(any(l["domain"] == "gmail.com" for l in leads))
        self.assertEqual(ls.active_domains(self.con, self.cfg, "2026-08-01", "2026-10-26"), {})

    def test_report_renders(self):
        seed(self.con, 40, 400, 20, 1000)
        base, res = self.run_eval()
        text = ls.render(base, res, "2026-10-26", "2026-08-01", "2026-10-26", self.rng)
        self.assertIn("**raise**", text)
        self.assertIn("funding", text)


if __name__ == "__main__":
    unittest.main()
