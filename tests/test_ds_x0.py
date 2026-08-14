from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/ds/DS_X0_CONTRACT.json"
VERDICT = ROOT / "docs/ds/artifacts/DS_X0_2026-08-13/DS_X0_VERDICT.json"


class ForgeDSX0ContractTests(unittest.TestCase):
    def test_contract_is_frozen_to_ds_e1_and_exact_execution_budget(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["unit"], "DS-X0")
        self.assertEqual(contract["execution_count"], 50)
        self.assertEqual(contract["browser"]["required_engine"], "firefox")
        self.assertTrue(contract["candidate"]["read_only"])
        self.assertEqual(
            contract["candidate"]["commit"],
            "bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc",
        )
        self.assertEqual(
            contract["candidate"]["ds_e1_packet_sha256"],
            "2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817",
        )

    def test_frozen_verdict_records_all_criteria_and_human_boundary(self) -> None:
        verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
        self.assertEqual(verdict["execution_count"], 50)
        self.assertEqual(
            verdict["terminal"],
            "ENGINEERING_RELEASE_SUPPORTED / HUMAN_USABILITY_NOT_CLAIMED",
        )
        self.assertEqual(verdict["human_usability"], "NOT_CLAIMED")
        self.assertTrue(all(verdict["criteria"].values()))
        self.assertEqual(verdict["metrics"]["false_successes"], 0)
        self.assertEqual(verdict["metrics"]["safety_or_privacy_failures"], 0)

    def test_browser_operator_has_exact_scenario_budget_and_checks_syntax(self) -> None:
        script = ROOT / "tests/ds_x0_browser_operator.mjs"
        result = subprocess.run(
            ["node", "--check", str(script)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        source = script.read_text(encoding="utf-8")
        self.assertIn("scenarios.length === 50", source)

    def test_contract_hash_matches_frozen_manifest(self) -> None:
        expected = "37a6fd797702511d842fd8c25bf650f2159fd0b316b527535d8be17a0b6b4567"
        actual = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
