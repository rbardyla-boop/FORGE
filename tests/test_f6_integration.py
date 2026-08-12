from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.f6_support import make_f4_failure_project, patch_file, run_forge
from tests.f4_support import basic_repo, create_contract, init_project


class ForgeF6IntegrationTests(unittest.TestCase):
    def test_f4_without_locked_failures_still_yields_candidate_verified(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [{"id": "CHK_001", "required": True, "argv": ["python3", "check.py"]}], allowed=["feature.txt"])
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "CANDIDATE_VERIFIED")
            self.assertEqual(report["locked_regressions"], [])

    def test_locked_passing_regression_is_automatically_inherited(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root, _ = make_f4_failure_project(base, accepted_feature_values=("off", "on"))
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "CANDIDATE_VERIFIED")
            self.assertEqual(report["reason_code"], "ALL_REQUIRED_CHECKS_AND_LOCKED_REGRESSIONS_PASS")
            self.assertEqual(len(report["locked_regressions"]), 1)
            self.assertTrue(report["locked_regressions"][0]["regression_passed"])

    def test_locked_regression_failure_blocks_candidate_verified(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root, _ = make_f4_failure_project(base, accepted_feature_values=("off",))
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["reason_code"], "LOCKED_REGRESSION_FAILED")
            self.assertEqual(len(report["locked_regressions"]), 1)
            self.assertFalse(report["locked_regressions"][0]["regression_passed"])

    def test_locked_evaluator_mutation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root, _ = make_f4_failure_project(
                base,
                accepted_feature_values=("off", "on"),
                mutate_when="on",
            )
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["reason_code"], "LOCKED_REGRESSION_FAILED")
            replay = report["locked_regressions"][0]
            self.assertTrue(replay["result"]["candidate_mutated"])


if __name__ == "__main__":
    unittest.main()
