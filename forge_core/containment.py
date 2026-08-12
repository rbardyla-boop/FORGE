from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import uuid
from typing import Any, Sequence

from .proposal import (
    ForgeProposalError,
    PATCH_LIMIT_BYTES,
    TRACE_LIMIT_BYTES,
    _assert_request_live,
    _load_request,
    submit_proposal,
    validate_trace_bytes,
)

BACKEND = "linux-docker-v0.1"
EXECUTION_ID = "execution-0001"
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
OUTPUT_LIMIT = 4096
WORKSPACE_MAX_FILES = 10000
WORKSPACE_MAX_BYTES = 64 * 1024 * 1024
PID_LIMIT = 64
MEMORY_LIMIT = "256m"
CPU_LIMIT = "1.0"
DEFAULT_TIMEOUT_SECONDS = 30.0


class ForgeContainmentError(RuntimeError):
    """W2 containment is unavailable, stale, unsafe, or produced invalid egress."""


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _git_text(git_exe: str, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [git_exe, "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


def _git_bytes(git_exe: str, root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [os.fsencode(git_exe), b"-C", os.fsencode(root), *[os.fsencode(arg) for arg in args]],
        capture_output=True,
        check=False,
        timeout=15,
    )


def _docker() -> str:
    if platform.system() != "Linux":
        raise ForgeContainmentError("CONTAINMENT_UNAVAILABLE: linux-docker-v0.1 requires Linux")
    docker = shutil.which("docker")
    if docker is None:
        raise ForgeContainmentError("CONTAINMENT_UNAVAILABLE: Docker CLI not found")
    version = subprocess.run(
        [docker, "version"],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if version.returncode != 0:
        raise ForgeContainmentError("CONTAINMENT_UNAVAILABLE: Docker daemon is unreachable")
    return docker


def _git(root: Path) -> tuple[str, str]:
    git_exe = shutil.which("git")
    if git_exe is None:
        raise ForgeContainmentError("Git is required for W2 containment")
    top = _git_text(git_exe, root, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root.resolve():
        raise ForgeContainmentError("W2 must run at the Git repository root")
    head = _git_text(git_exe, root, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0 or not head.stdout.strip():
        raise ForgeContainmentError("W2 requires a committed HEAD")
    return git_exe, head.stdout.strip()


def _validate_image_id(docker: str, image_id: str) -> str:
    if not IMAGE_ID_RE.fullmatch(image_id):
        raise ForgeContainmentError("provider execution requires an immutable local Docker image ID")
    inspected = subprocess.run(
        [docker, "image", "inspect", image_id, "--format", "{{.Id}}"],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if inspected.returncode != 0 or inspected.stdout.strip() != image_id:
        raise ForgeContainmentError("CONTAINMENT_UNAVAILABLE: provider image ID is not locally available")
    return image_id


def _bounded_file(path: Path) -> tuple[str, bool, int]:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            data = handle.read(OUTPUT_LIMIT)
    except OSError:
        return "", False, 0
    text = data.decode("utf-8", errors="replace")
    return text, size > OUTPUT_LIMIT, size


def _chmod_provider_workspace(workspace: Path) -> None:
    for current, dirs, files in os.walk(workspace, topdown=True, followlinks=False):
        current_path = Path(current)
        if not current_path.is_symlink():
            current_path.chmod(0o777)
        for name in dirs:
            path = current_path / name
            if not path.is_symlink():
                path.chmod(0o777)
        for name in files:
            path = current_path / name
            if path.is_symlink():
                continue
            mode = path.stat().st_mode
            path.chmod(0o777 if mode & stat.S_IXUSR else 0o666)


def _prepare_workspace(root: Path, baseline: str, request_bytes: bytes, parent: Path) -> tuple[Path, Path, Path, str]:
    git_exe, _ = _git(root)
    archive = parent / "baseline.tar"
    archived = subprocess.run(
        [git_exe, "-C", str(root), "archive", "--format=tar", "-o", str(archive), baseline],
        capture_output=True,
        check=False,
        timeout=20,
    )
    if archived.returncode != 0:
        raise ForgeContainmentError("unable to reconstruct W1 baseline snapshot")
    archive_bytes = archive.read_bytes()
    workspace = parent / "workspace"
    workspace.mkdir()
    with tarfile.open(archive, mode="r") as bundle:
        bundle.extractall(workspace, filter="data")
    if (workspace / ".forge").exists() or (workspace / ".forge").is_symlink():
        raise ForgeContainmentError("trusted baseline snapshot unexpectedly contains .forge")

    # Synthetic provider-local Git metadata is ergonomic only and is never trusted after execution.
    initialized = _git_text(git_exe, workspace, "init", "-q", "-b", "provider-workspace")
    if initialized.returncode != 0:
        raise ForgeContainmentError("unable to create disposable provider-local Git repository")
    _git_text(git_exe, workspace, "config", "user.name", "Forge Disposable Provider")
    _git_text(git_exe, workspace, "config", "user.email", "forge-provider@local.invalid")
    added = _git_text(git_exe, workspace, "add", "-A")
    committed = _git_text(git_exe, workspace, "commit", "-qm", "disposable baseline")
    if added.returncode != 0 or committed.returncode != 0:
        raise ForgeContainmentError("unable to freeze disposable provider-local baseline")
    _git_text(git_exe, workspace, "remote", "remove", "origin")
    _chmod_provider_workspace(workspace)

    input_dir = parent / "input"
    input_dir.mkdir()
    request_path = input_dir / "REQUEST.json"
    request_path.write_bytes(request_bytes)
    request_path.chmod(0o444)
    input_dir.chmod(0o555)

    output = parent / "output"
    output.mkdir()
    output.chmod(0o777)
    return workspace, request_path, output, _sha256(archive_bytes)


def _validate_workspace(workspace: Path) -> dict[str, Any]:
    root = workspace.resolve()
    file_count = 0
    total_bytes = 0
    paths: list[str] = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        rel_current = current_path.relative_to(root)
        if rel_current.parts and rel_current.parts[0] == ".git":
            dirs[:] = []
            continue
        dirs[:] = [name for name in dirs if not (rel_current == Path(".") and name == ".git")]
        for name in dirs + files:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if relative == ".forge" or relative.startswith(".forge/"):
                raise ForgeContainmentError("provider workspace created forbidden .forge authority path")
            metadata = os.lstat(path)
            file_count += 1
            if file_count > WORKSPACE_MAX_FILES:
                raise ForgeContainmentError("provider workspace exceeds file-count limit")
            if stat.S_ISLNK(metadata.st_mode):
                try:
                    path.resolve(strict=False).relative_to(root)
                except (OSError, ValueError) as exc:
                    raise ForgeContainmentError(f"provider workspace symlink escapes containment: {relative}") from exc
            elif stat.S_ISREG(metadata.st_mode):
                total_bytes += metadata.st_size
                if total_bytes > WORKSPACE_MAX_BYTES:
                    raise ForgeContainmentError("provider workspace exceeds byte limit")
            elif stat.S_ISDIR(metadata.st_mode):
                pass
            else:
                raise ForgeContainmentError(f"provider workspace contains unsupported special file: {relative}")
            paths.append(relative)
    return {"file_count": file_count, "total_bytes": total_bytes, "paths_checked": len(paths)}


def _clear_product_tree(collector: Path) -> None:
    for child in collector.iterdir():
        if child.name == ".git":
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)


def _copy_provider_tree(workspace: Path, collector: Path) -> None:
    for child in workspace.iterdir():
        if child.name == ".git":
            continue
        target = collector / child.name
        if child.is_symlink():
            target.symlink_to(os.readlink(child))
        elif child.is_dir():
            shutil.copytree(child, target, symlinks=True)
        else:
            shutil.copy2(child, target, follow_symlinks=False)


def _derive_patch(root: Path, baseline: str, workspace: Path, parent: Path) -> tuple[bytes, list[str]]:
    git_exe, _ = _git(root)
    collector = parent / "collector"
    added = _git_text(git_exe, root, "worktree", "add", "--detach", "--quiet", str(collector), baseline)
    if added.returncode != 0:
        raise ForgeContainmentError("trusted collector worktree creation failed")
    try:
        _clear_product_tree(collector)
        _copy_provider_tree(workspace, collector)
        staged = _git_text(git_exe, collector, "add", "-A")
        if staged.returncode != 0:
            raise ForgeContainmentError("trusted collector could not stage provider filesystem")
        diff = _git_bytes(
            git_exe,
            collector,
            "diff",
            "--cached",
            "--binary",
            "--full-index",
            "--no-ext-diff",
            "--no-renames",
        )
        names = _git_bytes(
            git_exe,
            collector,
            "diff",
            "--cached",
            "--name-only",
            "-z",
            "--no-renames",
        )
        if diff.returncode != 0 or names.returncode != 0:
            raise ForgeContainmentError("trusted collector could not derive provider patch")
        changed_paths = [os.fsdecode(item) for item in names.stdout.split(b"\x00") if item]
        if not diff.stdout or not changed_paths:
            raise ForgeContainmentError("provider produced no product change")
        if len(diff.stdout) > PATCH_LIMIT_BYTES:
            raise ForgeContainmentError("harness-derived provider patch exceeds W1 limit")
        return diff.stdout, changed_paths
    finally:
        _git_text(git_exe, root, "worktree", "remove", "--force", str(collector))


def _output_trace(output: Path) -> Path:
    entries = list(output.iterdir())
    if len(entries) != 1 or entries[0].name != "TRACE.json":
        names = sorted(item.name for item in entries)
        raise ForgeContainmentError(f"provider output shape is invalid: {names}")
    trace = entries[0]
    if trace.is_symlink() or not trace.is_file():
        raise ForgeContainmentError("provider TRACE.json must be a regular non-symlink file")
    metadata = trace.stat()
    if metadata.st_size > TRACE_LIMIT_BYTES:
        raise ForgeContainmentError("provider TRACE.json exceeds W1 limit")
    data = trace.read_bytes()
    validate_trace_bytes(data)
    return trace


def _profile_args(
    docker: str,
    image_id: str,
    name: str,
    workspace: Path,
    request_path: Path,
    output: Path,
    command: Sequence[str],
) -> list[str]:
    return [
        docker,
        "run",
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(PID_LIMIT),
        "--memory",
        MEMORY_LIMIT,
        "--cpus",
        CPU_LIMIT,
        "--user",
        "65534:65534",
        "--ipc",
        "private",
        "--mount",
        f"type=bind,src={workspace},dst=/workspace",
        "--mount",
        f"type=bind,src={request_path},dst=/input/REQUEST.json,readonly",
        "--mount",
        f"type=bind,src={output},dst=/output",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--env",
        "FORGE_REQUEST=/input/REQUEST.json",
        "--env",
        "FORGE_WORKSPACE=/workspace",
        "--env",
        "FORGE_OUTPUT=/output",
        image_id,
        *command,
    ]


def _run_container(
    docker: str,
    image_id: str,
    workspace: Path,
    request_path: Path,
    output: Path,
    command: Sequence[str],
    parent: Path,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    if not command or any(not isinstance(item, str) or not item or len(item) > 4096 for item in command):
        raise ForgeContainmentError("provider command must be a bounded non-empty argv list")
    name = f"forge-w2-{uuid.uuid4().hex[:16]}"
    argv = _profile_args(docker, image_id, name, workspace, request_path, output, command)
    stdout_file = parent / "provider.stdout"
    stderr_file = parent / "provider.stderr"
    timed_out = False
    with stdout_file.open("wb") as stdout_handle, stderr_file.open("wb") as stderr_handle:
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                shell=False,
                env=os.environ.copy(),
                start_new_session=True,
            )
        except OSError as exc:
            raise ForgeContainmentError(f"provider container launch failed: {exc}") from exc
        try:
            exit_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(
                [docker, "rm", "-f", name],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=15,
            )
            process.kill()
            exit_code = process.wait(timeout=10)
    stdout, stdout_truncated, stdout_bytes = _bounded_file(stdout_file)
    stderr, stderr_truncated, stderr_bytes = _bounded_file(stderr_file)
    return {
        "argv": argv[1:],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "container_name": name,
    }


def probe_backend(image_id: str, command: Sequence[str]) -> dict[str, Any]:
    docker = _docker()
    image_id = _validate_image_id(docker, image_id)
    with tempfile.TemporaryDirectory(prefix="forge-w2-probe-") as tmp:
        parent = Path(tmp)
        workspace = parent / "workspace"; workspace.mkdir(); workspace.chmod(0o777)
        request_path = parent / "REQUEST.json"; request_path.write_text("{}\n"); request_path.chmod(0o444)
        output = parent / "output"; output.mkdir(); output.chmod(0o777)
        result = _run_container(
            docker,
            image_id,
            workspace,
            request_path,
            output,
            command,
            parent,
            timeout_seconds=10,
        )
        if result["timed_out"] or result["exit_code"] != 0:
            raise ForgeContainmentError("CONTAINMENT_UNAVAILABLE: full-profile probe container failed")
        return {
            "backend": BACKEND,
            "classification": "CONTAINMENT_READY",
            "image_id": image_id,
            "profile": result["argv"],
        }


def execute_provider(
    root: Path,
    unit_id: str,
    image_id: str,
    command: Sequence[str],
    *,
    adapter_id: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], int]:
    root = root.resolve()
    request_dir, request = _load_request(root, unit_id)
    _assert_request_live(root, unit_id, request)
    execution_dir = request_dir / EXECUTION_ID
    if execution_dir.exists() or execution_dir.is_symlink():
        raise ForgeContainmentError("provider execution evidence already exists; refusing overwrite")
    if not isinstance(adapter_id, str) or not adapter_id.strip() or len(adapter_id) > 256:
        raise ForgeContainmentError("adapter_id must be a bounded non-empty string")
    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise ForgeContainmentError("provider timeout must be within (0, 300] seconds")

    docker = _docker()
    image_id = _validate_image_id(docker, image_id)
    git_exe, head = _git(root)
    if head != request["baseline_commit"]:
        raise ForgeContainmentError("W1 request baseline no longer matches repository HEAD")
    request_path = request_dir / "REQUEST.json"
    request_bytes = request_path.read_bytes()
    tracked_before = _git_text(git_exe, root, "status", "--porcelain=v1", "--untracked-files=no")
    worktrees_before = _git_text(git_exe, root, "worktree", "list", "--porcelain")
    if tracked_before.returncode != 0 or worktrees_before.returncode != 0:
        raise ForgeContainmentError("unable to snapshot operator preconditions")

    report: dict[str, Any] = {
        "schema": "forge.provider-execution.v0.1",
        "execution_id": EXECUTION_ID,
        "unit_id": unit_id,
        "request_digest": request["request_digest"],
        "baseline_commit": request["baseline_commit"],
        "backend": BACKEND,
        "image_id": image_id,
        "adapter_id": adapter_id.strip(),
        "execution_state": "PROVIDER_REJECTED",
        "completion_authority": "none",
        "candidate_authority": "none",
        "operator_status_unchanged": False,
        "worktree_registry_unchanged": False,
    }

    with tempfile.TemporaryDirectory(prefix="forge-w2-exec-") as tmp:
        parent = Path(tmp)
        workspace, copied_request, output, snapshot_digest = _prepare_workspace(
            root, request["baseline_commit"], request_bytes, parent
        )
        report["snapshot_sha256"] = snapshot_digest
        provider = _run_container(
            docker,
            image_id,
            workspace,
            copied_request,
            output,
            command,
            parent,
            timeout_seconds=timeout_seconds,
        )
        report["containment_profile"] = provider["argv"]
        report["provider_exit_code"] = provider["exit_code"]
        report["provider_timed_out"] = provider["timed_out"]
        for key in (
            "stdout",
            "stderr",
            "stdout_truncated",
            "stderr_truncated",
            "stdout_bytes",
            "stderr_bytes",
        ):
            report[key] = provider[key]

        if provider["timed_out"]:
            report["reason_code"] = "PROVIDER_TIMEOUT"
        elif provider["exit_code"] != 0:
            report["reason_code"] = "PROVIDER_NONZERO"
        else:
            try:
                trace = _output_trace(output)
                workspace_report = _validate_workspace(workspace)
                patch_bytes, derived_paths = _derive_patch(root, request["baseline_commit"], workspace, parent)
                patch = output / "PATCH.diff"
                patch.write_bytes(patch_bytes)
                _assert_request_live(root, unit_id, request)
                submitted = submit_proposal(root, unit_id, patch, trace)
                report["workspace_validation"] = workspace_report
                report["derived_changed_paths"] = derived_paths
                report["patch_sha256"] = _sha256(patch_bytes)
                report["patch_bytes"] = len(patch_bytes)
                trace_bytes = trace.read_bytes()
                report["trace_sha256"] = _sha256(trace_bytes)
                report["trace_bytes"] = len(trace_bytes)
                report["proposal_digest"] = submitted["proposal_digest"]
                report["proposal_state"] = submitted["proposal_state"]
                report["execution_state"] = "PROPOSAL_ACCEPTED"
                report["reason_code"] = "CONTAINED_PROVIDER_OUTPUT_ACCEPTED_BY_W1"
            except (ForgeContainmentError, ForgeProposalError, OSError, subprocess.TimeoutExpired) as exc:
                report["reason_code"] = "PROVIDER_OUTPUT_REJECTED"
                report["detail"] = str(exc)[:4096]

    tracked_after = _git_text(git_exe, root, "status", "--porcelain=v1", "--untracked-files=no")
    worktrees_after = _git_text(git_exe, root, "worktree", "list", "--porcelain")
    report["operator_status_unchanged"] = (
        tracked_after.returncode == 0 and tracked_after.stdout == tracked_before.stdout
    )
    report["worktree_registry_unchanged"] = (
        worktrees_after.returncode == 0 and worktrees_after.stdout == worktrees_before.stdout
    )
    if not report["operator_status_unchanged"] or not report["worktree_registry_unchanged"]:
        report["execution_state"] = "PROVIDER_REJECTED"
        report["reason_code"] = "OPERATOR_POSTCONDITION_CHANGED"

    execution_dir.mkdir()
    evidence_path = execution_dir / "EVIDENCE.json"
    evidence_path.write_bytes(_pretty(report))
    return report, 0 if report["execution_state"] == "PROPOSAL_ACCEPTED" else 3
