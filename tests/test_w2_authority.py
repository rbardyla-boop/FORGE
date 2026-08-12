from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from forge_core.containment import ForgeContainmentError, execute_provider
from tests.f5_support import git, run_forge
from tests.f6_support import register_failure_fixture
from tests.w2_support import (
    execute,
    execution_path,
    image_id,
    proposal_path,
    read_json,
    setup_request,
    stored_patch,
)


class ForgeW2AuthorityTests(unittest.TestCase):
    def test_mutable_image_tag_is_not_execution_authority(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            with self.assertRaisesRegex(ForgeContainmentError, "immutable local Docker image ID"):
                execute_provider(root, "U-0001", "w2-fixture:latest", ["good"], adapter_id="mutable-tag")
            self.assertFalse(execution_path(root).exists())

    def test_containment_unavailable_has_no_ordinary_subprocess_fallback(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            with mock_patch(
                "forge_core.containment._docker",
                side_effect=ForgeContainmentError("CONTAINMENT_UNAVAILABLE: forced fixture"),
            ):
                with self.assertRaisesRegex(ForgeContainmentError, "CONTAINMENT_UNAVAILABLE"):
                    execute_provider(root, "U-0001", image_id(), ["good"], adapter_id="no-fallback")
            self.assertFalse(proposal_path(root).exists())
            self.assertFalse(execution_path(root).exists())

    def test_baseline_movement_after_request_blocks_provider_execution(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            (root / "later.txt").write_text("new baseline\n")
            git(root, "add", "later.txt"); git(root, "commit", "-qm", "move request baseline")
            with self.assertRaisesRegex(Exception, "stale"):
                execute(root, "good")
            self.assertFalse(execution_path(root).exists())

    def test_contract_amendment_after_request_blocks_provider_execution(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            record = json.loads((root / ".forge/contracts/U-0001.json").read_text())
            authority = record["authority"]
            authority["objective"] = "amended after W1 request"
            source = base / "amended.json"
            source.write_text(json.dumps(authority, indent=2, sort_keys=True) + "\n")
            amended = run_forge(root, "contract", "amend", "U-0001", "--file", str(source), "--reason", "W2 stale request")
            self.assertEqual(amended.returncode, 0, amended.stderr)
            self.assertEqual(run_forge(root, "contract", "freeze", "U-0001").returncode, 0)
            with self.assertRaisesRegex(Exception, "stale"):
                execute(root, "good")

    def test_corrupt_failure_anchor_after_request_blocks_execution(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            registered, _, _ = register_failure_fixture(root, base, failure_id="FAIL-W2A")
            self.assertEqual(registered.returncode, 0, registered.stderr)
            ref = "refs/forge/failures/registered/FAIL-W2A"
            self.assertEqual(git(root, "update-ref", "-d", ref).returncode, 0)
            with self.assertRaisesRegex(Exception, "failure"):
                execute(root, "good")
            self.assertFalse(execution_path(root).exists())

    def test_nonzero_provider_is_rejected_and_evidence_is_persisted(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "nonzero")
            self.assertEqual(code, 3)
            self.assertEqual(report["execution_state"], "PROVIDER_REJECTED")
            self.assertEqual(report["reason_code"], "PROVIDER_NONZERO")
            self.assertEqual(report["provider_exit_code"], 9)
            self.assertTrue(execution_path(root).is_file())
            self.assertFalse(proposal_path(root).exists())

    def test_hanging_provider_is_killed_rejected_and_does_not_leave_container(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "hang", timeout_seconds=1.0)
            self.assertEqual(code, 3)
            self.assertTrue(report["provider_timed_out"])
            self.assertEqual(report["reason_code"], "PROVIDER_TIMEOUT")
            docker_ps = __import__("subprocess").run(
                ["docker", "ps", "--format", "{{.Names}}"],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertNotIn("forge-w2-", docker_ps.stdout)

    def test_execution_evidence_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "good")
            self.assertEqual(code, 0, report)
            before = execution_path(root).read_bytes()
            with self.assertRaisesRegex(ForgeContainmentError, "already exists"):
                execute(root, "good")
            self.assertEqual(execution_path(root).read_bytes(), before)

    def test_bad_behavior_can_be_proposal_accepted_but_foundation_rejects_it(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "bad_behavior")
            self.assertEqual(code, 0, report)
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")
            proposal = read_json(proposal_path(root))
            self.assertEqual(proposal["completion_authority"], "none")
            stored = stored_patch(root)
            lifecycle = run_forge(root, "unit", "run", "U-0001", "--patch", str(stored))
            self.assertEqual(lifecycle.returncode, 3, lifecycle.stderr)
            self.assertEqual(json.loads(lifecycle.stdout)["terminal_state"], "REPAIR_REQUIRED")

    def test_good_provider_proposal_requires_explicit_foundation_handoff_and_stops_at_candidate(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "good")
            self.assertEqual(code, 0, report)
            self.assertFalse((root / ".forge/runs/U-0001/attempt-0001").exists())
            lifecycle = run_forge(root, "unit", "run", "U-0001", "--patch", str(stored_patch(root)))
            self.assertEqual(lifecycle.returncode, 0, lifecycle.stderr)
            candidate = json.loads(lifecycle.stdout)
            self.assertEqual(candidate["terminal_state"], "CANDIDATE_VERIFIED")
            self.assertFalse((root / ".forge/runs/U-0001/attempt-0001/FINAL_EVALUATION.json").exists())

    def test_provider_pass_merge_deploy_prose_remains_zero_authority(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "bad_behavior")
            self.assertEqual(code, 0, report)
            proposal = read_json(proposal_path(root))
            self.assertEqual(proposal["completion_authority"], "none")
            self.assertEqual(proposal["candidate_authority"], "none")
            self.assertFalse(proposal["checks_executed_by_forge"])

    def test_execution_evidence_binds_immutable_image_profile_and_w1_proposal(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "good")
            self.assertEqual(code, 0, report)
            evidence = read_json(execution_path(root))
            self.assertEqual(evidence["image_id"], image_id())
            self.assertTrue(evidence["image_id"].startswith("sha256:"))
            self.assertEqual(evidence["backend"], "linux-docker-v0.1")
            self.assertEqual(evidence["proposal_digest"], read_json(proposal_path(root))["proposal_digest"])
            self.assertEqual(evidence["completion_authority"], "none")
            joined = " ".join(evidence["containment_profile"])
            for token in ("--network none", "--read-only", "--cap-drop ALL", "--security-opt no-new-privileges"):
                self.assertIn(token, joined)

    def test_w2_adds_no_real_provider_or_release_cli_surface(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = Path(tmp)
            help_result = run_forge(root, "--help")
            self.assertEqual(help_result.returncode, 0)
            text = help_result.stdout.lower()
            self.assertIn("proposal", text)
            for forbidden in ("containment", "provider", "codex", "claude", "merge", "deploy", "swarm", "autonomous"):
                self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
