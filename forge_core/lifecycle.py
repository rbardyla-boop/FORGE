from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
from typing import Any

from .contract import ForgeContractError, verify_contract
from .doctor import (
    BLOCKED_EXTERNAL,
    CHECK_TIMEOUT_SECONDS,
    ENVIRONMENT_READY,
    EXTERNAL_PREFIX,
    FORGE_CANNOT_VERIFY,
    OUTPUT_LIMIT,
    PROJECT_BASELINE_FAILURE,
    run_doctor,
)

PATCH_LIMIT_BYTES = 1024 * 1024
RUN_SCHEMA = "forge.unit-attempt.v0.1"
RUNS_DIR = "runs"
ATTEMPT_NAME = "attempt-0001"

CANDIDATE_VERIFIED = "CANDIDATE_VERIFIED"
REPAIR_REQUIRED = "REPAIR_REQUIRED"


class ForgeLifecycleError(RuntimeError):
    """The F4 one-unit lifecycle cannot be started safely."""


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _bounded(value: str | None) -> tuple[str, bool]:
    text = value or ""
    if len(text) <= OUTPUT_LIMIT:
        return text, False
    return text[:OUTPUT_LIMIT], True


def _git_text(git_exe: str, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [git_exe, "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def _git_bytes(git_exe: str, root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [os.fsencode(git_exe), b"-C", os.fsencode(root), *[os.fsencode(arg) for arg in args]],
        capture_output=True,
        check=False,
        timeout=10,
    )


def _read_frozen_record(root: Path, unit_id: str) -> dict[str, Any]:
    before = verify_contract(root, unit_id)
    path = root / ".forge" / "contracts" / f"{unit_id}.json"
    if path.is_symlink():
        raise ForgeContractError("contract file must not be a symlink")
    try:
        raw = path.read_bytes()
        record = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ForgeContractError("verified contract became unreadable during F4 preflight") from exc
    after = verify_contract(root, unit_id)
    if (
        before["contract_digest"] != after["contract_digest"]
        or record.get("contract_digest") != after["contract_digest"]
        or path.read_bytes() != raw
    ):
        raise ForgeContractError("contract changed during F4 preflight")
    return record


def _load_patch(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if path.is_symlink():
            raise ForgeLifecycleError("patch file must not be a symlink") from exc
        raise ForgeLifecycleError("patch file is unreadable") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ForgeLifecycleError("patch file must be a regular file")
        if metadata.st_size > PATCH_LIMIT_BYTES:
            raise ForgeLifecycleError("patch file exceeds the F4 1 MiB limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, PATCH_LIMIT_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > PATCH_LIMIT_BYTES:
                raise ForgeLifecycleError("patch file exceeds the F4 1 MiB limit")
        return b"".join(chunks)
    except OSError as exc:
        raise ForgeLifecycleError("patch file is unreadable") from exc
    finally:
        os.close(descriptor)


def _attempt_dir(root: Path, unit_id: str) -> Path:
    forge_dir = root / ".forge"
    if forge_dir.is_symlink() or not forge_dir.is_dir():
        raise ForgeLifecycleError("canonical .forge directory is missing or unsafe")
    runs = forge_dir / RUNS_DIR
    if runs.is_symlink() or (runs.exists() and not runs.is_dir()):
        raise ForgeLifecycleError("Forge runs directory is unsafe")
    unit_dir = runs / unit_id
    if unit_dir.is_symlink() or (unit_dir.exists() and not unit_dir.is_dir()):
        raise ForgeLifecycleError("Forge unit runs directory is unsafe")
    return unit_dir / ATTEMPT_NAME


def _path_matches(path: str, pattern: str) -> bool:
    # Anchored POSIX glob semantics: * never crosses '/', ** may cross '/'.
    regex: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                regex.append(".*")
                index += 2
                continue
            regex.append("[^/]*")
        elif char == "?":
            regex.append("[^/]")
        else:
            regex.append(re.escape(char))
        index += 1
    regex.append("$")
    return re.fullmatch("".join(regex), path) is not None


def _tracked_symlink_safety(
    git_exe: str, worktree: Path
) -> tuple[str | None, list[str], str]:
    try:
        indexed = _git_text(git_exe, worktree, "ls-files", "-z", "-s")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "SYMLINK_INDEX_FAILED", [], str(exc)
    if indexed.returncode != 0:
        return "SYMLINK_INDEX_FAILED", [], indexed.stderr

    unsafe: list[str] = []
    unsupported: list[str] = []
    root = worktree.resolve()
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
            resolved.relative_to(root)
        except (OSError, ValueError):
            unsafe.append(relative)
    if unsupported:
        return "TRACKED_SYMLINK_UNSUPPORTED", sorted(unsupported), ""
    if unsafe:
        return "TRACKED_SYMLINK_ESCAPE", sorted(unsafe), ""
    return None, [], ""


def _scope_violations(paths: list[str], authority: dict[str, Any]) -> list[dict[str, str]]:
    allowed = authority["scope"]["allowed_paths"]
    forbidden = authority["scope"]["forbidden_paths"]
    violations: list[dict[str, str]] = []
    for path in paths:
        if path == ".forge" or path.startswith(".forge/"):
            violations.append({"path": path, "reason": "FORGE_AUTHORITY_PATH"})
            continue
        if not any(_path_matches(path, pattern) for pattern in allowed):
            violations.append({"path": path, "reason": "OUTSIDE_ALLOWED_PATHS"})
            continue
        if any(_path_matches(path, pattern) for pattern in forbidden):
            violations.append({"path": path, "reason": "MATCHES_FORBIDDEN_PATH"})
    return violations


def _execute_required_check(
    argv: list[str], worktree: Path, timeout_seconds: float
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "argv": argv,
        "classification": FORGE_CANNOT_VERIFY,
        "exit_code": None,
        "reason_code": "CHECK_LAUNCH_FAILED",
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
    }
    env = os.environ.copy()
    env["PWD"] = str(worktree)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    try:
        process = subprocess.Popen(
            argv,
            cwd=worktree,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=(os.name == "posix"),
        )
    except FileNotFoundError as exc:
        result["reason_code"] = "EXECUTABLE_NOT_FOUND"
        result["stderr"] = str(exc)
        return result
    except PermissionError as exc:
        result["reason_code"] = "EXECUTABLE_NOT_EXECUTABLE"
        result["stderr"] = str(exc)
        return result
    except OSError as exc:
        result["stderr"] = str(exc)
        return result

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
        result.update(
            {
                "exit_code": process.returncode,
                "reason_code": "CHECK_TIMEOUT",
                "stdout": out,
                "stderr": err,
                "stdout_truncated": out_truncated,
                "stderr_truncated": err_truncated,
            }
        )
        return result

    out, out_truncated = _bounded(stdout)
    err, err_truncated = _bounded(stderr)
    result.update(
        {
            "exit_code": process.returncode,
            "stdout": out,
            "stderr": err,
            "stdout_truncated": out_truncated,
            "stderr_truncated": err_truncated,
        }
    )
    if process.returncode == 0:
        result["classification"] = ENVIRONMENT_READY
        result["reason_code"] = "CHECK_PASS"
    elif process.returncode == 75 and any(
        line.startswith(EXTERNAL_PREFIX) for line in stderr.splitlines()
    ):
        result["classification"] = BLOCKED_EXTERNAL
        result["reason_code"] = "EXTERNAL_DEPENDENCY_REPORTED"
    else:
        result["classification"] = PROJECT_BASELINE_FAILURE
        result["reason_code"] = "CHECK_NONZERO"
    return result


def _persist_attempt(
    attempt_dir: Path, evidence: dict[str, Any], applied_diff: bytes | None
) -> None:
    if attempt_dir.exists() or attempt_dir.is_symlink():
        raise ForgeLifecycleError("F4 attempt evidence already exists; refusing overwrite")
    parent = attempt_dir.parent
    runs = parent.parent
    if runs.is_symlink() or parent.is_symlink():
        raise ForgeLifecycleError("Forge evidence parent is unsafe")
    runs.mkdir(exist_ok=True)
    parent.mkdir(exist_ok=True)
    attempt_dir.mkdir(exist_ok=False)
    if applied_diff is not None:
        (attempt_dir / "APPLIED.diff").write_bytes(applied_diff)
    encoded = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (attempt_dir / "EVIDENCE.json").write_bytes(encoded)


def run_unit_attempt(
    root: Path,
    unit_id: str,
    patch_file: Path,
    *,
    timeout_seconds: float = CHECK_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], int]:
    root = root.resolve()
    record = _read_frozen_record(root, unit_id)
    attempt_dir = _attempt_dir(root, unit_id)
    if attempt_dir.exists() or attempt_dir.is_symlink():
        raise ForgeLifecycleError("F4 attempt already exists for unit")

    doctor_report, doctor_exit = run_doctor(root, unit_id)
    if doctor_exit != 0 or doctor_report["classification"] != ENVIRONMENT_READY:
        raise ForgeLifecycleError(
            f"Doctor prerequisite not ready: {doctor_report['classification']}"
        )
    post_doctor_contract = verify_contract(root, unit_id)
    if (
        post_doctor_contract["revision"] != record["revision"]
        or post_doctor_contract["contract_digest"] != record["contract_digest"]
    ):
        raise ForgeLifecycleError("contract changed during Doctor prerequisite")

    patch_bytes = _load_patch(patch_file)
    patch_digest = _sha256(patch_bytes)
    baseline_commit = doctor_report["baseline_commit"]
    contract_digest = record["contract_digest"]
    required_checks = [c for c in record["authority"]["checks"] if c["required"]]
    advisory_ids = [c["id"] for c in record["authority"]["checks"] if not c["required"]]

    git_exe = shutil.which("git")
    if git_exe is None:
        raise ForgeLifecycleError("Git became unavailable after Doctor preflight")

    tracked_before = _git_text(
        git_exe, root, "status", "--porcelain=v1", "--untracked-files=no"
    )
    worktrees_before = _git_text(git_exe, root, "worktree", "list", "--porcelain")
    if tracked_before.returncode != 0 or worktrees_before.returncode != 0:
        raise ForgeLifecycleError("unable to snapshot operator postconditions")

    temp_parent = Path(tempfile.mkdtemp(prefix="forge-unit-"))
    disposable = temp_parent / "worktree"
    patch_copy = temp_parent / "input.patch"
    patch_copy.write_bytes(patch_bytes)
    worktree_added = False
    cleanup_problem: str | None = None

    terminal_state = REPAIR_REQUIRED
    reason_code = "ATTEMPT_NOT_EVALUATED"
    applied_diff: bytes | None = None
    changed_paths: list[str] = []
    scope_violations: list[dict[str, str]] = []
    check_results: list[dict[str, Any]] = []
    checks_not_run: list[str] = []

    try:
        added = _git_text(
            git_exe,
            root,
            "worktree",
            "add",
            "--detach",
            "--quiet",
            str(disposable),
            baseline_commit,
        )
        if added.returncode != 0:
            reason_code = "WORKTREE_CREATE_FAILED"
        else:
            worktree_added = True
            if not patch_bytes:
                reason_code = "EMPTY_PATCH"
            else:
                patch_check = subprocess.run(
                    [
                        git_exe,
                        "-C",
                        str(disposable),
                        "apply",
                        "--check",
                        "--whitespace=error-all",
                        str(patch_copy),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                if patch_check.returncode != 0:
                    reason_code = "PATCH_APPLY_CHECK_FAILED"
                else:
                    applied = subprocess.run(
                        [
                            git_exe,
                            "-C",
                            str(disposable),
                            "apply",
                            "--index",
                            "--whitespace=error-all",
                            str(patch_copy),
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    if applied.returncode != 0:
                        reason_code = "PATCH_APPLY_FAILED"
                    else:
                        names = _git_bytes(
                            git_exe,
                            disposable,
                            "diff",
                            "--cached",
                            "--name-only",
                            "-z",
                            "--no-renames",
                        )
                        diff_result = _git_bytes(
                            git_exe,
                            disposable,
                            "diff",
                            "--cached",
                            "--binary",
                            "--full-index",
                            "--no-ext-diff",
                            "--no-renames",
                        )
                        if names.returncode != 0 or diff_result.returncode != 0:
                            reason_code = "APPLIED_DIFF_READ_FAILED"
                        else:
                            changed_paths = [
                                os.fsdecode(item)
                                for item in names.stdout.split(b"\x00")
                                if item
                            ]
                            applied_diff = diff_result.stdout
                            if not changed_paths or not applied_diff:
                                reason_code = "EMPTY_APPLIED_DIFF"
                            else:
                                scope_violations = _scope_violations(
                                    changed_paths, record["authority"]
                                )
                                if scope_violations:
                                    reason_code = "SCOPE_VIOLATION"
                                else:
                                    symlink_reason, unsafe_symlinks, symlink_detail = _tracked_symlink_safety(
                                        git_exe, disposable
                                    )
                                    if symlink_reason is not None:
                                        reason_code = symlink_reason
                                        scope_violations = [
                                            {"path": path, "reason": symlink_reason}
                                            for path in unsafe_symlinks
                                        ]
                                        if symlink_detail:
                                            infra_detail, infra_truncated = _bounded(symlink_detail)
                                    else:
                                        patch_status = _git_bytes(
                                            git_exe,
                                            disposable,
                                            "status",
                                            "--porcelain=v1",
                                            "-z",
                                            "--untracked-files=no",
                                        )
                                        if patch_status.returncode != 0:
                                            reason_code = "PATCH_STATUS_READ_FAILED"
                                        else:
                                            for index, check in enumerate(required_checks):
                                                check_result = _execute_required_check(
                                                    check["argv"], disposable, timeout_seconds
                                                )
                                                check_result["id"] = check["id"]
                                                current_staged = _git_bytes(
                                                    git_exe,
                                                    disposable,
                                                    "diff",
                                                    "--cached",
                                                    "--binary",
                                                    "--full-index",
                                                    "--no-ext-diff",
                                                    "--no-renames",
                                                )
                                                current_unstaged = _git_bytes(
                                                    git_exe,
                                                    disposable,
                                                    "diff",
                                                    "--binary",
                                                    "--full-index",
                                                    "--no-ext-diff",
                                                    "--no-renames",
                                                )
                                                if (
                                                    current_staged.returncode != 0
                                                    or current_unstaged.returncode != 0
                                                ):
                                                    check_result["classification"] = FORGE_CANNOT_VERIFY
                                                    check_result["reason_code"] = "PATCHED_DIFF_READ_FAILED"
                                                elif (
                                                    current_staged.stdout != applied_diff
                                                    or current_unstaged.stdout
                                                ):
                                                    check_result["classification"] = FORGE_CANNOT_VERIFY
                                                    check_result["reason_code"] = "CHECK_MUTATED_PATCHED_STATE"
                                                    check_result["tracked_state_mutated"] = True
                                                check_results.append(check_result)
                                                if check_result["classification"] == FORGE_CANNOT_VERIFY:
                                                    checks_not_run = [
                                                        item["id"]
                                                        for item in required_checks[index + 1 :]
                                                    ]
                                                    break

                                            classifications = [
                                                result["classification"] for result in check_results
                                            ]
                                            if FORGE_CANNOT_VERIFY in classifications:
                                                terminal_state = REPAIR_REQUIRED
                                                reason_code = "VERIFICATION_FAILURE"
                                            elif BLOCKED_EXTERNAL in classifications:
                                                terminal_state = BLOCKED_EXTERNAL
                                                reason_code = "EXTERNAL_DEPENDENCY_REPORTED"
                                            elif PROJECT_BASELINE_FAILURE in classifications:
                                                terminal_state = REPAIR_REQUIRED
                                                reason_code = "REQUIRED_CHECK_FAILED"
                                            elif (
                                                len(check_results) == len(required_checks)
                                                and classifications
                                                and all(
                                                    c == ENVIRONMENT_READY
                                                    for c in classifications
                                                )
                                            ):
                                                terminal_state = CANDIDATE_VERIFIED
                                                reason_code = "ALL_REQUIRED_CHECKS_PASS"
                                            else:
                                                terminal_state = REPAIR_REQUIRED
                                                reason_code = "INCOMPLETE_CHECK_EVIDENCE"
    except (OSError, subprocess.TimeoutExpired) as exc:
        terminal_state = REPAIR_REQUIRED
        reason_code = "ATTEMPT_INFRASTRUCTURE_FAILURE"
        infra_detail, infra_truncated = _bounded(str(exc))
    finally:
        if worktree_added:
            try:
                removed = _git_text(
                    git_exe, root, "worktree", "remove", "--force", str(disposable)
                )
                if removed.returncode != 0:
                    cleanup_problem = "WORKTREE_REMOVE_FAILED"
            except (OSError, subprocess.TimeoutExpired):
                cleanup_problem = "WORKTREE_REMOVE_FAILED"
        shutil.rmtree(temp_parent, ignore_errors=True)
        if cleanup_problem:
            try:
                _git_text(git_exe, root, "worktree", "prune")
            except (OSError, subprocess.TimeoutExpired):
                pass

    tracked_after = _git_text(
        git_exe, root, "status", "--porcelain=v1", "--untracked-files=no"
    )
    worktrees_after = _git_text(git_exe, root, "worktree", "list", "--porcelain")
    operator_status_unchanged = (
        tracked_after.returncode == 0 and tracked_after.stdout == tracked_before.stdout
    )
    worktree_registry_unchanged = (
        worktrees_after.returncode == 0
        and worktrees_after.stdout == worktrees_before.stdout
    )
    if cleanup_problem or not operator_status_unchanged or not worktree_registry_unchanged:
        terminal_state = REPAIR_REQUIRED
        reason_code = cleanup_problem or (
            "OPERATOR_STATUS_CHANGED"
            if not operator_status_unchanged
            else "WORKTREE_REGISTRY_CHANGED"
        )

    contract_postcondition_unchanged = False
    try:
        final_contract = verify_contract(root, unit_id)
        contract_postcondition_unchanged = (
            final_contract["revision"] == record["revision"]
            and final_contract["contract_digest"] == contract_digest
        )
    except ForgeContractError as exc:
        contract_postcondition_detail, contract_postcondition_truncated = _bounded(str(exc))

    if not contract_postcondition_unchanged:
        terminal_state = REPAIR_REQUIRED
        reason_code = "CONTRACT_CHANGED_DURING_ATTEMPT"

    evidence: dict[str, Any] = {
        "schema": RUN_SCHEMA,
        "unit_id": unit_id,
        "attempt": ATTEMPT_NAME,
        "contract_revision": record["revision"],
        "contract_digest": contract_digest,
        "baseline_commit": baseline_commit,
        "input_patch_sha256": patch_digest,
        "input_patch_bytes": len(patch_bytes),
        "applied_diff_sha256": _sha256(applied_diff) if applied_diff is not None else None,
        "applied_diff_bytes": len(applied_diff) if applied_diff is not None else 0,
        "changed_paths": changed_paths,
        "scope_violations": scope_violations,
        "required_checks": check_results,
        "required_checks_not_run": checks_not_run,
        "advisory_checks_skipped": advisory_ids,
        "terminal_state": terminal_state,
        "reason_code": reason_code,
        "operator_status_unchanged": operator_status_unchanged,
        "worktree_registry_unchanged": worktree_registry_unchanged,
        "contract_postcondition_unchanged": contract_postcondition_unchanged,
        "completion_authority": "harness",
    }
    if "infra_detail" in locals():
        evidence["detail"] = infra_detail
        evidence["detail_truncated"] = infra_truncated
    if "contract_postcondition_detail" in locals():
        evidence["contract_postcondition_detail"] = contract_postcondition_detail
        evidence["contract_postcondition_detail_truncated"] = contract_postcondition_truncated

    _persist_attempt(attempt_dir, evidence, applied_diff)
    return evidence, 0 if terminal_state == CANDIDATE_VERIFIED else (5 if terminal_state == BLOCKED_EXTERNAL else 3)
