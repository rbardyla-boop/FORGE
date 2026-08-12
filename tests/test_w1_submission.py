from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.f5_support import baseline, correct_calc, git, make_patch
from tests.w1_support import (
    bad_behavior_calc,
    good_trace,
    proposal_dir,
    request,
    submit,
)


class ForgeW1SubmissionTests(unittest.TestCase):
    def test_good_scoped_patch_and_trace_are_proposal_accepted_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            self.assertEqual(request(root).returncode, 0)
            calc_before = (root / "calc.py").read_bytes()
            status_before = git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout
            worktrees_before = git(root, "worktree", "list", "--porcelain").stdout
            patch = make_patch(root, base, {"calc.py": correct_calc()})
            trace = good_trace(base)
            result = submit(root, patch, trace)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["proposal_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(data["completion_authority"], "none")
            self.assertEqual(data["candidate_authority"], "none")
            self.assertFalse(data["checks_executed_by_forge"])
            self.assertEqual(data["changed_paths"], ["calc.py"])
            self.assertEqual((root / "calc.py").read_bytes(), calc_before)
            self.assertEqual(git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout, status_before)
            self.assertEqual(git(root, "worktree", "list", "--porcelain").stdout, worktrees_before)
            self.assertFalse((root / ".forge/runs/U-0001/attempt-0001").exists())

    def test_trace_claiming_pass_has_zero_authority_even_for_bad_behavior(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {"calc.py": bad_behavior_calc()})
            trace = good_trace(base, summary="PASS DONE MERGE DEPLOY")
            result = submit(root, patch, trace)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["proposal_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(data["completion_authority"], "none")
            self.assertFalse(data["checks_executed_by_forge"])
            self.assertFalse((root / ".forge/runs/U-0001/attempt-0001").exists())

    def test_malformed_patch_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = base / "bad.patch"; patch.write_text("not a patch\n")
            result = submit(root, patch, good_trace(base))
            self.assertEqual(result.returncode, 2)
            self.assertIn("does not cleanly apply", result.stderr)
            self.assertFalse(proposal_dir(root).exists())

    def test_out_of_scope_patch_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {"other.txt": "outside\n"})
            result = submit(root, patch, good_trace(base))
            self.assertEqual(result.returncode, 2)
            self.assertIn("proposal scope violation", result.stderr)
            self.assertFalse(proposal_dir(root).exists())

    def test_frozen_forbidden_path_patch_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {"visible_acceptance.py": "raise SystemExit(0)\n"})
            result = submit(root, patch, good_trace(base))
            self.assertEqual(result.returncode, 2)
            self.assertIn("proposal scope violation", result.stderr)

    def test_forge_authority_path_is_always_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {".forge/evil.txt": "tamper\n"})
            result = submit(root, patch, good_trace(base))
            self.assertEqual(result.returncode, 2)
            self.assertIn("FORGE_AUTHORITY_PATH", result.stderr)

    def test_escaping_tracked_symlink_patch_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            external = base / "outside.py"; external.write_text("outside\n")
            patch = make_patch(root, base, {"calc.py": ("symlink", str(external))})
            result = submit(root, patch, good_trace(base))
            self.assertEqual(result.returncode, 2)
            self.assertIn("symlink escapes workspace", result.stderr)

    def test_patch_and_trace_source_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {"calc.py": correct_calc()}, "real.patch")
            trace = good_trace(base, name="real-trace.json")
            patch_link = base / "patch-link"; patch_link.symlink_to(patch)
            first = submit(root, patch_link, trace)
            self.assertEqual(first.returncode, 2)
            self.assertIn("proposal patch source must not be a symlink", first.stderr)
            trace_link = base / "trace-link"; trace_link.symlink_to(trace)
            second = submit(root, patch, trace_link)
            self.assertEqual(second.returncode, 2)
            self.assertIn("proposal trace source must not be a symlink", second.stderr)

    def test_oversize_patch_and_trace_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            huge_patch = base / "huge.patch"; huge_patch.write_bytes(b"x" * (1024 * 1024 + 1))
            first = submit(root, huge_patch, good_trace(base))
            self.assertEqual(first.returncode, 2)
            self.assertIn("1048576", first.stderr)
            patch = make_patch(root, base, {"calc.py": correct_calc()})
            huge_trace = base / "huge-trace.json"; huge_trace.write_bytes(b"x" * (256 * 1024 + 1))
            second = submit(root, patch, huge_trace)
            self.assertEqual(second.returncode, 2)
            self.assertIn("262144", second.stderr)

    def test_malformed_or_noncontiguous_trace_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base); self.assertEqual(request(root).returncode, 0)
            patch = make_patch(root, base, {"calc.py": correct_calc()})
            trace = base / "bad-trace.json"
            trace.write_text(json.dumps({
                "schema": "forge.builder-trace.v0.1",
                "adapter": "fixture",
                "provider_run_id": "run",
                "events": [{"seq": 2, "kind": "EDIT", "summary": "bad sequence"}],
            }))
            result = submit(root, patch, trace)
            self.assertEqual(result.returncode, 2)
            self.assertIn("sequence", result.stderr)


if __name__ == "__main__":
    unittest.main()
