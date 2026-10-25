import unittest

import propose


class GuardTest(unittest.TestCase):
    def test_disallowed_paths(self):
        paths = ["cold-email/copy-frameworks/SKILL.md", "cold-email/copy-frameworks/PLAYBOOK.md",
                 "reports/2026-10-26-copy-learnings.md", "learnings/2026-10.md",
                 "icp-research/icp-matrix-builder/SKILL.md", "CLAUDE.md", "flywheel/db.py"]
        self.assertEqual(propose.disallowed(paths),
                         ["icp-research/icp-matrix-builder/SKILL.md", "CLAUDE.md", "flywheel/db.py"])

    def test_frontmatter_check_on_real_skill(self):
        self.assertTrue(propose.frontmatter_ok("cold-email/copy-frameworks/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
