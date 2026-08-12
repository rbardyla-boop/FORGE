from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
FORGE = REPO_ROOT / "forge"


def run_forge(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{REPO_ROOT}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        ["forge", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ForgeF1Tests(unittest.TestCase):
    def test_launcher_is_executable(self) -> None:
        self.assertTrue(FORGE.is_file())
        self.assertTrue(os.access(FORGE, os.X_OK))

    def test_init_creates_exact_authorized_state_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            result = run_forge(root, "init")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                sorted(p.name for p in (root / ".forge").iterdir()),
                ["project.json", "state.json"],
            )
            project = json.loads((root / ".forge/project.json").read_text())
            state = json.loads((root / ".forge/state.json").read_text())
            self.assertEqual(project["project_name"], "demo")
            self.assertEqual(project["authorized_commands"], ["init", "status"])
            self.assertEqual(state["current_unit"], "F1")
            self.assertEqual(state["unit_state"], "INITIALIZED")

    def test_second_init_is_idempotent_and_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            first = run_forge(root, "init")
            self.assertEqual(first.returncode, 0, first.stderr)
            paths = [root / ".forge/project.json", root / ".forge/state.json"]
            before = [sha256(path) for path in paths]
            second = run_forge(root, "init")
            self.assertEqual(second.returncode, 0, second.stderr)
            after = [sha256(path) for path in paths]
            self.assertEqual(before, after)
            self.assertFalse(json.loads(second.stdout)["created"])

    def test_fresh_process_status_recovers_canonical_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_result = run_forge(root, "init")
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            # subprocess starts a distinct interpreter; no Python memory survives.
            status_result = run_forge(root, "status")
            self.assertEqual(status_result.returncode, 0, status_result.stderr)
            status = json.loads(status_result.stdout)
            self.assertEqual(status["project_name"], "demo")
            self.assertEqual(status["current_unit"], "F1")
            self.assertEqual(status["unit_state"], "INITIALIZED")
            self.assertIsNone(status["terminal_state"])
            self.assertEqual(status["canonical_state"], "VALID")
            self.assertEqual(
                status["largest_remaining_gap"], "prove process-loss recovery"
            )

    def test_status_fails_closed_on_missing_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            result = run_forge(root, "status")
            self.assertEqual(result.returncode, 2)
            self.assertIn("canonical state directory is missing or unsafe", result.stderr)

    def test_status_fails_closed_on_corrupt_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            self.assertEqual(run_forge(root, "init").returncode, 0)
            (root / ".forge/state.json").write_text("{not-json}\n")
            result = run_forge(root, "status")
            self.assertEqual(result.returncode, 2)
            self.assertIn("canonical state unreadable", result.stderr)

    def test_init_refuses_to_overwrite_modified_canonical_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            self.assertEqual(run_forge(root, "init").returncode, 0)
            state_path = root / ".forge/state.json"
            state = json.loads(state_path.read_text())
            state["unit_state"] = "FAKE_PASS"
            state_path.write_text(json.dumps(state) + "\n")
            result = run_forge(root, "init")
            self.assertEqual(result.returncode, 2)
            self.assertIn("differs from F1 initialization contract", result.stderr)

    def test_same_named_projects_initialize_to_identical_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-a-") as a, tempfile.TemporaryDirectory(prefix="forge-f1-b-") as b:
            left = Path(a) / "same-name"
            right = Path(b) / "same-name"
            left.mkdir()
            right.mkdir()
            self.assertEqual(run_forge(left, "init").returncode, 0)
            self.assertEqual(run_forge(right, "init").returncode, 0)
            for name in ("project.json", "state.json"):
                self.assertEqual(
                    (left / ".forge" / name).read_bytes(),
                    (right / ".forge" / name).read_bytes(),
                )

    def test_symlinked_state_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            base = Path(tmp)
            root = base / "demo"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            (root / ".forge").symlink_to(outside, target_is_directory=True)
            result = run_forge(root, "init")
            self.assertEqual(result.returncode, 2)
            self.assertIn("must not be a symlink", result.stderr)
            self.assertEqual(list(outside.iterdir()), [])

    def test_partial_state_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            root = Path(tmp) / "demo"
            (root / ".forge").mkdir(parents=True)
            marker = root / ".forge/project.json"
            marker.write_text("{}\n")
            before = marker.read_bytes()
            result = run_forge(root, "init")
            self.assertEqual(result.returncode, 2)
            self.assertIn("partial canonical state", result.stderr)
            self.assertEqual(marker.read_bytes(), before)
            self.assertFalse((root / ".forge/state.json").exists())

    def test_unauthorized_doctor_command_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f1-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            result = run_forge(root, "doctor")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
