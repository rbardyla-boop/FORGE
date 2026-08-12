from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.f5_support import baseline, git, run_forge
from tests.f6_support import register_failure_fixture
from tests.w1_support import request, request_path


class ForgeW1RequestTests(unittest.TestCase):
    def test_valid_request_is_digest_bound_deterministic_and_product_clean(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            head_before = git(root, "rev-parse", "HEAD").stdout.strip()
            status_before = git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout
            worktrees_before = git(root, "worktree", "list", "--porcelain").stdout
            calc_before = (root / "calc.py").read_bytes()
            result = request(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            live = json.loads(result.stdout)
            stored = json.loads(request_path(root).read_text())
            self.assertEqual(live["request_digest"], stored["request_digest"])
            self.assertEqual(stored["baseline_commit"], head_before)
            self.assertEqual(stored["completion_authority"], "none")
            self.assertEqual(stored["output_protocol"], "forge.builder-trace.v0.1")
            self.assertNotIn("timestamp", stored)
            self.assertNotIn("conversation", stored)
            self.assertTrue(stored["request_digest"].startswith("sha256:"))
            self.assertEqual((root / "calc.py").read_bytes(), calc_before)
            self.assertEqual(git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout, status_before)
            self.assertEqual(git(root, "worktree", "list", "--porcelain").stdout, worktrees_before)
            self.assertEqual(git(root, "rev-parse", "HEAD").stdout.strip(), head_before)

    def test_second_request_is_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            self.assertEqual(request(root).returncode, 0)
            before = request_path(root).read_bytes()
            second = request(root)
            self.assertEqual(second.returncode, 2)
            self.assertIn("already exists", second.stderr)
            self.assertEqual(request_path(root).read_bytes(), before)

    def test_draft_contract_cannot_create_request(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            authority = base / "authority.json"
            created = run_forge(root, "contract", "create", "U-DRAFT", "--file", str(authority))
            self.assertEqual(created.returncode, 0, created.stderr)
            result = run_forge(root, "proposal", "request", "U-DRAFT")
            self.assertEqual(result.returncode, 2)
            self.assertIn("DRAFT", result.stderr)

    def test_tampered_frozen_contract_cannot_create_request(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            path = root / ".forge/contracts/U-0001.json"
            record = json.loads(path.read_text())
            record["authority"]["objective"] = "tampered after freeze"
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            result = request(root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("digest mismatch", result.stderr)
            self.assertFalse(request_path(root).exists())

    def test_non_ready_doctor_cannot_create_request(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            (root / "calc.py").write_text("def broken(:\n")
            git(root, "add", "calc.py"); git(root, "commit", "-qm", "break baseline")
            result = request(root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Doctor prerequisite not ready", result.stderr)
            self.assertFalse(request_path(root).exists())

    def test_corrupt_failure_anchor_authority_cannot_create_request(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            registered, _, _ = register_failure_fixture(root, base, failure_id="FAIL-W1A")
            self.assertEqual(registered.returncode, 0, registered.stderr)
            ref = "refs/forge/failures/registered/FAIL-W1A"
            self.assertEqual(git(root, "update-ref", "-d", ref).returncode, 0)
            result = request(root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("failure-anchor integrity failed", result.stderr)
            self.assertFalse(request_path(root).exists())

    def test_request_is_reconstructable_from_repository_files_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w1-") as tmp:
            base = Path(tmp); root = baseline(base)
            first = request(root)
            self.assertEqual(first.returncode, 0, first.stderr)
            stored = json.loads(request_path(root).read_text())
            contract = json.loads((root / ".forge/contracts/U-0001.json").read_text())
            self.assertEqual(stored["contract_digest"], contract["contract_digest"])
            self.assertEqual(stored["authority"], contract["authority"])
            self.assertEqual(stored["baseline_commit"], git(root, "rev-parse", "HEAD").stdout.strip())
            self.assertEqual(run_forge(root, "contract", "verify", "U-0001").returncode, 0)
            self.assertEqual(run_forge(root, "doctor", "U-0001").returncode, 0)


if __name__ == "__main__":
    unittest.main()
