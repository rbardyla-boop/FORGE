from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "docs/ds/artifacts/DS_D0_2026-08-13/DS_D0_VERDICT.json"


class ForgeDSD0Tests(unittest.TestCase):
    def test_ds_d0_is_frozen_to_ds_e1_candidate_and_has_no_deploy_write(self) -> None:
        verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
        self.assertEqual(verdict["unit"], "DS-D0")
        self.assertEqual(verdict["candidate"]["candidate_commit"], "bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc")
        self.assertEqual(verdict["deployment_target"]["write_performed"], False)
        self.assertEqual(verdict["human_usability"], "NOT_CLAIMED")

    def test_gate_blocks_for_real_release_boundary_and_operator_gaps(self) -> None:
        verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
        self.assertEqual(verdict["terminal"], "DS_D0_DEPLOYMENT_BLOCKED")
        self.assertTrue(verdict["checks"]["public_surface_matches_302"])
        self.assertFalse(verdict["checks"]["current_head_bound_to_candidate"])
        self.assertFalse(verdict["checks"]["production_rollback_operator_path_proven"])
        self.assertTrue(verdict["checks"]["ds_runtime_not_public_without_explicit_release"])
        self.assertFalse(verdict["checks"]["public_ds_release_boundary_authorized"])
        self.assertTrue(verdict["checks"]["w2_w4_dependency_non_blocking"])

    def test_candidate_local_preflight_and_source_rollback_pass(self) -> None:
        verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
        self.assertTrue(verdict["checks"]["candidate_production_preflight"])
        self.assertTrue(verdict["checks"]["source_rollback_reconstructed"])
        self.assertTrue(verdict["checks"]["ds_e1_ds_x0_ds_h2_evidence_intact"])


if __name__ == "__main__":
    unittest.main()
