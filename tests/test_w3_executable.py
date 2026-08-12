from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from forge_core.codex_boundary import (
    CREDENTIAL_ENV_KEYS,
    FORBIDDEN_ARG_TOKENS,
    FROZEN_EXEC_ARGS,
    ForgeCodexAdapterError,
    build_codex_argv,
    inspect_codex_executable,
)
from tests.w3_support import fresh_context, make_executable, make_root, make_workspace, run_mode


class ForgeW3ExecutableAuthorityTests(unittest.TestCase):
    def test_a00_exact_executable_fingerprint_and_version(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp)
            executable = make_executable(base)
            manifest = inspect_codex_executable(executable)
            expected = "sha256:" + hashlib.sha256(executable.read_bytes()).hexdigest()
            self.assertEqual(manifest["path"], str(executable))
            self.assertEqual(manifest["sha256"], expected)
            self.assertEqual(manifest["bytes"], executable.stat().st_size)
            self.assertEqual(manifest["version"], "codex-cli 0.143.0")

    def test_a01_relative_and_symlink_executables_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp)
            executable = make_executable(base)
            symlink = base / "codex-link"
            symlink.symlink_to(executable)
            with self.assertRaisesRegex(ForgeCodexAdapterError, "symlink"):
                inspect_codex_executable(symlink)
            previous = Path.cwd()
            try:
                os.chdir(base)
                with self.assertRaisesRegex(ForgeCodexAdapterError, "absolute"):
                    inspect_codex_executable(Path("fake-codex"))
            finally:
                os.chdir(previous)

    def test_a02_executable_replacement_before_run_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            executable.write_bytes(executable.read_bytes() + b"\n# replacement-before-run\n")
            with self.assertRaisesRegex(ForgeCodexAdapterError, "no longer matches frozen manifest"):
                run_mode(root, workspace, executable, manifest, "good")

    def test_a03_executable_replacement_during_run_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "self_replace")
            self.assertEqual(code, 3, report)
            self.assertEqual(report["adapter_state"], "CODEX_ADAPTER_REJECTED")
            self.assertEqual(report["reason_code"], "CODEX_EXECUTABLE_CHANGED")
            self.assertNotEqual(report["executable_sha256_after"], manifest["sha256"])

    def test_a04_exact_frozen_argv_is_generated(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, report)
            self.assertEqual(
                report["argv"],
                [*FROZEN_EXEC_ARGS, "--cd", str(workspace), "-"],
            )

    def test_a05_prompt_is_stdin_data_not_shell_interpolation(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            sentinel = base / "SHOULD_NOT_EXIST"
            self.assertFalse(sentinel.exists())
            report, code = run_mode(root, workspace, executable, manifest, "prompt_probe")
            self.assertEqual(code, 0, report)
            observed = (workspace / "prompt.sha256.txt").read_text().strip()
            self.assertEqual(observed, report["prompt_sha256"].removeprefix("sha256:"))
            self.assertFalse(sentinel.exists())
            self.assertNotIn("shell", " ".join(report["argv"]).lower())

    def test_a06_adapter_api_cannot_add_forbidden_codex_flags(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp)
            executable = make_executable(base)
            workspace = (base / "workspace").resolve(); workspace.mkdir()
            argv = build_codex_argv(executable, workspace)
            lowered = {item.lower() for item in argv[1:]}
            self.assertTrue(FORBIDDEN_ARG_TOKENS.isdisjoint(lowered))
            self.assertNotIn("--yolo", argv)
            self.assertNotIn("danger-full-access", argv)
            self.assertNotIn("--full-auto", argv)

    def test_a07_ambient_user_config_is_explicitly_ignored(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, report)
            self.assertIn("--ignore-user-config", report["argv"])

    def test_a08_ambient_execpolicy_rules_are_explicitly_ignored(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "good")
            self.assertEqual(code, 0, report)
            self.assertIn("--ignore-rules", report["argv"])

    def test_a09_codex_home_is_disposable_and_operator_auth_is_not_read(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            operator_home = base / "operator-home"; (operator_home / ".codex").mkdir(parents=True)
            auth = operator_home / ".codex" / "auth.json"
            auth.write_text('{"secret":"OPERATOR_AUTH_SENTINEL"}\n')
            previous = os.environ.get("HOME")
            os.environ["HOME"] = str(operator_home)
            try:
                report, code = run_mode(root, workspace, executable, manifest, "codex_home")
            finally:
                if previous is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = previous
            self.assertEqual(code, 0, report)
            self.assertEqual(auth.read_text(), '{"secret":"OPERATOR_AUTH_SENTINEL"}\n')
            self.assertIn("CODEX_HOME", report["provider_environment_keys"])
            self.assertNotIn("OPERATOR_AUTH_SENTINEL", str(report))

    def test_a10_common_credential_environment_is_absent_from_provider(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            prior = {key: os.environ.get(key) for key in CREDENTIAL_ENV_KEYS}
            try:
                for key in CREDENTIAL_ENV_KEYS:
                    os.environ[key] = f"HOST_SECRET_{key}"
                report, code = run_mode(root, workspace, executable, manifest, "secret_probe")
            finally:
                for key, value in prior.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            self.assertEqual(code, 0, report)
            self.assertTrue(CREDENTIAL_ENV_KEYS.isdisjoint(report["provider_environment_keys"]))
            for key in CREDENTIAL_ENV_KEYS:
                self.assertNotIn(f"HOST_SECRET_{key}", str(report))

    def test_changed_or_unsupported_version_surface_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp)
            executable = make_executable(base, version="mystery-codex development")
            with self.assertRaisesRegex(ForgeCodexAdapterError, "version.*frozen interface pattern"):
                inspect_codex_executable(executable)


if __name__ == "__main__":
    unittest.main()
