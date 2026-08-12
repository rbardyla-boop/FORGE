from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
from typing import Any

from .contract import ForgeContractError, verify_contract

ENVIRONMENT_READY = "ENVIRONMENT_READY"
PROJECT_BASELINE_FAILURE = "PROJECT_BASELINE_FAILURE"
FORGE_CANNOT_VERIFY = "FORGE_CANNOT_VERIFY"
BLOCKED_EXTERNAL = "BLOCKED_EXTERNAL"

CHECK_TIMEOUT_SECONDS = 30.0
OUTPUT_LIMIT = 4096
EXTERNAL_PREFIX = "FORGE_BLOCKED_EXTERNAL:"

EXIT_CODES = {
    ENVIRONMENT_READY: 0,
    PROJECT_BASELINE_FAILURE: 3,
    FORGE_CANNOT_VERIFY: 4,
    BLOCKED_EXTERNAL: 5,
}

_PRECEDENCE = {
    ENVIRONMENT_READY: 0,
    PROJECT_BASELINE_FAILURE: 1,
    BLOCKED_EXTERNAL: 2,
    FORGE_CANNOT_VERIFY: 3,
}


def _bounded(value: str | None) -> tuple[str, bool]:
    text = value or ""
    if len(text) <= OUTPUT_LIMIT:
        return text, False
    return text[:OUTPUT_LIMIT], True


