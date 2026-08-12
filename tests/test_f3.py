from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from forge_core.doctor import (
    BLOCKED_EXTERNAL,
    ENVIRONMENT_READY,
    FORGE_CANNOT_VERIFY,
    PROJECT_BASELINE_FAILURE,
    run_doctor,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_forge(
    cwd: Path, *args: str, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{REPO_ROOT}{os.pathsep}{env.get('PATH', '')}"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["forge", *args], cwd=cwd, env=env, text=True, capture_output=True, check=False
    )


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def make_repo(base: Path, files: dict[str, str]) -> Path:
    root = base / "project"
    root.mkdir()
    result = git(root, "init", "-b", "main")
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    git(root, "config", "user.name", "Forge F3 Test")
    git(root, "config", "user.email", "forge-f3@example.invalid")
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(root, "add", ".")
    committed = git(root, "commit", "-m", "fixture baseline")
    if committed.returncode != 0:
        raise AssertionError(committed.stderr)
    return root


def init_project(root: Path) -> None:
    result = run_forge(root, "init")
    if result.returncode != 0:
        raise AssertionError(result.stderr)


def authority_for(checks: list[dict]) -> dict:
    required = next(check["id"] for check in checks if check["required"])
    return {
        "objective": "Prove the frozen baseline verification environment is runnable",
        "deliverables": ["src/future_change.py"],
        "success_criteria": [
            {
                "id": "SC_001",
                "statement": "The required runner remains a valid completion gate",
                "check_ids": [required],
            }
        ],
        "scope": {
            "allowed_paths": ["src/future_change.py", "tests/**"],
            "forbidden_paths": [".github/**"],
        },
        "checks": checks,
        "terminal_states": ["PASS", "REPAIR_REQUIRED", "BLOCKED_EXTERNAL"],
        "non_goals": ["No product implementation during Doctor"],
        "forbidden_actions": ["Do not modify the operator working tree"],
    }


def write_authority(root: Path, authority: dict) -> Path:
    path = root / "authority.json"
    path.write_text(json.dumps(authority, indent=2, sort_keys=True) + "\n")
    return path


def create_contract(root: Path, checks: list[dict], *, freeze: bool = True) -> dict:
    source = write_authority(root, authority_for(checks))
    created = run_forge(root, "contract", "create", "U-0001", "--file", str(source))
    if created.returncode != 0:
        raise AssertionError(created.stderr)
    if not freeze:
        return json.loads(created.stdout)
    frozen = run_forge(root, "contract", "freeze", "U-0001")
    if frozen.returncode != 0:
        raise AssertionError(frozen.stderr)
    return json.loads(frozen.stdout)


def required(argv: list[str], check_id: str = "CHK_001") -> dict:
    return {"id": check_id, "required": True, "argv": argv}


def advisory(argv: list[str], check_id: str = "CHK_ADV") -> dict:
    return {"id": check_id, "required": False, "argv": argv}


class ForgeF3Tests(unittest.TestCase):
    def test_green_frozen_baseline_is_environment_ready_and_bound(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {
                    "check.py": 'print("baseline-green")\n',
                    "tracked.txt": "original\n",
                },
            )
            init_project(root)
            frozen = create_contract(root, [required(["python3", "check.py"])])
            baseline = git(root, "rev-parse", "HEAD").stdout.strip()
            status_before = git(root, "status", "--porcelain=v1").stdout
            worktrees_before = git(root, "worktree", "list", "--porcelain").stdout

            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], ENVIRONMENT_READY)
            self.assertTrue(report["implementation_environment_ready"])
            self.assertEqual(report["baseline_commit"], baseline)
            self.assertEqual(report["contract_digest"], frozen["contract_digest"])
            self.assertEqual(report["workspace_mode"], "detached_git_worktree")
            self.assertEqual(report["checks"][0]["classification"], ENVIRONMENT_READY)
            self.assertEqual(report["checks"][0]["stdout"], "baseline-green\n")
            self.assertTrue(report["operator_status_unchanged"])
            self.assertTrue(report["worktree_registry_unchanged"])
            self.assertEqual(git(root, "status", "--porcelain=v1").stdout, status_before)
            self.assertEqual(
                git(root, "worktree", "list", "--porcelain").stdout,
                worktrees_before,
            )

    def test_draft_contract_blocks_before_check_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            marker = Path(tmp) / "marker"
            root = make_repo(
                Path(tmp),
                {
                    "check.py": (
                        "import os\nfrom pathlib import Path\n"
                        'Path(os.environ["F3_MARKER"]).write_text("ran")\n'
                    )
                },
            )
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])], freeze=False)
            result = run_forge(
                root, "doctor", "U-0001", env_extra={"F3_MARKER": str(marker)}
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("DRAFT", result.stderr)
            self.assertFalse(marker.exists())

    def test_tampered_contract_blocks_before_check_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            marker = Path(tmp) / "marker"
            root = make_repo(
                Path(tmp),
                {
                    "check.py": (
                        "import os\nfrom pathlib import Path\n"
                        'Path(os.environ["F3_MARKER"]).write_text("ran")\n'
                    )
                },
            )
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            path = root / ".forge/contracts/U-0001.json"
            record = json.loads(path.read_text())
            record["authority"]["objective"] = "tampered after freeze"
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            result = run_forge(
                root, "doctor", "U-0001", env_extra={"F3_MARKER": str(marker)}
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("digest mismatch", result.stderr)
            self.assertFalse(marker.exists())

    def test_non_git_directory_is_forge_cannot_verify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            init_project(root)
            create_contract(root, [required(["python3", "-c", "print('ok')"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 4)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], FORGE_CANNOT_VERIFY)
            self.assertEqual(report["reason_code"], "NOT_GIT_REPOSITORY")

    def test_invocation_below_git_root_is_forge_cannot_verify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            repo = make_repo(Path(tmp), {"sub/placeholder.txt": "x\n"})
            root = repo / "sub"
            init_project(root)
            create_contract(root, [required(["python3", "-c", "print('ok')"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 4)
            report = json.loads(result.stdout)
            self.assertEqual(report["reason_code"], "NOT_REPOSITORY_ROOT")

    def test_dirty_tracked_baseline_blocks_without_executing_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            marker = Path(tmp) / "marker"
            root = make_repo(
                Path(tmp),
                {
                    "check.py": (
                        "import os\nfrom pathlib import Path\n"
                        'Path(os.environ["F3_MARKER"]).write_text("ran")\n'
                    ),
                    "tracked.txt": "clean\n",
                },
            )
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            (root / "tracked.txt").write_text("dirty\n")
            result = run_forge(
                root, "doctor", "U-0001", env_extra={"F3_MARKER": str(marker)}
            )
            self.assertEqual(result.returncode, 4)
            report = json.loads(result.stdout)
            self.assertEqual(report["reason_code"], "TRACKED_WORKTREE_DIRTY")
            self.assertFalse(marker.exists())

    def test_missing_required_executable_is_forge_cannot_verify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(Path(tmp), {"tracked.txt": "clean\n"})
            init_project(root)
            create_contract(root, [required(["forge-command-that-does-not-exist"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 4)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], FORGE_CANNOT_VERIFY)
            self.assertEqual(report["checks"][0]["reason_code"], "EXECUTABLE_NOT_FOUND")
            self.assertTrue(report["operator_status_unchanged"])

    def test_timeout_is_forge_cannot_verify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {"slow.py": "import time\ntime.sleep(5)\n"},
            )
            init_project(root)
            create_contract(root, [required(["python3", "slow.py"])])
            report, code = run_doctor(root, "U-0001", timeout_seconds=0.1)
            self.assertEqual(code, 4)
            self.assertEqual(report["classification"], FORGE_CANNOT_VERIFY)
            self.assertEqual(report["checks"][0]["reason_code"], "CHECK_TIMEOUT")
            self.assertTrue(report["operator_status_unchanged"])
            self.assertTrue(report["worktree_registry_unchanged"])

    def test_check_mutation_is_rejected_and_original_tree_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {
                    "mutate.py": 'from pathlib import Path\nPath("tracked.txt").write_text("changed\\n")\n',
                    "tracked.txt": "original\n",
                },
            )
            original = (root / "tracked.txt").read_bytes()
            init_project(root)
            create_contract(root, [required(["python3", "mutate.py"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 4)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["checks"][0]["reason_code"], "CHECK_MUTATED_TRACKED_BASELINE"
            )
            self.assertTrue(report["checks"][0]["tracked_baseline_mutated"])
            self.assertEqual((root / "tracked.txt").read_bytes(), original)
            self.assertTrue(report["operator_status_unchanged"])
            self.assertTrue(report["worktree_registry_unchanged"])

    def test_ordinary_nonzero_is_project_baseline_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {"fail.py": "import sys\nsys.exit(7)\n"},
            )
            init_project(root)
            create_contract(root, [required(["python3", "fail.py"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], PROJECT_BASELINE_FAILURE)
            self.assertEqual(report["checks"][0]["exit_code"], 7)
            self.assertEqual(report["checks"][0]["reason_code"], "CHECK_NONZERO")

    def test_exit_75_without_external_prefix_is_project_baseline_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {"tempfail.py": 'import sys\nprint("ordinary failure", file=sys.stderr)\nsys.exit(75)\n'},
            )
            init_project(root)
            create_contract(root, [required(["python3", "tempfail.py"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], PROJECT_BASELINE_FAILURE)

    def test_explicit_external_protocol_is_blocked_external(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {
                    "external.py": (
                        "import sys\n"
                        'print("FORGE_BLOCKED_EXTERNAL: service unavailable", file=sys.stderr)\n'
                        "sys.exit(75)\n"
                    )
                },
            )
            init_project(root)
            create_contract(root, [required(["python3", "external.py"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 5)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], BLOCKED_EXTERNAL)
            self.assertEqual(
                report["checks"][0]["reason_code"], "EXTERNAL_DEPENDENCY_REPORTED"
            )

    def test_advisory_check_is_skipped_and_cannot_block_readiness(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {
                    "required.py": "pass\n",
                    "advisory.py": (
                        'from pathlib import Path\nPath("tracked.txt").write_text("mutated\\n")\n'
                    ),
                    "tracked.txt": "original\n",
                },
            )
            init_project(root)
            create_contract(
                root,
                [
                    required(["python3", "required.py"]),
                    advisory(["python3", "advisory.py"]),
                ],
            )
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], ENVIRONMENT_READY)
            self.assertEqual(report["advisory_checks_skipped"], ["CHK_ADV"])
            self.assertEqual([item["id"] for item in report["checks"]], ["CHK_001"])
            self.assertEqual((root / "tracked.txt").read_text(), "original\n")

    def test_tracked_symlink_escape_blocks_before_check_and_preserves_external_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            base = Path(tmp)
            external = base / "operator-target.txt"
            external.write_text("original\n")
            root = make_repo(
                base,
                {"write_link.py": 'from pathlib import Path\nPath("escape").write_text("changed\\n")\n'},
            )
            (root / "escape").symlink_to(external)
            git(root, "add", "escape")
            committed = git(root, "commit", "-m", "add escaping symlink")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            init_project(root)
            create_contract(root, [required(["python3", "write_link.py"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 4)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], FORGE_CANNOT_VERIFY)
            self.assertEqual(report["reason_code"], "TRACKED_SYMLINK_ESCAPE")
            self.assertEqual(report["unsafe_symlinks"], ["escape"])
            self.assertEqual(report["checks"], [])
            self.assertEqual(external.read_text(), "original\n")
            self.assertTrue(report["operator_status_unchanged"])
            self.assertTrue(report["worktree_registry_unchanged"])

    def test_safe_internal_symlink_can_be_used_by_green_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            base = Path(tmp)
            root = make_repo(
                base,
                {
                    "target.txt": "inside\n",
                    "read_link.py": 'from pathlib import Path\nassert Path("inside-link").read_text() == "inside\\n"\n',
                },
            )
            (root / "inside-link").symlink_to("target.txt")
            git(root, "add", "inside-link")
            committed = git(root, "commit", "-m", "add internal symlink")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            init_project(root)
            create_contract(root, [required(["python3", "read_link.py"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], ENVIRONMENT_READY)

    def test_check_output_is_bounded_and_pwd_points_at_disposable_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {
                    "loud.py": (
                        "import os, sys\n"
                        "print(os.environ.get('PWD', ''))\n"
                        "print('x' * 5000)\n"
                        "print('y' * 5000, file=sys.stderr)\n"
                    )
                },
            )
            init_project(root)
            create_contract(root, [required(["python3", "loud.py"])])
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            check = report["checks"][0]
            self.assertTrue(check["stdout_truncated"])
            self.assertTrue(check["stderr_truncated"])
            self.assertEqual(len(check["stdout"]), 4096)
            self.assertEqual(len(check["stderr"]), 4096)
            first_line = check["stdout"].splitlines()[0]
            self.assertNotEqual(first_line, str(root))
            self.assertTrue(first_line.endswith("/worktree"))

    def test_precedence_external_over_project_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {
                    "fail.py": "import sys\nsys.exit(2)\n",
                    "external.py": (
                        "import sys\n"
                        'print("FORGE_BLOCKED_EXTERNAL: dependency", file=sys.stderr)\n'
                        "sys.exit(75)\n"
                    ),
                },
            )
            init_project(root)
            create_contract(
                root,
                [
                    required(["python3", "fail.py"], "CHK_FAIL"),
                    required(["python3", "external.py"], "CHK_EXT"),
                ],
            )
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 5)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], BLOCKED_EXTERNAL)

    def test_precedence_cannot_verify_over_external_and_project_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = make_repo(
                Path(tmp),
                {
                    "fail.py": "import sys\nsys.exit(2)\n",
                    "external.py": (
                        "import sys\n"
                        'print("FORGE_BLOCKED_EXTERNAL: dependency", file=sys.stderr)\n'
                        "sys.exit(75)\n"
                    ),
                },
            )
            init_project(root)
            create_contract(
                root,
                [
                    required(["python3", "fail.py"], "CHK_FAIL"),
                    required(["python3", "external.py"], "CHK_EXT"),
                    required(["definitely-missing-forge-tool"], "CHK_MISSING"),
                ],
            )
            result = run_forge(root, "doctor", "U-0001")
            self.assertEqual(result.returncode, 4)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], FORGE_CANNOT_VERIFY)
            self.assertEqual(len(report["checks"]), 3)

    def test_bare_doctor_remains_predecessor_compatible_invalid_choice(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            result = run_forge(root, "doctor")
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid choice", result.stderr)

    def test_build_remains_unauthorized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f3-") as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            result = run_forge(root, "build")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
