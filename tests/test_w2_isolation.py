from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.f5_support import git
from tests.w2_support import execute, execution_path, probe, read_json, setup_request


class ForgeW2IsolationTests(unittest.TestCase):
    def test_backend_probe_is_containment_ready_with_immutable_image(self):
        report = probe()
        self.assertEqual(report["classification"], "CONTAINMENT_READY")
        self.assertEqual(report["backend"], "linux-docker-v0.1")
        self.assertTrue(report["image_id"].startswith("sha256:"))
        joined = " ".join(report["profile"])
        for required in (
            "--network none",
            "--read-only",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "--pids-limit 64",
            "--memory 256m",
            "--cpus 1.0",
            "--user 65534:65534",
        ):
            self.assertIn(required, joined)

    def test_good_fixture_edits_only_disposable_workspace_and_reaches_proposal_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            calc_before = (root / "calc.py").read_bytes()
            status_before = git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout
            worktrees_before = git(root, "worktree", "list", "--porcelain").stdout
            report, code = execute(root, "good")
            self.assertEqual(code, 0, report)
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(report["proposal_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(report["completion_authority"], "none")
            self.assertEqual(report["candidate_authority"], "none")
            self.assertEqual(report["derived_changed_paths"], ["calc.py"])
            self.assertTrue(report["operator_status_unchanged"])
            self.assertTrue(report["worktree_registry_unchanged"])
            self.assertEqual((root / "calc.py").read_bytes(), calc_before)
            self.assertEqual(git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout, status_before)
            self.assertEqual(git(root, "worktree", "list", "--porcelain").stdout, worktrees_before)
            self.assertFalse((root / ".forge/runs/U-0001/attempt-0001").exists())
            self.assertTrue(execution_path(root).is_file())

    def test_host_secret_environment_is_absent_from_provider(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            previous = os.environ.get("FORGE_W2_SECRET")
            os.environ["FORGE_W2_SECRET"] = "HOST_SECRET_SENTINEL"
            try:
                report, code = execute(root, "secret")
            finally:
                if previous is None:
                    os.environ.pop("FORGE_W2_SECRET", None)
                else:
                    os.environ["FORGE_W2_SECRET"] = previous
            self.assertEqual(code, 0, report)
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")

    def test_known_host_absolute_path_is_unreadable_inside_provider(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            sentinel = base / "operator-only-secret.txt"
            sentinel.write_text("HOST_ONLY_SECRET\n")
            report, code = execute(root, "host_path", str(sentinel))
            self.assertEqual(code, 0, report)
            self.assertEqual(sentinel.read_text(), "HOST_ONLY_SECRET\n")

    def test_outbound_network_attempt_fails_inside_provider(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "network")
            self.assertEqual(code, 0, report)
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")
            self.assertIn("--network", report["containment_profile"])
            self.assertIn("none", report["containment_profile"])

    def test_docker_socket_is_absent(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "docker_socket")
            self.assertEqual(code, 0, report)

    def test_zero_capabilities_and_no_new_privileges_are_observed(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "privilege")
            self.assertEqual(code, 0, report)

    def test_host_accelerator_devices_are_not_exposed(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "devices")
            self.assertEqual(code, 0, report)

    def test_provider_has_private_pid_namespace(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "pid_namespace")
            self.assertEqual(code, 0, report)

    def test_pid_and_memory_cgroup_limits_are_observed(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "limits")
            self.assertEqual(code, 0, report)
            joined = " ".join(report["containment_profile"])
            self.assertIn("--pids-limit 64", joined)
            self.assertIn("--memory 256m", joined)
            self.assertIn("--cpus 1.0", joined)

    def test_container_root_filesystem_is_read_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "rootfs")
            self.assertEqual(code, 0, report)
            self.assertIn("--read-only", report["containment_profile"])

    def test_write_outside_workspace_output_tmp_is_denied(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "outside_write")
            self.assertEqual(code, 0, report)


if __name__ == "__main__":
    unittest.main()
