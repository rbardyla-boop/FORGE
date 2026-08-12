from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from forge_core import codex_boundary
from forge_core.codex_boundary import ForgeCodexAdapterError
from tests.w3_support import fresh_context, make_executable


class ForgeW3Repair001Tests(unittest.TestCase):
    def test_r001_a00_relative_inspection_fails_before_delegate(self):
        with patch.object(codex_boundary._kernel, "inspect_codex_executable") as delegate:
            with self.assertRaisesRegex(ForgeCodexAdapterError, "absolute"):
                codex_boundary.inspect_codex_executable(Path("relative-codex"))
            delegate.assert_not_called()

    def test_r001_a01_relative_execution_fails_before_delegate(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-r001-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            with patch.object(codex_boundary._kernel, "execute_codex_adapter") as delegate:
                with self.assertRaisesRegex(ForgeCodexAdapterError, "absolute"):
                    codex_boundary.execute_codex_adapter(
                        root,
                        "U-0001",
                        Path(executable.name),
                        manifest,
                        workspace,
                        fixture_mode="good",
                    )
                delegate.assert_not_called()

    def test_r001_a02_absolute_inspection_delegates_and_preserves_manifest(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-r001-") as tmp:
            base = Path(tmp); executable = make_executable(base)
            manifest = codex_boundary.inspect_codex_executable(executable)
            self.assertEqual(manifest["path"], str(executable))
            self.assertTrue(manifest["sha256"].startswith("sha256:"))

    def test_r001_a03_symlink_remains_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-r001-") as tmp:
            base = Path(tmp); executable = make_executable(base)
            link = (base / "codex-link").resolve(strict=False)
            link.symlink_to(executable)
            with self.assertRaisesRegex(ForgeCodexAdapterError, "symlink"):
                codex_boundary.inspect_codex_executable(link)

    def test_r001_a04_supported_w3_tests_use_public_boundary(self):
        repo = Path(__file__).resolve().parents[1]
        supported = [
            repo / "tests/w3_support.py",
            repo / "tests/test_w3_executable.py",
            repo / "tests/test_w3_composition.py",
        ]
        for path in supported:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("from forge_core.codex_adapter import", text, path)
            self.assertIn("forge_core.codex_boundary", text, path)


if __name__ == "__main__":
    unittest.main()
