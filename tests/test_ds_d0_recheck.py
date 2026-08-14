import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "docs/ds/artifacts/DS_D0_REEVALUATION_2026-08-13/DS_D0_REEVALUATION_VERDICT.json"


class FreshDSD0Tests(unittest.TestCase):
    def test_fresh_gate_authorizes_only_frozen_public_subset(self):
        verdict = json.loads(VERDICT.read_text())
        self.assertEqual(verdict["unit"], "DS-D0")
        self.assertTrue(verdict["recheck"])
        self.assertEqual(verdict["terminal"], "DS_D0_DEPLOYMENT_AUTHORIZED")
        self.assertEqual(verdict["release_choice"], "B")
        self.assertTrue(verdict["checks"]["release_choice_B_explicit"])
        self.assertEqual(verdict["deployment_target"]["write_performed"], False)
        self.assertEqual(verdict["human_usability"], "NOT_CLAIMED")

    def test_all_fresh_checks_pass(self):
        verdict = json.loads(VERDICT.read_text())
        self.assertTrue(all(verdict["checks"].values()), verdict["blocking_reasons"])


if __name__ == "__main__":
    unittest.main()
