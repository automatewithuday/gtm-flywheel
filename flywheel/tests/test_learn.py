import random
import unittest

import db
import learn


def seed(con, cells):
    """cells: list of (campaign, variant, archetype, sends, positive)."""
    rows = {"campaigns": [], "steps": [], "stats": []}
    for i, (camp, var, arch, sends, pos) in enumerate(cells):
        rows["campaigns"].append({"tool": "t", "id": camp, "name": camp})
        rows["steps"].append({"tool": "t", "campaign_id": camp, "step_no": 1, "variant": var,
                              "subject": f"s{i}", "body": f"b{i}"})
        rows["stats"].append({"tool": "t", "campaign_id": camp, "step_no": 1, "variant": var, "as_of": "2026-10-26",
                              "sends": sends, "replies": pos + 5, "positive": pos})
    db.upsert(con, rows)
    for i, (camp, var, arch, *_rest) in enumerate(cells):
        h = db.content_hash(f"s{i}", f"b{i}")
        con.execute("INSERT INTO classification (content_hash, archetype, word_count) VALUES (?,?,?)", (h, arch, 80))
    con.commit()


class LearnTest(unittest.TestCase):
    def setUp(self):
        self.con = db.connect(":memory:")
        self.rng = random.Random(0)

    def test_clear_winner(self):
        seed(self.con, [("c1", "A", "Observation", 400, 40), ("c1", "B", "Benchmark", 400, 12)])
        agg = learn.aggregate(learn.latest_rows(self.con), {})
        ranked, winner = learn.rank(agg["archetype"], self.rng)
        self.assertEqual(ranked[0][0][1], "Observation")
        self.assertIsNotNone(winner)
        self.assertEqual(winner[0][1], "Observation")

    def test_no_winner_under_min_sample(self):
        seed(self.con, [("c1", "A", "Observation", 50, 10), ("c1", "B", "Benchmark", 50, 1)])
        agg = learn.aggregate(learn.latest_rows(self.con), {})
        ranked, winner = learn.rank(agg["archetype"], self.rng)
        self.assertEqual(ranked, [])
        self.assertIsNone(winner)

    def test_no_winner_when_close(self):
        seed(self.con, [("c1", "A", "Observation", 400, 20), ("c1", "B", "Benchmark", 400, 18)])
        agg = learn.aggregate(learn.latest_rows(self.con), {})
        _, winner = learn.rank(agg["archetype"], self.rng)
        self.assertIsNone(winner)

    def test_mixed_tools_use_positive_basis_only(self):
        seed(self.con, [("c1", "A", "Observation", 400, 40)])
        # a second tool with no positive label joins the same archetype cell
        db.upsert(self.con, {"campaigns": [{"tool": "u", "id": "c9", "name": "c9"}],
                             "steps": [{"tool": "u", "campaign_id": "c9", "step_no": 1, "variant": "A", "subject": "s0", "body": "b0"}],
                             "stats": [{"tool": "u", "campaign_id": "c9", "step_no": 1, "variant": "A", "as_of": "2026-10-26",
                                        "sends": 400, "replies": 4, "positive": None}]})
        cell = learn.aggregate(learn.latest_rows(self.con), {})["archetype"][("*", "Observation")]
        self.assertTrue(cell.use_positive)
        self.assertEqual(cell.basis, 400)          # not 800
        self.assertAlmostEqual(cell.rate, 0.10)

    def test_reply_rate_cell_never_beats_positive_rate_cells(self):
        seed(self.con, [("c1", "A", "Observation", 400, 12), ("c1", "B", "Benchmark", 400, 10)])
        db.upsert(self.con, {"campaigns": [{"tool": "u", "id": "c9", "name": "c9"}],
                             "steps": [{"tool": "u", "campaign_id": "c9", "step_no": 1, "variant": "A", "subject": "x", "body": "y"}],
                             "stats": [{"tool": "u", "campaign_id": "c9", "step_no": 1, "variant": "A", "as_of": "2026-10-26",
                                        "sends": 400, "replies": 60, "positive": None}]})
        self.con.execute("INSERT INTO classification (content_hash, archetype, word_count) VALUES (?,?,?)",
                         (db.content_hash("x", "y"), "Referral Ceiling", 80))
        self.con.commit()
        ranked, _ = learn.rank(learn.aggregate(learn.latest_rows(self.con), {})["archetype"], self.rng)
        self.assertNotIn("Referral Ceiling", [k[1] for k, _ in ranked])
        self.assertEqual(len(ranked), 2)

    def test_latest_snapshot_only_and_report_renders(self):
        seed(self.con, [("c1", "A", "Observation", 400, 40)])
        db.upsert(self.con, {"stats": [{"tool": "t", "campaign_id": "c1", "step_no": 1, "variant": "A",
                                        "as_of": "2026-11-02", "sends": 800, "replies": 90, "positive": 80}]})
        rows = learn.latest_rows(self.con)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sends"], 800)
        agg = learn.aggregate(rows, {})
        text = learn.render_report(agg, self.rng, "2026-11-02", len(rows))
        self.assertIn("Observation", text)
        self.assertIn("10.0%", text)
        pb = learn.render_playbook(agg, self.rng, "2026-11-02", len(rows), 1)
        self.assertIn("60-90 words", pb)


if __name__ == "__main__":
    unittest.main()
