import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "docs/ds/artifacts/DS_D2_2026-08-13/DS_D2_PUBLIC_REPLAY_VERDICT.json"


class FreshDSD2Tests(unittest.TestCase):
    def test_public_replay_terminal_pass(self):
        verdict = json.loads(VERDICT.read_text())
        self.assertEqual(verdict["unit"], "DS-D2")
        self.assertEqual(verdict["terminal"], "DS_D2_PUBLIC_REPLAY_PASS")
        self.assertEqual(verdict["production"]["version_id"], "53c7c021-96a5-495b-b622-16bd1b368967")
        self.assertFalse(verdict["release"]["ds00_public"])
        self.assertEqual(verdict["human_usability"], "NOT_CLAIMED")

    def test_all_public_replay_checks_pass(self):
        verdict = json.loads(VERDICT.read_text())
        self.assertTrue(all(verdict["checks"].values()), verdict["blocking_reasons"])


if __name__ == "__main__":
    unittest.main()
