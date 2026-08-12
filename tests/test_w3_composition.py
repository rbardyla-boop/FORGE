from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from forge_core.codex_adapter import ForgeCodexAdapterError, execute_codex_adapter
from forge_core.containment import _derive_patch, _validate_workspace
from tests.f5_support import git
from tests.w3_support import (
    evidence_path,
    fresh_context,
    proposal_path,
    run_mode,
    submit_workspace_as_w1_proposal,
)


class ForgeW3CompositionTests(unittest.TestCase):
    def test_a23_jsonl_file_change_claim_never_becomes_patch_authority(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "false_file_claim")
            self.assertEqual(code, 0, report)
            with tempfile.TemporaryDirectory(prefix="forge-w3-collector-") as collector:
                _validate_workspace(workspace)
                patch, changed = _derive_patch(root, report["baseline_commit"], workspace, Path(collector))
            self.assertEqual(changed, ["calc.py"])
            self.assertIn(b"safe_divide", patch)
            self.assertNotIn(b"other.txt", patch)

    def test_a24_provider_local_git_tamper_has_no_patch_authority(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "git_tamper")
            self.assertEqual(code, 0, report)
            self.assertFalse((workspace / ".git").exists())
            with tempfile.TemporaryDirectory(prefix="forge-w3-collector-") as collector:
                _validate_workspace(workspace)
                patch, changed = _derive_patch(root, report["baseline_commit"], workspace, Path(collector))
            self.assertEqual(changed, ["calc.py"])
            self.assertIn(b"safe_divide", patch)

    def test_a25_exact_workspace_bytes_feed_w2_trusted_collector(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, report)
            proposal, changed, patch_file, _ = submit_workspace_as_w1_proposal(root, workspace, report, base)
            self.assertEqual(changed, ["calc.py"])
            self.assertIn(b"def safe_divide", patch_file.read_bytes())
            self.assertEqual(proposal["changed_paths"], ["calc.py"])

    def test_a26_successful_codex_shaped_run_reaches_proposal_accepted_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, report)
            proposal, _, _, _ = submit_workspace_as_w1_proposal(root, workspace, report, base)
            self.assertEqual(proposal["proposal_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(proposal["completion_authority"], "none")
            self.assertEqual(proposal["candidate_authority"], "none")
            self.assertTrue(proposal_path(root).is_file())

    def test_a27_no_f4_or_f5_artifact_exists_after_w3_success(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, report)
            submit_workspace_as_w1_proposal(root, workspace, report, base)
            self.assertFalse((root / ".forge/runs/U-0001/attempt-0001").exists())
            self.assertFalse((root / ".forge/final/U-0001").exists())

    def test_a28_operator_tracked_state_is_unchanged(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            before = git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout
            calc_before = (root / "calc.py").read_bytes()
            report, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, report)
            self.assertTrue(report["operator_status_unchanged"])
            self.assertTrue(report["worktree_registry_unchanged"])
            self.assertEqual(git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout, before)
            self.assertEqual((root / "calc.py").read_bytes(), calc_before)

    def test_a29_w1_request_baseline_drift_invalidates_run(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            (root / "drift.txt").write_text("drift\n")
            git(root, "add", "drift.txt")
            git(root, "commit", "-qm", "move operator baseline")
            with self.assertRaises(Exception):
                run_mode(root, workspace, executable, manifest, "good")
            self.assertFalse(evidence_path(root).exists())

    def test_a30_adapter_evidence_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            first, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, first)
            original = evidence_path(root).read_bytes()
            with self.assertRaisesRegex(ForgeCodexAdapterError, "already exists"):
                run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(evidence_path(root).read_bytes(), original)

    def test_a31_no_network_or_credential_bridge_exists_in_w3(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "secret_probe")
            self.assertEqual(code, 0, report)
            self.assertFalse(report["credential_bridge"])
            self.assertFalse(report["network_bridge"])
            self.assertNotIn("CODEX_API_KEY", report["provider_environment_keys"])
            self.assertNotIn("OPENAI_API_KEY", report["provider_environment_keys"])

    def test_a32_terminal_w3_fixture_makes_no_real_remote_codex_request(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, report)
            self.assertFalse(report["real_remote_request"])
            self.assertEqual(Path(report["executable"]["path"]), executable)
            self.assertTrue(str(executable).startswith(str(base)))


if __name__ == "__main__":
    unittest.main()
