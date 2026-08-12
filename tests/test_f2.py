from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_forge(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{REPO_ROOT}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        ["forge", *args], cwd=cwd, env=env, text=True, capture_output=True, check=False
    )


def valid_authority() -> dict:
    return {
        "objective": "Add bounded example behavior",
        "deliverables": ["src/example.py", "tests/test_example.py"],
        "success_criteria": [
            {
                "id": "SC_001",
                "statement": "Example behavior passes its deterministic acceptance check",
                "check_ids": ["CHK_001"],
            }
        ],
        "scope": {
            "allowed_paths": ["src/example.py", "tests/test_example.py"],
            "forbidden_paths": ["docs/f0/**", ".github/**"],
        },
        "checks": [
            {
                "id": "CHK_001",
                "required": True,
                "argv": ["python3", "-m", "unittest", "tests.test_example"],
            }
        ],
        "terminal_states": ["PASS", "REPAIR_REQUIRED", "BLOCKED_EXTERNAL"],
        "non_goals": ["No deployment"],
        "forbidden_actions": ["Do not modify files outside allowed_paths"],
    }


def write_authority(root: Path, value: dict, name: str = "authority.json") -> Path:
    path = root / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return path


def init_project(root: Path) -> None:
    result = run_forge(root, "init")
    if result.returncode != 0:
        raise AssertionError(result.stderr)


def contract_path(root: Path, unit: str = "U-0001") -> Path:
    return root / ".forge" / "contracts" / f"{unit}.json"


