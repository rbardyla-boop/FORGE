from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Sequence

from .proposal import (
    ForgeProposalError,
    REQUEST_ID,
    TRACE_SCHEMA,
    _assert_request_live,
    _load_request,
)

ADAPTER_SCHEMA = "forge.codex-adapter.v0.1"
EXECUTION_ID = "codex-execution-0001"
VERSION_RE = re.compile(r"^codex-cli [0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
EXECUTABLE_MAX_BYTES = 256 * 1024 * 1024
VERSION_MAX_BYTES = 4096
PROMPT_MAX_BYTES = 512 * 1024
STDOUT_MAX_BYTES = 1024 * 1024
STDERR_MAX_BYTES = 256 * 1024
JSONL_LINE_MAX_BYTES = 64 * 1024
JSONL_MAX_EVENTS = 1024
DEFAULT_TIMEOUT_SECONDS = 60.0

CREDENTIAL_ENV_KEYS = {
    "CODEX_API_KEY",
    "OPENAI_API_KEY",
    "CODEX_ACCESS_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
}

FROZEN_EXEC_ARGS = (
    "exec",
    "--ephemeral",
    "--json",
    "--sandbox",
    "workspace-write",
    "--ask-for-approval",
    "never",
    "--ignore-user-config",
    "--ignore-rules",
    "--color",
    "never",
)

FORBIDDEN_ARG_TOKENS = {
    "--yolo",
    "--dangerously-bypass-approvals-and-sandbox",
    "danger-full-access",
    "--full-auto",
    "--dangerously-bypass-hook-trust",
    "--skip-git-repo-check",
    "--profile",
    "--add-dir",
    "--image",
    "--mcp",
    "--plugin",
    "--cloud",
    "resume",
    "-c",
    "--config",
}


class ForgeCodexAdapterError(RuntimeError):
    """W3 Codex adapter authority is stale, unsafe, malformed, or unverified."""


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _git_text(git_exe: str, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [git_exe, "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


def _git(root: Path) -> tuple[str, str]:
    git_exe = shutil.which("git")
    if git_exe is None:
        raise ForgeCodexAdapterError("Git is required for W3 adapter authority")
    top = _git_text(git_exe, root, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root.resolve():
        raise ForgeCodexAdapterError("W3 must run at the operator Git repository root")
    head = _git_text(git_exe, root, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0 or not head.stdout.strip():
        raise ForgeCodexAdapterError("W3 requires a committed operator HEAD")
    return git_exe, head.stdout.strip()


def _read_regular_nofollow(path: Path, *, limit: int, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if path.is_symlink():
            raise ForgeCodexAdapterError(f"{label} must not be a symlink") from exc
        raise ForgeCodexAdapterError(f"{label} is unreadable") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ForgeCodexAdapterError(f"{label} must be a regular file")
        if metadata.st_size > limit:
            raise ForgeCodexAdapterError(f"{label} exceeds {limit} bytes")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise ForgeCodexAdapterError(f"{label} exceeds {limit} bytes")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _executable_bytes(path: Path) -> bytes:
    if not path.is_absolute():
        raise ForgeCodexAdapterError("Codex executable path must be absolute")
    if path.is_symlink():
        raise ForgeCodexAdapterError("Codex executable must not be a symlink")
    data = _read_regular_nofollow(path, limit=EXECUTABLE_MAX_BYTES, label="Codex executable")
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise ForgeCodexAdapterError("Codex executable metadata is unreadable") from exc
    if not mode & stat.S_IXUSR and not mode & stat.S_IXGRP and not mode & stat.S_IXOTH:
        raise ForgeCodexAdapterError("Codex executable is not executable")
    return data


def _safe_process_env(parent: Path, *, fixture_mode: str | None = None) -> dict[str, str]:
    home = parent / "home"
    codex_home = parent / "codex-home"
    tmp = parent / "tmp"
    home.mkdir(mode=0o700)
    codex_home.mkdir(mode=0o700)
    tmp.mkdir(mode=0o700)
    env = {
        "HOME": str(home),
        "CODEX_HOME": str(codex_home),
        "TMPDIR": str(tmp),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TERM": "dumb",
        "NO_COLOR": "1",
    }
    if fixture_mode is not None:
        if not isinstance(fixture_mode, str) or not fixture_mode or len(fixture_mode) > 128:
            raise ForgeCodexAdapterError("fixture mode must be a bounded non-empty string")
        env["FORGE_W3_FIXTURE_MODE"] = fixture_mode
    if CREDENTIAL_ENV_KEYS.intersection(env):
        raise ForgeCodexAdapterError("credential environment leaked into W3 provider environment")
    return env


def _bounded_process_output(path: Path, *, limit: int, label: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ForgeCodexAdapterError(f"{label} is unavailable") from exc
    if size > limit:
        raise ForgeCodexAdapterError(f"{label} exceeds {limit} bytes")
    return _read_regular_nofollow(path, limit=limit, label=label)


def inspect_codex_executable(executable: Path) -> dict[str, Any]:
    executable = executable.resolve(strict=False) if not executable.is_symlink() else executable
    first = _executable_bytes(executable)
    digest = _sha256(first)
    with tempfile.TemporaryDirectory(prefix="forge-w3-inspect-") as tmp_name:
        parent = Path(tmp_name)
        env = _safe_process_env(parent)
        stdout = parent / "stdout"
        stderr = parent / "stderr"
        with stdout.open("wb") as out_handle, stderr.open("wb") as err_handle:
            try:
                process = subprocess.run(
                    [str(executable), "--version"],
                    stdin=subprocess.DEVNULL,
                    stdout=out_handle,
                    stderr=err_handle,
                    shell=False,
                    env=env,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ForgeCodexAdapterError(f"Codex --version failed: {exc}") from exc
        if process.returncode != 0:
            raise ForgeCodexAdapterError("Codex --version returned nonzero")
        raw_version = _bounded_process_output(stdout, limit=VERSION_MAX_BYTES, label="Codex version stdout")
        raw_stderr = _bounded_process_output(stderr, limit=VERSION_MAX_BYTES, label="Codex version stderr")
        if raw_stderr:
            raise ForgeCodexAdapterError("Codex --version wrote unexpected stderr")
        try:
            version = raw_version.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise ForgeCodexAdapterError("Codex --version is not UTF-8") from exc
        if not VERSION_RE.fullmatch(version):
            raise ForgeCodexAdapterError("Codex --version does not match frozen interface pattern")
    second = _executable_bytes(executable)
    if _sha256(second) != digest:
        raise ForgeCodexAdapterError("Codex executable changed during fingerprint inspection")
    return {
        "schema": "forge.codex-executable.v0.1",
        "path": str(executable),
        "sha256": digest,
        "bytes": len(first),
        "version": version,
    }


def _verify_manifest(executable: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    expected = {"schema", "path", "sha256", "bytes", "version"}
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise ForgeCodexAdapterError("Codex executable manifest schema is invalid")
    current = inspect_codex_executable(executable)
    if current != manifest:
        raise ForgeCodexAdapterError("Codex executable no longer matches frozen manifest")
    return current


def build_codex_argv(executable: Path, workspace: Path) -> list[str]:
    if not executable.is_absolute():
        raise ForgeCodexAdapterError("Codex executable path must be absolute")
    if not workspace.is_absolute():
        raise ForgeCodexAdapterError("Codex workspace path must be absolute")
    argv = [str(executable), *FROZEN_EXEC_ARGS, "--cd", str(workspace), "-"]
    lowered = {item.lower() for item in argv[1:]}
    if FORBIDDEN_ARG_TOKENS.intersection(lowered):
        raise ForgeCodexAdapterError("frozen Codex argv contains a forbidden authority token")
    return argv


def _build_prompt(request: dict[str, Any]) -> bytes:
    authority = request.get("authority")
    if not isinstance(authority, dict):
        raise ForgeCodexAdapterError("W1 request authority is malformed")
    payload = {
        "instruction": (
            "Implement only the frozen task in the disposable workspace. "
            "Do not change the task contract, do not claim completion authority, and do not attempt release/merge/deploy."
        ),
        "request_digest": request.get("request_digest"),
        "contract_digest": request.get("contract_digest"),
        "baseline_commit": request.get("baseline_commit"),
        "authority": authority,
    }
    prompt = _pretty(payload)
    if len(prompt) > PROMPT_MAX_BYTES:
        raise ForgeCodexAdapterError("Codex prompt exceeds W3 bound")
    return prompt


def _parse_jsonl(raw: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(raw) > STDOUT_MAX_BYTES:
        raise ForgeCodexAdapterError("Codex JSONL stdout exceeds W3 bound")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ForgeCodexAdapterError("Codex JSONL stdout is not UTF-8") from exc
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        encoded = line.encode("utf-8")
        if len(encoded) > JSONL_LINE_MAX_BYTES:
            raise ForgeCodexAdapterError(f"Codex JSONL line {line_number} exceeds W3 bound")
        if len(events) >= JSONL_MAX_EVENTS:
            raise ForgeCodexAdapterError("Codex JSONL event count exceeds W3 bound")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ForgeCodexAdapterError(f"Codex JSONL line {line_number} is malformed") from exc
        if not isinstance(value, dict):
            raise ForgeCodexAdapterError(f"Codex JSONL line {line_number} is not an object")
        events.append(value)
    completed = sum(event.get("type") == "turn.completed" for event in events)
    failed = sum(event.get("type") == "turn.failed" for event in events)
    errors = sum(event.get("type") == "error" for event in events)
    if failed or errors:
        raise ForgeCodexAdapterError("Codex JSONL reports failed/error terminal state")
    if completed != 1:
        raise ForgeCodexAdapterError("Codex JSONL must contain exactly one turn.completed event")
    return events, {
        "event_count": len(events),
        "event_types": [str(event.get("type", "<unknown>"))[:256] for event in events],
        "completed_events": completed,
        "failed_events": failed,
        "error_events": errors,
    }


def events_to_w1_trace(events: Sequence[dict[str, Any]], *, adapter_id: str) -> bytes:
    event_types = [str(event.get("type", "unknown"))[:128] for event in events[:32]]
    trace = {
        "schema": TRACE_SCHEMA,
        "adapter": adapter_id[:256],
        "provider_run_id": EXECUTION_ID,
        "events": [
            {
                "seq": 1,
                "kind": "PLAN",
                "summary": "Codex adapter invoked frozen non-interactive task contract",
            },
            {
                "seq": 2,
                "kind": "EDIT",
                "summary": "Observed Codex JSONL event types: " + ", ".join(event_types),
            },
        ],
    }
    return _pretty(trace)


def _execution_dir(root: Path, unit_id: str) -> Path:
    return root / ".forge" / "proposals" / unit_id / REQUEST_ID / EXECUTION_ID


def _validate_workspace_precondition(root: Path, workspace: Path, baseline: str) -> None:
    workspace = workspace.resolve()
    if workspace == root or root in workspace.parents:
        raise ForgeCodexAdapterError("Codex workspace must not be the operator repository or a child of it")
    if workspace.is_symlink() or not workspace.is_dir():
        raise ForgeCodexAdapterError("Codex workspace must be a regular directory")
    if (workspace / ".forge").exists() or (workspace / ".forge").is_symlink():
        raise ForgeCodexAdapterError("Codex workspace must not contain Forge authority")
    git_exe = shutil.which("git")
    if git_exe is None:
        raise ForgeCodexAdapterError("Git is required in Codex fixture workspace")
    head = _git_text(git_exe, workspace, "rev-parse", "--verify", "HEAD")
    status = _git_text(git_exe, workspace, "status", "--porcelain=v1", "--untracked-files=all")
    if head.returncode != 0 or head.stdout.strip() != baseline:
        raise ForgeCodexAdapterError("Codex workspace does not match W1 baseline")
    if status.returncode != 0 or status.stdout:
        raise ForgeCodexAdapterError("Codex workspace must begin clean")


def _persist_evidence(path: Path, report: dict[str, Any]) -> None:
    parent = path.parent
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ForgeCodexAdapterError("Codex adapter evidence directory is unsafe")
    if parent.exists():
        raise ForgeCodexAdapterError("Codex adapter execution evidence already exists; refusing overwrite")
    parent.mkdir()
    path.write_bytes(_pretty(report))


def execute_codex_adapter(
    root: Path,
    unit_id: str,
    executable: Path,
    manifest: dict[str, Any],
    workspace: Path,
    *,
    adapter_id: str = "codex-cli",
    fixture_mode: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], int]:
    root = root.resolve()
    workspace = workspace.resolve()
    request_dir, request = _load_request(root, unit_id)
    _assert_request_live(root, unit_id, request)
    if not isinstance(adapter_id, str) or not adapter_id.strip() or len(adapter_id) > 256:
        raise ForgeCodexAdapterError("adapter_id must be a bounded non-empty string")
    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise ForgeCodexAdapterError("Codex timeout must be within (0, 300] seconds")
    evidence_path = _execution_dir(root, unit_id) / "EVIDENCE.json"
    if evidence_path.parent.exists() or evidence_path.parent.is_symlink():
        raise ForgeCodexAdapterError("Codex adapter execution evidence already exists; refusing overwrite")

    git_exe, operator_head = _git(root)
    if operator_head != request.get("baseline_commit"):
        raise ForgeCodexAdapterError("W1 request baseline no longer matches operator HEAD")
    _validate_workspace_precondition(root, workspace, str(request["baseline_commit"]))
    tracked_before = _git_text(git_exe, root, "status", "--porcelain=v1", "--untracked-files=no")
    worktrees_before = _git_text(git_exe, root, "worktree", "list", "--porcelain")
    if tracked_before.returncode != 0 or worktrees_before.returncode != 0:
        raise ForgeCodexAdapterError("unable to snapshot operator preconditions")

    current = _verify_manifest(executable, manifest)
    prompt = _build_prompt(request)
    argv = build_codex_argv(Path(current["path"]), workspace)
    report: dict[str, Any] = {
        "schema": ADAPTER_SCHEMA,
        "execution_id": EXECUTION_ID,
        "unit_id": unit_id,
        "request_digest": request["request_digest"],
        "contract_digest": request["contract_digest"],
        "baseline_commit": request["baseline_commit"],
        "adapter_id": adapter_id.strip(),
        "executable": current,
        "argv": argv[1:],
        "prompt_sha256": _sha256(prompt),
        "prompt_bytes": len(prompt),
        "adapter_state": "CODEX_ADAPTER_REJECTED",
        "completion_authority": "none",
        "candidate_authority": "none",
        "f4_f5_handoff": False,
        "operator_status_unchanged": False,
        "worktree_registry_unchanged": False,
        "real_remote_request": False,
        "credential_bridge": False,
        "network_bridge": False,
    }

    with tempfile.TemporaryDirectory(prefix="forge-w3-run-") as tmp_name:
        parent = Path(tmp_name)
        env = _safe_process_env(parent, fixture_mode=fixture_mode)
        report["provider_environment_keys"] = sorted(env)
        stdout_path = parent / "stdout.jsonl"
        stderr_path = parent / "stderr.txt"
        timed_out = False
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            try:
                process = subprocess.Popen(
                    argv,
                    stdin=subprocess.PIPE,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    shell=False,
                    env=env,
                    start_new_session=True,
                )
            except OSError as exc:
                raise ForgeCodexAdapterError(f"Codex adapter launch failed: {exc}") from exc
            try:
                process.communicate(input=prompt, timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, 9)
                except (OSError, ProcessLookupError):
                    process.kill()
                process.wait(timeout=10)
        report["provider_exit_code"] = process.returncode
        report["provider_timed_out"] = timed_out

        after_bytes = _executable_bytes(Path(current["path"]))
        after_digest = _sha256(after_bytes)
        report["executable_sha256_after"] = after_digest
        if after_digest != current["sha256"]:
            report["reason_code"] = "CODEX_EXECUTABLE_CHANGED"
        elif timed_out:
            report["reason_code"] = "CODEX_TIMEOUT"
        elif process.returncode != 0:
            report["reason_code"] = "CODEX_NONZERO"
        else:
            try:
                stdout = _bounded_process_output(
                    stdout_path, limit=STDOUT_MAX_BYTES, label="Codex JSONL stdout"
                )
                stderr = _bounded_process_output(
                    stderr_path, limit=STDERR_MAX_BYTES, label="Codex stderr"
                )
                events, parsed = _parse_jsonl(stdout)
                _assert_request_live(root, unit_id, request)
                report["stdout_sha256"] = _sha256(stdout)
                report["stdout_bytes"] = len(stdout)
                report["stderr_sha256"] = _sha256(stderr)
                report["stderr_bytes"] = len(stderr)
                report["jsonl"] = parsed
                report["trace_sha256"] = _sha256(
                    events_to_w1_trace(events, adapter_id=adapter_id.strip())
                )
                report["adapter_state"] = "CODEX_ADAPTER_ACCEPTED"
                report["reason_code"] = "CODEX_JSONL_ACCEPTED"
            except (ForgeCodexAdapterError, ForgeProposalError, OSError) as exc:
                report["reason_code"] = "CODEX_OUTPUT_REJECTED"
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
        report["adapter_state"] = "CODEX_ADAPTER_REJECTED"
        report["reason_code"] = "OPERATOR_POSTCONDITION_CHANGED"

    _persist_evidence(evidence_path, report)
    return report, 0 if report["adapter_state"] == "CODEX_ADAPTER_ACCEPTED" else 3