def _git(git_exe: str, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [git_exe, "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def _failure_report(
    report: dict[str, Any], reason_code: str, detail: str = ""
) -> tuple[dict[str, Any], int]:
    report["classification"] = FORGE_CANNOT_VERIFY
    report["implementation_environment_ready"] = False
    report["reason_code"] = reason_code
    if detail:
        bounded, truncated = _bounded(detail)
        report["detail"] = bounded
        report["detail_truncated"] = truncated
    return report, EXIT_CODES[FORGE_CANNOT_VERIFY]


def _execute_check(argv: list[str], worktree: Path, timeout_seconds: float) -> dict[str, Any]:
    base: dict[str, Any] = {
        "argv": argv,
        "classification": FORGE_CANNOT_VERIFY,
        "exit_code": None,
        "reason_code": "CHECK_LAUNCH_FAILED",
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "tracked_baseline_mutated": False,
    }

    check_env = os.environ.copy()
    check_env["PWD"] = str(worktree)
    for inherited_git_key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        check_env.pop(inherited_git_key, None)

    try:
        process = subprocess.Popen(
            argv,
            cwd=worktree,
            env=check_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=(os.name == "posix"),
        )
    except FileNotFoundError as exc:
        base["reason_code"] = "EXECUTABLE_NOT_FOUND"
        base["stderr"] = str(exc)
        return base
    except PermissionError as exc:
        base["reason_code"] = "EXECUTABLE_NOT_EXECUTABLE"
        base["stderr"] = str(exc)
        return base
    except OSError as exc:
        base["reason_code"] = "CHECK_LAUNCH_FAILED"
        base["stderr"] = str(exc)
        return base

    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        stdout, stderr = process.communicate()
        out, out_truncated = _bounded(stdout)
        err, err_truncated = _bounded(stderr)
        base.update(
            {
                "exit_code": process.returncode,
                "reason_code": "CHECK_TIMEOUT",
                "stdout": out,
                "stderr": err,
                "stdout_truncated": out_truncated,
                "stderr_truncated": err_truncated,
            }
        )
        return base

    out, out_truncated = _bounded(stdout)
    err, err_truncated = _bounded(stderr)
    base.update(
        {
            "exit_code": process.returncode,
            "stdout": out,
            "stderr": err,
            "stdout_truncated": out_truncated,
            "stderr_truncated": err_truncated,
        }
    )

    if process.returncode == 0:
        base["classification"] = ENVIRONMENT_READY
        base["reason_code"] = "CHECK_PASS"
    elif process.returncode == 75 and any(
        line.startswith(EXTERNAL_PREFIX) for line in stderr.splitlines()
    ):
        base["classification"] = BLOCKED_EXTERNAL
        base["reason_code"] = "EXTERNAL_DEPENDENCY_REPORTED"
    else:
        base["classification"] = PROJECT_BASELINE_FAILURE
        base["reason_code"] = "CHECK_NONZERO"
    return base


def _tracked_symlink_safety(
    git_exe: str, worktree: Path
) -> tuple[str | None, list[str], str]:
    try:
        indexed = _git(git_exe, worktree, "ls-files", "-z", "-s")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "SYMLINK_INDEX_FAILED", [], str(exc)
    if indexed.returncode != 0:
        return "SYMLINK_INDEX_FAILED", [], indexed.stderr

    unsafe: list[str] = []
    unsupported: list[str] = []
    worktree_resolved = worktree.resolve()
    for record in indexed.stdout.split("\x00"):
        if not record:
            continue
        try:
            metadata, relative = record.split("\t", 1)
            mode = metadata.split(" ", 1)[0]
        except ValueError:
            return "SYMLINK_INDEX_FAILED", [], "unable to parse git ls-files record"
        if mode != "120000":
            continue
        link = worktree / relative
        if not link.is_symlink():
            unsupported.append(relative)
            continue
        try:
            resolved = link.resolve(strict=False)
            resolved.relative_to(worktree_resolved)
        except (OSError, ValueError):
            unsafe.append(relative)

    if unsupported:
        return "TRACKED_SYMLINK_UNSUPPORTED", sorted(unsupported), ""
    if unsafe:
        return "TRACKED_SYMLINK_ESCAPE", sorted(unsafe), ""
    return None, [], ""


def _overall_classification(checks: list[dict[str, Any]]) -> str:
    return max(
        (check["classification"] for check in checks),
        key=lambda classification: _PRECEDENCE[classification],
    )


def run_doctor(
    root: Path, unit_id: str, *, timeout_seconds: float = CHECK_TIMEOUT_SECONDS
) -> tuple[dict[str, Any], int]:
    root = root.resolve()
    verification_before = verify_contract(root, unit_id)
    contract_path = root / ".forge" / "contracts" / f"{unit_id}.json"
    if contract_path.is_symlink():
        raise ForgeContractError("contract file must not be a symlink")
    try:
        contract_bytes = contract_path.read_bytes()
        contract = json.loads(contract_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ForgeContractError("verified contract became unreadable during Doctor preflight") from exc
    verification_after = verify_contract(root, unit_id)
    if (
        verification_before["contract_digest"] != verification_after["contract_digest"]
        or contract.get("contract_digest") != verification_after["contract_digest"]
        or contract_path.read_bytes() != contract_bytes
    ):
        raise ForgeContractError("contract changed during Doctor preflight")

    authority = contract["authority"]
    required_checks = [check for check in authority["checks"] if check["required"]]
    advisory_ids = [check["id"] for check in authority["checks"] if not check["required"]]

    report: dict[str, Any] = {
        "unit_id": unit_id,
        "contract_digest": verification_after["contract_digest"],
        "baseline_commit": None,
        "workspace_mode": None,
        "classification": FORGE_CANNOT_VERIFY,
        "implementation_environment_ready": False,
        "checks": [],
        "advisory_checks_skipped": advisory_ids,
        "required_checks_not_run": [],
        "reason_code": None,
        "operator_status_unchanged": None,
        "worktree_registry_unchanged": None,
    }

    git_exe = shutil.which("git")
    if git_exe is None:
        return _failure_report(report, "GIT_NOT_FOUND")

    try:
        top = _git(git_exe, root, "rev-parse", "--show-toplevel")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _failure_report(report, "GIT_PROBE_FAILED", str(exc))
    if top.returncode != 0:
        return _failure_report(report, "NOT_GIT_REPOSITORY", top.stderr)
    try:
        git_root = Path(top.stdout.strip()).resolve()
    except OSError as exc:
        return _failure_report(report, "GIT_ROOT_UNRESOLVABLE", str(exc))
    if git_root != root:
        return _failure_report(report, "NOT_REPOSITORY_ROOT", top.stdout.strip())

    try:
        head = _git(git_exe, root, "rev-parse", "--verify", "HEAD")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _failure_report(report, "HEAD_PROBE_FAILED", str(exc))
    if head.returncode != 0 or not head.stdout.strip():
        return _failure_report(report, "NO_COMMITTED_HEAD", head.stderr)
    baseline_commit = head.stdout.strip()
    report["baseline_commit"] = baseline_commit

    try:
        tracked_status = _git(
            git_exe, root, "status", "--porcelain=v1", "--untracked-files=no"
        )
        full_status_before = _git(
            git_exe, root, "status", "--porcelain=v1", "--untracked-files=all"
        )
        worktrees_before = _git(git_exe, root, "worktree", "list", "--porcelain")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _failure_report(report, "GIT_STATUS_FAILED", str(exc))
    if tracked_status.returncode != 0 or full_status_before.returncode != 0:
        return _failure_report(report, "GIT_STATUS_FAILED", tracked_status.stderr)
    if worktrees_before.returncode != 0:
        return _failure_report(report, "WORKTREE_LIST_FAILED", worktrees_before.stderr)
    if tracked_status.stdout:
        return _failure_report(report, "TRACKED_WORKTREE_DIRTY", tracked_status.stdout)

    temp_parent = Path(tempfile.mkdtemp(prefix="forge-doctor-"))
    disposable = temp_parent / "worktree"
    worktree_added = False
    cleanup_problem: tuple[str, str] | None = None

    try:
        try:
            added = _git(
                git_exe,
                root,
                "worktree",
                "add",
                "--detach",
                "--quiet",
                str(disposable),
                baseline_commit,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return _failure_report(report, "WORKTREE_CREATE_FAILED", str(exc))
        if added.returncode != 0:
            return _failure_report(report, "WORKTREE_CREATE_FAILED", added.stderr)
        worktree_added = True
        report["workspace_mode"] = "detached_git_worktree"

        symlink_reason, unsafe_symlinks, symlink_detail = _tracked_symlink_safety(
            git_exe, disposable
        )
        if symlink_reason is not None:
            report["classification"] = FORGE_CANNOT_VERIFY
            report["reason_code"] = symlink_reason
            report["unsafe_symlinks"] = unsafe_symlinks
            if symlink_detail:
                report["detail"], report["detail_truncated"] = _bounded(symlink_detail)
            report["required_checks_not_run"] = [item["id"] for item in required_checks]
        else:
            for index, check in enumerate(required_checks):
                check_result = _execute_check(check["argv"], disposable, timeout_seconds)
                check_result["id"] = check["id"]

                try:
                    disposable_status = _git(
                        git_exe,
                        disposable,
                        "status",
                        "--porcelain=v1",
                        "--untracked-files=no",
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    check_result["classification"] = FORGE_CANNOT_VERIFY
                    check_result["reason_code"] = "DISPOSABLE_STATUS_FAILED"
                    check_result["stderr"], check_result["stderr_truncated"] = _bounded(
                        str(exc)
                    )
                    report["checks"].append(check_result)
                    report["required_checks_not_run"] = [
                        item["id"] for item in required_checks[index + 1 :]
                    ]
                    break

                if disposable_status.returncode != 0:
                    check_result["classification"] = FORGE_CANNOT_VERIFY
                    check_result["reason_code"] = "DISPOSABLE_STATUS_FAILED"
                    check_result["stderr"], check_result["stderr_truncated"] = _bounded(
                        disposable_status.stderr
                    )
                    report["checks"].append(check_result)
                    report["required_checks_not_run"] = [
                        item["id"] for item in required_checks[index + 1 :]
                    ]
                    break

                if disposable_status.stdout:
                    check_result["classification"] = FORGE_CANNOT_VERIFY
                    check_result["reason_code"] = "CHECK_MUTATED_TRACKED_BASELINE"
                    check_result["tracked_baseline_mutated"] = True
                    mutation, mutation_truncated = _bounded(disposable_status.stdout)
                    check_result["tracked_mutation"] = mutation
                    check_result["tracked_mutation_truncated"] = mutation_truncated
                    report["checks"].append(check_result)
                    report["required_checks_not_run"] = [
                        item["id"] for item in required_checks[index + 1 :]
                    ]
                    break

                report["checks"].append(check_result)

            if report["checks"]:
                report["classification"] = _overall_classification(report["checks"])
                report["reason_code"] = "REQUIRED_CHECKS_EVALUATED"
            else:
                report["classification"] = FORGE_CANNOT_VERIFY
                report["reason_code"] = "NO_REQUIRED_CHECK_RESULT"
    finally:
        if worktree_added:
            try:
                removed = _git(
                    git_exe, root, "worktree", "remove", "--force", str(disposable)
                )
                if removed.returncode != 0:
                    cleanup_problem = ("WORKTREE_REMOVE_FAILED", removed.stderr)
            except (OSError, subprocess.TimeoutExpired) as exc:
                cleanup_problem = ("WORKTREE_REMOVE_FAILED", str(exc))
        try:
            shutil.rmtree(temp_parent, ignore_errors=True)
        except OSError as exc:
            cleanup_problem = cleanup_problem or ("TEMP_CLEANUP_FAILED", str(exc))
        if cleanup_problem is not None:
            try:
                _git(git_exe, root, "worktree", "prune")
            except (OSError, subprocess.TimeoutExpired):
                pass

    try:
        full_status_after = _git(
            git_exe, root, "status", "--porcelain=v1", "--untracked-files=all"
        )
        worktrees_after = _git(git_exe, root, "worktree", "list", "--porcelain")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _failure_report(report, "POSTCONDITION_PROBE_FAILED", str(exc))

    report["operator_status_unchanged"] = (
        full_status_after.returncode == 0
        and full_status_after.stdout == full_status_before.stdout
    )
    report["worktree_registry_unchanged"] = (
        worktrees_after.returncode == 0
        and worktrees_after.stdout == worktrees_before.stdout
    )

    if cleanup_problem is not None:
        reason, detail = cleanup_problem
        return _failure_report(report, reason, detail)
    if not report["operator_status_unchanged"]:
        return _failure_report(
            report,
            "OPERATOR_STATUS_CHANGED",
            full_status_after.stdout,
        )
    if not report["worktree_registry_unchanged"]:
        return _failure_report(
            report,
            "WORKTREE_REGISTRY_CHANGED",
            worktrees_after.stdout,
        )

    report["implementation_environment_ready"] = (
        report["classification"] == ENVIRONMENT_READY
    )
    return report, EXIT_CODES[report["classification"]]
