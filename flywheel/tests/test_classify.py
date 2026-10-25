import unittest

import classify_copy


class TaxonomyTest(unittest.TestCase):
    def test_labels_parse_from_skill_files(self):
        tax = classify_copy.taxonomy()
        self.assertIn("The Observation", tax["archetype"])
        self.assertEqual(len(tax["archetype"]), 7)                  # 6 archetypes + Other
        self.assertIn("Signal observation", tax["opener"])
        self.assertIn("Low-friction question", tax["cta_pattern"])
        self.assertIn("{{company}} + topic", tax["subject_formula"])
        s = classify_copy.schema(tax)
        self.assertEqual(s["required"], ["archetype", "subject_formula", "opener", "cta_pattern"])


if __name__ == "__main__":
    unittest.main()
