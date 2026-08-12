from __future__ import annotations

import inspect
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from forge_core import containment
from forge_core.containment import ForgeContainmentError
from tests.w2_support import execute, probe, setup_request


class ForgeW2Repair001Tests(unittest.TestCase):
    def test_r001_a00_profile_uses_exact_non_root_forge_uid_gid(self):
        report = probe()
        self.assertGreater(os.geteuid(), 0)
        self.assertEqual(report["provider_uid"], os.geteuid())
        self.assertEqual(report["provider_gid"], os.getegid())
        profile = report["profile"]
        index = profile.index("--user")
        self.assertEqual(profile[index + 1], f"{os.geteuid()}:{os.getegid()}")

    def test_r001_a01_host_root_identity_fails_closed(self):
        with patch.object(containment.os, "geteuid", return_value=0), patch.object(
            containment.os, "getegid", return_value=0
        ):
            with self.assertRaisesRegex(ForgeContainmentError, "requires Forge to run as non-root"):
                containment._host_identity()

    def test_r001_a02_original_forge_path_attack_returns_normal_rejection(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-r001-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "forge_path")
            self.assertEqual(code, 3, report)
            self.assertEqual(report["execution_state"], "PROVIDER_REJECTED")
            self.assertEqual(report["reason_code"], "PROVIDER_OUTPUT_REJECTED")
            self.assertIn("forbidden .forge authority path", report.get("detail", ""))

    def test_r001_a03_rejected_forge_path_attack_leaves_no_exec_temp_residue(self):
        temp_root = Path(tempfile.gettempdir())
        before = {path.resolve() for path in temp_root.glob("forge-w2-exec-*")}
        with tempfile.TemporaryDirectory(prefix="forge-w2-r001-") as tmp:
            root = setup_request(Path(tmp))
            report, code = execute(root, "forge_path")
            self.assertEqual(code, 3, report)
        after = {path.resolve() for path in temp_root.glob("forge-w2-exec-*")}
        self.assertEqual(after, before)

    def test_r001_a04_restrictive_nested_tree_is_reclaimable_by_forge_owner(self):
        with tempfile.TemporaryDirectory(prefix="forge-w2-r001-tree-") as tmp:
            root = Path(tmp) / "workspace"
            nested = root / "locked" / "deeper"
            nested.mkdir(parents=True)
            payload = nested / "payload.txt"
            payload.write_text("provider-owned-by-same-host-uid\n")
            payload.chmod(0o000)
            nested.chmod(0o000)
            (root / "locked").chmod(0o000)
            containment._reclaim_provider_tree(root)
            self.assertEqual(payload.read_text(), "provider-owned-by-same-host-uid\n")
            self.assertTrue(os.access(root / "locked", os.R_OK | os.W_OK | os.X_OK))

    def test_r001_a05_no_privileged_cleanup_and_userns_modes_fail_policy(self):
        source = inspect.getsource(containment)
        self.assertNotIn("--privileged", source)
        self.assertNotIn("cap-add", source)
        self.assertNotIn("sudo", source)
        self.assertFalse(containment._docker_security_options_reclaimable('["name=rootless"]'))
        self.assertFalse(containment._docker_security_options_reclaimable('["name=userns"]'))
        self.assertTrue(
            containment._docker_security_options_reclaimable(
                '["name=seccomp,profile=builtin","name=apparmor","name=cgroupns"]'
            )
        )

    def test_r001_a06_original_isolation_profile_is_preserved(self):
        report = probe()
        joined = " ".join(report["profile"])
        for required in (
            "--network none",
            "--read-only",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "--pids-limit 64",
            "--memory 256m",
            "--cpus 1.0",
            "--ipc private",
        ):
            self.assertIn(required, joined)


if __name__ == "__main__":
    unittest.main()