class ForgeF2Tests(unittest.TestCase):
    def test_create_produces_draft_and_draft_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            source = write_authority(root, valid_authority())
            created = run_forge(root, "contract", "create", "U-0001", "--file", str(source))
            self.assertEqual(created.returncode, 0, created.stderr)
            record = json.loads(contract_path(root).read_text())
            self.assertEqual(record["state"], "DRAFT")
            self.assertIsNone(record["contract_digest"])
            ready = run_forge(root, "contract", "ready", "U-0001")
            self.assertEqual(ready.returncode, 2)
            self.assertIn("DRAFT", ready.stderr)

    def test_freeze_verify_ready_and_second_freeze_are_stable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            source = write_authority(root, valid_authority())
            self.assertEqual(run_forge(root, "contract", "create", "U-0001", "--file", str(source)).returncode, 0)
            first = run_forge(root, "contract", "freeze", "U-0001")
            self.assertEqual(first.returncode, 0, first.stderr)
            before = contract_path(root).read_bytes()
            digest = json.loads(first.stdout)["contract_digest"]
            self.assertTrue(digest.startswith("sha256:"))
            second = run_forge(root, "contract", "freeze", "U-0001")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(contract_path(root).read_bytes(), before)
            verify = run_forge(root, "contract", "verify", "U-0001")
            self.assertEqual(verify.returncode, 0, verify.stderr)
            ready = run_forge(root, "contract", "ready", "U-0001")
            self.assertEqual(ready.returncode, 0, ready.stderr)
            self.assertTrue(json.loads(ready.stdout)["implementation_eligible"])

    def test_same_contract_has_same_digest_in_separate_projects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-a-") as a, tempfile.TemporaryDirectory(prefix="forge-f2-b-") as b:
            roots = [Path(a) / "demo", Path(b) / "demo"]
            digests = []
            for root in roots:
                root.mkdir()
                init_project(root)
                source = write_authority(root, valid_authority())
                self.assertEqual(run_forge(root, "contract", "create", "U-0001", "--file", str(source)).returncode, 0)
                frozen = run_forge(root, "contract", "freeze", "U-0001")
                self.assertEqual(frozen.returncode, 0, frozen.stderr)
                digests.append(json.loads(frozen.stdout)["contract_digest"])
            self.assertEqual(digests[0], digests[1])

    def test_tampering_any_authority_class_breaks_verify_and_ready(self) -> None:
        mutations = {
            "objective": lambda a: a.__setitem__("objective", "Silently changed objective"),
            "success": lambda a: a["success_criteria"][0].__setitem__("statement", "Weakened criterion"),
            "scope": lambda a: a["scope"]["allowed_paths"].append("src/extra.py"),
            "checks": lambda a: a["checks"][0]["argv"].append("--changed"),
            "terminal": lambda a: a["terminal_states"].append("SEALED_NEGATIVE_RESULT"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
                root = Path(tmp) / "demo"
                root.mkdir()
                init_project(root)
                source = write_authority(root, valid_authority())
                self.assertEqual(run_forge(root, "contract", "create", "U-0001", "--file", str(source)).returncode, 0)
                self.assertEqual(run_forge(root, "contract", "freeze", "U-0001").returncode, 0)
                path = contract_path(root)
                record = json.loads(path.read_text())
                mutate(record["authority"])
                path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
                verify = run_forge(root, "contract", "verify", "U-0001")
                ready = run_forge(root, "contract", "ready", "U-0001")
                self.assertEqual(verify.returncode, 2)
                self.assertEqual(ready.returncode, 2)
                self.assertIn("digest mismatch", verify.stderr)

    def test_invalid_unit_ids_and_unsafe_paths_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            source = write_authority(root, valid_authority())
            for unit in ("../X", "u lowercase", "/ABS"):
                with self.subTest(unit=unit):
                    result = run_forge(root, "contract", "create", unit, "--file", str(source))
                    self.assertEqual(result.returncode, 2)
            for bad_path in ("../escape.py", "/tmp/escape.py", "./src/x.py", ".forge/contracts/U.json"):
                with self.subTest(path=bad_path):
                    authority = valid_authority()
                    authority["scope"]["allowed_paths"] = [bad_path]
                    bad = write_authority(root, authority, "bad.json")
                    result = run_forge(root, "contract", "create", "U-BAD", "--file", str(bad))
                    self.assertEqual(result.returncode, 2)

    def test_check_argv_rejects_absolute_machine_paths(self) -> None:
        unsafe_tokens = (
            "/usr/bin/python3",
            "C:\\Python311\\python.exe",
            "--config=/tmp/forge-config.json",
        )
        for index, token in enumerate(unsafe_tokens):
            with self.subTest(token=token), tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
                root = Path(tmp) / "demo"
                root.mkdir()
                init_project(root)
                authority = valid_authority()
                authority["checks"][0]["argv"] = [token, "check.py"]
                source = write_authority(root, authority, f"unsafe-{index}.json")
                result = run_forge(
                    root, "contract", "create", "U-0001", "--file", str(source)
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("absolute machine-specific path", result.stderr)
                self.assertFalse(contract_path(root).exists())

    def test_relative_check_argv_paths_remain_allowed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            authority = valid_authority()
            authority["checks"][0]["argv"] = [
                "python3",
                "tools/check.py",
                "--config=config/test.json",
            ]
            source = write_authority(root, authority)
            result = run_forge(
                root, "contract", "create", "U-0001", "--file", str(source)
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_success_criterion_must_reference_existing_required_check(self) -> None:
        cases = []
        missing = valid_authority()
        missing["success_criteria"][0]["check_ids"] = ["CHK_MISSING"]
        cases.append(missing)
        advisory = valid_authority()
        advisory["checks"][0]["required"] = False
        cases.append(advisory)
        for index, authority in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
                root = Path(tmp) / "demo"
                root.mkdir()
                init_project(root)
                source = write_authority(root, authority)
                result = run_forge(root, "contract", "create", "U-0001", "--file", str(source))
                self.assertEqual(result.returncode, 2)

    def test_amendment_archives_parent_and_blocks_until_refrozen(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            source = write_authority(root, valid_authority())
            self.assertEqual(run_forge(root, "contract", "create", "U-0001", "--file", str(source)).returncode, 0)
            frozen = run_forge(root, "contract", "freeze", "U-0001")
            self.assertEqual(frozen.returncode, 0, frozen.stderr)
            parent_digest = json.loads(frozen.stdout)["contract_digest"]
            parent_bytes = contract_path(root).read_bytes()

            changed = valid_authority()
            changed["objective"] = "Explicitly amended objective"
            changed_source = write_authority(root, changed, "changed.json")
            amended = run_forge(
                root,
                "contract",
                "amend",
                "U-0001",
                "--file",
                str(changed_source),
                "--reason",
                "Objective changed by operator decision",
            )
            self.assertEqual(amended.returncode, 0, amended.stderr)
            record = json.loads(contract_path(root).read_text())
            self.assertEqual(record["revision"], 2)
            self.assertEqual(record["state"], "DRAFT")
            self.assertEqual(record["parent_digest"], parent_digest)
            archive = root / ".forge/contracts/history/U-0001/revision-0001.json"
            self.assertEqual(archive.read_bytes(), parent_bytes)
            self.assertEqual(run_forge(root, "contract", "ready", "U-0001").returncode, 2)
            refrozen = run_forge(root, "contract", "freeze", "U-0001")
            self.assertEqual(refrozen.returncode, 0, refrozen.stderr)
            new_digest = json.loads(refrozen.stdout)["contract_digest"]
            self.assertNotEqual(new_digest, parent_digest)
            self.assertEqual(run_forge(root, "contract", "ready", "U-0001").returncode, 0)

    def test_amendment_history_tamper_breaks_verify_and_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            source = write_authority(root, valid_authority())
            self.assertEqual(run_forge(root, "contract", "create", "U-0001", "--file", str(source)).returncode, 0)
            self.assertEqual(run_forge(root, "contract", "freeze", "U-0001").returncode, 0)
            changed = valid_authority()
            changed["objective"] = "Explicit revision two"
            changed_source = write_authority(root, changed, "changed.json")
            self.assertEqual(
                run_forge(root, "contract", "amend", "U-0001", "--file", str(changed_source), "--reason", "explicit change").returncode,
                0,
            )
            self.assertEqual(run_forge(root, "contract", "freeze", "U-0001").returncode, 0)
            archive = root / ".forge/contracts/history/U-0001/revision-0001.json"
            archived = json.loads(archive.read_text())
            archived["authority"]["objective"] = "tampered historical objective"
            archive.write_text(json.dumps(archived, indent=2, sort_keys=True) + "\n")
            verify = run_forge(root, "contract", "verify", "U-0001")
            ready = run_forge(root, "contract", "ready", "U-0001")
            self.assertEqual(verify.returncode, 2)
            self.assertEqual(ready.returncode, 2)
            self.assertIn("digest mismatch", verify.stderr)

    def test_missing_amendment_history_breaks_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            source = write_authority(root, valid_authority())
            self.assertEqual(run_forge(root, "contract", "create", "U-0001", "--file", str(source)).returncode, 0)
            self.assertEqual(run_forge(root, "contract", "freeze", "U-0001").returncode, 0)
            changed_source = write_authority(root, valid_authority(), "changed.json")
            self.assertEqual(
                run_forge(root, "contract", "amend", "U-0001", "--file", str(changed_source), "--reason", "explicit change").returncode,
                0,
            )
            self.assertEqual(run_forge(root, "contract", "freeze", "U-0001").returncode, 0)
            archive = root / ".forge/contracts/history/U-0001/revision-0001.json"
            archive.unlink()
            ready = run_forge(root, "contract", "ready", "U-0001")
            self.assertEqual(ready.returncode, 2)
            self.assertIn("revision missing", ready.stderr)

    def test_amendment_refuses_tampered_parent_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            source = write_authority(root, valid_authority())
            self.assertEqual(run_forge(root, "contract", "create", "U-0001", "--file", str(source)).returncode, 0)
            self.assertEqual(run_forge(root, "contract", "freeze", "U-0001").returncode, 0)
            path = contract_path(root)
            record = json.loads(path.read_text())
            record["authority"]["objective"] = "tampered"
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            before = path.read_bytes()
            changed_source = write_authority(root, valid_authority(), "changed.json")
            result = run_forge(root, "contract", "amend", "U-0001", "--file", str(changed_source), "--reason", "legit reason")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((root / ".forge/contracts/history/U-0001/revision-0001.json").exists())

    def test_create_refuses_duplicate_and_unknown_terminal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            init_project(root)
            source = write_authority(root, valid_authority())
            first = run_forge(root, "contract", "create", "U-0001", "--file", str(source))
            self.assertEqual(first.returncode, 0, first.stderr)
            second = run_forge(root, "contract", "create", "U-0001", "--file", str(source))
            self.assertEqual(second.returncode, 2)

            authority = valid_authority()
            authority["terminal_states"].append("MAGIC_SUCCESS")
            bad = write_authority(root, authority, "bad.json")
            result = run_forge(root, "contract", "create", "U-0002", "--file", str(bad))
            self.assertEqual(result.returncode, 2)

    def test_build_and_doctor_remain_unauthorized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f2-") as tmp:
            root = Path(tmp) / "demo"
            root.mkdir()
            for command in ("build", "doctor"):
                with self.subTest(command=command):
                    result = run_forge(root, command)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
