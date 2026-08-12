from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tests.w2_support import execute, proposal_path, setup_request


class ForgeW2AdditionalContainmentTests(unittest.TestCase):
    def test_w1_request_mount_is_read_only_inside_provider(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "request_readonly")
            self.assertEqual(code, 0, report)
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")

    def test_extra_output_directory_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "dir_output")
            self.assertEqual(code, 3)
            self.assertEqual(report["execution_state"], "PROVIDER_REJECTED")
            self.assertIn("output shape is invalid", report["detail"])
            self.assertFalse(proposal_path(root).exists())


if __name__ == "__main__":
    unittest.main()
