from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.f5_support import baseline, correct_calc, git, make_patch, run_forge
from tests.w1_support import (
    bad_behavior_calc,
    good_trace,
    make_good_proposal,
    proposal_dir,
    request,
    request_path,
    submit,
    verify,
)


class ForgeW1IntegrityTests(unittest.TestCase):
    def test_verify_accepts_intact_proposal_and_returns_stored_patch_path(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root, _, _, submitted = make_good_proposal(base)
            result = verify(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["proposal_verified"])
            self.assertEqual(data["proposal_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(data["completion_authority"], "none")
            self.assertEqual(data["candidate_authority"], "none")
            self.assertEqual(data["patch_file"], submitted["patch_file"])
            self.assertTrue((root / data["patch_file"]).is_file())

    def test_baseline_movement_after_request_blocks_submission(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {"calc.py": correct_calc()})
            (root / "marker.txt").write_text("later baseline\n")
            git(root, "add", "marker.txt"); git(root, "commit", "-qm", "move baseline")
            result = submit(root, patch, good_trace(base))
            self.assertEqual(result.returncode, 2)
            self.assertIn("stale", result.stderr)

    def test_baseline_movement_after_submission_blocks_verify(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root, _, _, _ = make_good_proposal(base)
            (root / "marker.txt").write_text("later baseline\n")
            git(root, "add", "marker.txt"); git(root, "commit", "-qm", "move baseline")
            result = verify(root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("stale", result.stderr)

    def test_contract_amendment_after_request_blocks_submission(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {"calc.py": correct_calc()})
            record = json.loads((root / ".forge/contracts/U-0001.json").read_text())
            authority = record["authority"]; authority["objective"] = "amended objective"
            amended = base / "amended-authority.json"
            amended.write_text(json.dumps(authority, indent=2, sort_keys=True) + "\n")
            a = run_forge(root, "contract", "amend", "U-0001", "--file", str(amended), "--reason", "W1 stale request test")
            self.assertEqual(a.returncode, 0, a.stderr)
            self.assertEqual(run_forge(root, "contract", "freeze", "U-0001").returncode, 0)
            result = submit(root, patch, good_trace(base))
            self.assertEqual(result.returncode, 2)
            self.assertIn("stale", result.stderr)

    def test_request_byte_tamper_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            path = request_path(root); record = json.loads(path.read_text())
            record["baseline_commit"] = "0" * 40
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            patch = make_patch(root, base, {"calc.py": correct_calc()})
            result = submit(root, patch, good_trace(base))
            self.assertEqual(result.returncode, 2)
            self.assertIn("request digest mismatch", result.stderr)

    def test_stored_patch_trace_and_metadata_tamper_are_each_detected(self):
        cases = ("PATCH.diff", "TRACE.json", "PROPOSAL.json")
        for filename in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
                base = Path(tmp); root, _, _, _ = make_good_proposal(base)
                path = proposal_dir(root) / filename
                if filename == "PROPOSAL.json":
                    record = json.loads(path.read_text()); record["changed_paths"] = ["other.txt"]
                    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
                elif filename == "TRACE.json":
                    path.write_bytes(path.read_bytes() + b" \n")
                else:
                    path.write_bytes(path.read_bytes() + b"\n")
                result = verify(root)
                self.assertEqual(result.returncode, 2)
                self.assertIn("mismatch", result.stderr)

    def test_second_submission_is_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root, patch, trace, _ = make_good_proposal(base)
            before = {p.name: p.read_bytes() for p in proposal_dir(root).iterdir() if p.is_file()}
            second = submit(root, patch, trace)
            self.assertEqual(second.returncode, 2)
            self.assertIn("already exists", second.stderr)
            after = {p.name: p.read_bytes() for p in proposal_dir(root).iterdir() if p.is_file()}
            self.assertEqual(after, before)

    def test_good_stored_patch_handoff_reaches_foundation_candidate_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root, _, _, _ = make_good_proposal(base)
            verified = json.loads(verify(root).stdout)
            stored_patch = root / verified["patch_file"]
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(stored_patch))
            self.assertEqual(result.returncode, 0, result.stderr)
            candidate = json.loads(result.stdout)
            self.assertEqual(candidate["terminal_state"], "CANDIDATE_VERIFIED")
            self.assertEqual(verified["completion_authority"], "none")
            self.assertFalse((root / ".forge/runs/U-0001/attempt-0001/FINAL_EVALUATION.json").exists())

    def test_behaviorally_bad_accepted_proposal_is_rejected_by_foundation_f4(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {"calc.py": bad_behavior_calc()}, "bad-behavior.patch")
            trace = good_trace(base, summary="PASS according to untrusted provider")
            accepted = submit(root, patch, trace)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            stored = root / json.loads(accepted.stdout)["patch_file"]
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(stored))
            self.assertEqual(result.returncode, 3, result.stderr)
            candidate = json.loads(result.stdout)
            self.assertEqual(candidate["terminal_state"], "REPAIR_REQUIRED")

    def test_cli_adds_only_proposal_not_execution_or_release_authority(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            root = Path(tmp)
            help_result = run_forge(root, "--help")
            self.assertEqual(help_result.returncode, 0)
            text = help_result.stdout.lower()
            self.assertIn("proposal", text)
            for forbidden in ("build", "builder", "merge", "deploy", "swarm", "autonomous", "codex", "claude"):
                self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
