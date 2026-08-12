from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.w2_support import execute, proposal_path, read_json, setup_request, stored_patch, stored_trace


class ForgeW2WorkspaceOutputTests(unittest.TestCase):
    def test_provider_local_git_tamper_does_not_change_harness_patch_authority(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp1, tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp2:
            root_good = setup_request(Path(tmp1))
            report_good, code_good = execute(root_good, "good")
            self.assertEqual(code_good, 0, report_good)
            patch_good = stored_patch(root_good).read_bytes()

            root_tamper = setup_request(Path(tmp2))
            report_tamper, code_tamper = execute(root_tamper, "git_tamper")
            self.assertEqual(code_tamper, 0, report_tamper)
            patch_tamper = stored_patch(root_tamper).read_bytes()
            self.assertEqual(patch_tamper, patch_good)
            self.assertEqual(report_tamper["patch_sha256"], report_good["patch_sha256"])

    def test_provider_created_forge_authority_path_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "forge_path")
            self.assertEqual(code, 3)
            self.assertEqual(report["execution_state"], "PROVIDER_REJECTED")
            self.assertIn("forbidden .forge", report["detail"])
            self.assertFalse(proposal_path(root).exists())

    def test_workspace_escape_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "escape_symlink")
            self.assertEqual(code, 3)
            self.assertIn("symlink escapes containment", report["detail"])

    def test_workspace_fifo_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "fifo_workspace")
            self.assertEqual(code, 3)
            self.assertIn("unsupported special file", report["detail"])

    def test_extra_provider_output_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "extra_output")
            self.assertEqual(code, 3)
            self.assertIn("output shape is invalid", report["detail"])

    def test_provider_authored_patch_output_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "provider_patch")
            self.assertEqual(code, 3)
            self.assertIn("PATCH.diff", report["detail"])
            self.assertFalse(proposal_path(root).exists())

    def test_symlink_trace_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "symlink_trace")
            self.assertEqual(code, 3)
            self.assertIn("regular non-symlink", report["detail"])

    def test_fifo_trace_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "fifo_trace")
            self.assertEqual(code, 3)
            self.assertIn("regular non-symlink", report["detail"])

    def test_missing_trace_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "missing_trace")
            self.assertEqual(code, 3)
            self.assertIn("output shape is invalid", report["detail"])

    def test_oversize_trace_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "huge_trace")
            self.assertEqual(code, 3)
            self.assertIn("exceeds W1 limit", report["detail"])

    def test_malformed_trace_is_rejected_by_w1_trace_validation(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "malformed_trace")
            self.assertEqual(code, 3)
            self.assertIn("valid UTF-8 JSON", report["detail"])

    def test_provider_stdout_is_diagnostic_and_bounded(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "stdout_spam")
            self.assertEqual(code, 0, report)
            self.assertTrue(report["stdout_truncated"])
            self.assertGreater(report["stdout_bytes"], len(report["stdout"]))
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")

    def test_stored_patch_is_harness_derived_and_trace_is_exact_provider_egress(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "good")
            self.assertEqual(code, 0, report)
            proposal = read_json(proposal_path(root))
            self.assertEqual(proposal["patch_sha256"], report["patch_sha256"])
            self.assertEqual(proposal["trace_sha256"], report["trace_sha256"])
            self.assertEqual(proposal["changed_paths"], ["calc.py"])
            self.assertTrue(stored_patch(root).read_bytes())
            trace = json.loads(stored_trace(root).read_text())
            self.assertEqual(trace["adapter"], "w2-fixture")


if __name__ == "__main__":
    unittest.main()
