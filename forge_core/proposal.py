from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Any

from .contract import ForgeContractError, verify_contract
from .doctor import ENVIRONMENT_READY, run_doctor
from .sealed_failures import ForgeFailureError, verify_failure_anchors

REQUEST_SCHEMA = "forge.proposal-request.v0.1"
PROPOSAL_SCHEMA = "forge.proposal.v0.1"
TRACE_SCHEMA = "forge.builder-trace.v0.1"
REQUEST_ID = "request-0001"
PROPOSAL_ID = "proposal-0001"
PATCH_LIMIT_BYTES = 1024 * 1024
TRACE_LIMIT_BYTES = 256 * 1024
TRACE_MAX_EVENTS = 256
TRACE_TEXT_LIMIT = 2048
TRACE_ID_LIMIT = 256
TRACE_KINDS = {"PLAN", "EDIT", "CHECK_ATTEMPT", "NOTE"}


class ForgeProposalError(RuntimeError):
    """W1 proposal authority is missing, stale, malformed, tampered, or unsafe."""


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


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


def _git(root: Path) -> tuple[str, str]:
    git_exe = shutil.which("git")
    if git_exe is None:
        raise ForgeProposalError("Git is required for W1 proposal authority")
    top = _git_text(git_exe, root, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root.resolve():
        raise ForgeProposalError("W1 must run at the Git repository root")
    head = _git_text(git_exe, root, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0 or not head.stdout.strip():
        raise ForgeProposalError("W1 requires a committed HEAD")
    return git_exe, head.stdout.strip()


def _read_regular(path: Path, *, limit: int, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if path.is_symlink():
            raise ForgeProposalError(f"{label} must not be a symlink") from exc
        raise ForgeProposalError(f"{label} is unreadable") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ForgeProposalError(f"{label} must be a regular file")
        if metadata.st_size > limit:
            raise ForgeProposalError(f"{label} exceeds {limit} bytes")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise ForgeProposalError(f"{label} exceeds {limit} bytes")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _proposal_root(root: Path, unit_id: str, *, create: bool) -> Path:
    forge = root / ".forge"
    if forge.is_symlink() or not forge.is_dir():
        raise ForgeProposalError("canonical .forge state is missing or unsafe")
    proposals = forge / "proposals"
    if proposals.is_symlink() or (proposals.exists() and not proposals.is_dir()):
        raise ForgeProposalError("proposal authority directory is unsafe")
    if create:
        proposals.mkdir(exist_ok=True)
    unit = proposals / unit_id
    if unit.is_symlink() or (unit.exists() and not unit.is_dir()):
        raise ForgeProposalError("unit proposal authority directory is unsafe")
    if create:
        unit.mkdir(exist_ok=True)
    return unit


def _request_dir(root: Path, unit_id: str, *, create_parent: bool = False) -> Path:
    return _proposal_root(root, unit_id, create=create_parent) / REQUEST_ID


def _request_payload(request: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in request.items() if key != "request_digest"}


def _request_digest(request: dict[str, Any]) -> str:
    return _sha256(_canonical(_request_payload(request)))


def _proposal_payload(proposal: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in proposal.items() if key != "proposal_digest"}


def _proposal_digest(proposal: dict[str, Any]) -> str:
    return _sha256(_canonical(_proposal_payload(proposal)))


def _read_contract_record(root: Path, unit_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    before = verify_contract(root, unit_id)
    path = root / ".forge" / "contracts" / f"{unit_id}.json"
    if path.is_symlink():
        raise ForgeContractError("contract file must not be a symlink")
    try:
        raw = path.read_bytes()
        record = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ForgeContractError("verified contract became unreadable during W1 authority read") from exc
    after = verify_contract(root, unit_id)
    if (
        before["revision"] != after["revision"]
        or before["contract_digest"] != after["contract_digest"]
        or record.get("contract_digest") != after["contract_digest"]
        or path.read_bytes() != raw
    ):
        raise ForgeContractError("contract changed during W1 authority read")
    authority = record.get("authority")
    if not isinstance(authority, dict):
        raise ForgeContractError("frozen contract authority is missing")
    return record, after


def _live_authority(root: Path, unit_id: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    try:
        verify_failure_anchors(root)
    except ForgeFailureError as exc:
        raise ForgeProposalError(f"failure-anchor integrity failed: {exc}") from exc
    record, verified = _read_contract_record(root, unit_id)
    doctor, doctor_exit = run_doctor(root, unit_id)
    if doctor_exit != 0 or doctor.get("classification") != ENVIRONMENT_READY:
        raise ForgeProposalError(f"Doctor prerequisite not ready: {doctor.get('classification')}")
    _, head = _git(root)
    if doctor.get("baseline_commit") != head:
        raise ForgeProposalError("Doctor baseline does not match current HEAD")
    final = verify_contract(root, unit_id)
    if (
        final["revision"] != verified["revision"]
        or final["contract_digest"] != verified["contract_digest"]
    ):
        raise ForgeProposalError("contract changed during W1 Doctor prerequisite")
    return record, final, head


def _trace_text(value: Any, label: str, *, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ForgeProposalError(f"{label} must be a non-empty string")
    if len(value) > limit:
        raise ForgeProposalError(f"{label} exceeds {limit} characters")
    return value


def validate_trace_bytes(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ForgeProposalError("proposal trace must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict) or set(value) != {"schema", "adapter", "provider_run_id", "events"}:
        raise ForgeProposalError("proposal trace keys do not match W1 schema")
    if value["schema"] != TRACE_SCHEMA:
        raise ForgeProposalError("proposal trace schema mismatch")
    adapter = _trace_text(value["adapter"], "trace adapter", limit=TRACE_ID_LIMIT)
    provider_run_id = _trace_text(value["provider_run_id"], "trace provider_run_id", limit=TRACE_ID_LIMIT)
    events = value["events"]
    if not isinstance(events, list) or len(events) > TRACE_MAX_EVENTS:
        raise ForgeProposalError(f"trace events must be a list of at most {TRACE_MAX_EVENTS}")
    normalized: list[dict[str, Any]] = []
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict) or set(event) != {"seq", "kind", "summary"}:
            raise ForgeProposalError("trace event keys do not match W1 schema")
        if event["seq"] != index:
            raise ForgeProposalError("trace event sequence must start at 1 and remain contiguous")
        if event["kind"] not in TRACE_KINDS:
            raise ForgeProposalError("trace event kind is not authorized")
        summary = _trace_text(event["summary"], "trace event summary", limit=TRACE_TEXT_LIMIT)
        normalized.append({"seq": index, "kind": event["kind"], "summary": summary})
    return {
        "schema": TRACE_SCHEMA,
        "adapter": adapter,
        "provider_run_id": provider_run_id,
        "events": normalized,
    }


def _path_matches(path: str, pattern: str) -> bool:
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


def _scope_violations(paths: list[str], authority: dict[str, Any]) -> list[dict[str, str]]:
    scope = authority.get("scope", {})
    allowed = scope.get("allowed_paths", [])
    forbidden = scope.get("forbidden_paths", [])
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


def _tracked_symlink_safety(git_exe: str, worktree: Path) -> list[str]:
    indexed = _git_text(git_exe, worktree, "ls-files", "-z", "-s")
    if indexed.returncode != 0:
        raise ForgeProposalError("unable to inspect proposal symlink safety")
    root = worktree.resolve()
    unsafe: list[str] = []
    for item in indexed.stdout.split("\x00"):
        if not item:
            continue
        try:
            metadata, relative = item.split("\t", 1)
            mode = metadata.split(" ", 1)[0]
        except ValueError as exc:
            raise ForgeProposalError("unable to parse proposal Git index") from exc
        if mode != "120000":
            continue
        link = worktree / relative
        if not link.is_symlink():
            raise ForgeProposalError(f"tracked symlink unsupported by filesystem: {relative}")
        try:
            link.resolve(strict=False).relative_to(root)
        except (OSError, ValueError):
            unsafe.append(relative)
    return sorted(unsafe)


def _validate_patch(root: Path, baseline: str, patch_bytes: bytes, authority: dict[str, Any]) -> list[str]:
    if not patch_bytes:
        raise ForgeProposalError("proposal patch must not be empty")
    git_exe, _ = _git(root)
    temp_parent = Path(tempfile.mkdtemp(prefix="forge-proposal-"))
    worktree = temp_parent / "worktree"
    patch_file = temp_parent / "proposal.patch"
    patch_file.write_bytes(patch_bytes)
    added = False
    try:
        created = _git_text(git_exe, root, "worktree", "add", "--detach", "--quiet", str(worktree), baseline)
        if created.returncode != 0:
            raise ForgeProposalError("proposal disposable worktree creation failed")
        added = True
        checked = _git_text(
            git_exe,
            worktree,
            "apply",
            "--check",
            "--whitespace=error-all",
            str(patch_file),
        )
        if checked.returncode != 0:
            raise ForgeProposalError("proposal patch does not cleanly apply to request baseline")
        applied = _git_text(
            git_exe,
            worktree,
            "apply",
            "--index",
            "--whitespace=error-all",
            str(patch_file),
        )
        if applied.returncode != 0:
            raise ForgeProposalError("proposal patch application failed")
        names = _git_bytes(
            git_exe,
            worktree,
            "diff",
            "--cached",
            "--name-only",
            "-z",
            "--no-renames",
        )
        unstaged = _git_bytes(
            git_exe,
            worktree,
            "diff",
            "--binary",
            "--full-index",
            "--no-ext-diff",
            "--no-renames",
        )
        if names.returncode != 0 or unstaged.returncode != 0 or unstaged.stdout:
            raise ForgeProposalError("proposal patched state cannot be verified exactly")
        changed_paths = [os.fsdecode(item) for item in names.stdout.split(b"\x00") if item]
        if not changed_paths:
            raise ForgeProposalError("proposal patch produces no changed paths")
        violations = _scope_violations(changed_paths, authority)
        if violations:
            rendered = ", ".join(f"{item['path']}:{item['reason']}" for item in violations)
            raise ForgeProposalError(f"proposal scope violation: {rendered}")
        unsafe = _tracked_symlink_safety(git_exe, worktree)
        if unsafe:
            raise ForgeProposalError(f"proposal tracked symlink escapes workspace: {unsafe}")
        return changed_paths
    finally:
        if added:
            _git_text(git_exe, root, "worktree", "remove", "--force", str(worktree))
        shutil.rmtree(temp_parent, ignore_errors=True)


def _load_request(root: Path, unit_id: str) -> tuple[Path, dict[str, Any]]:
    request_dir = _request_dir(root, unit_id)
    if request_dir.is_symlink() or not request_dir.is_dir():
        raise ForgeProposalError("proposal request is missing or unsafe")
    path = request_dir / "REQUEST.json"
    data = _read_regular(path, limit=256 * 1024, label="stored proposal request")
    try:
        request = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ForgeProposalError("stored proposal request is unreadable JSON") from exc
    expected_keys = {
        "schema",
        "request_id",
        "unit_id",
        "contract_revision",
        "contract_digest",
        "baseline_commit",
        "authority",
        "output_protocol",
        "completion_authority",
        "request_digest",
    }
    if not isinstance(request, dict) or set(request) != expected_keys:
        raise ForgeProposalError("stored proposal request keys do not match W1 schema")
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["request_id"] != REQUEST_ID
        or request["unit_id"] != unit_id
        or request["output_protocol"] != TRACE_SCHEMA
        or request["completion_authority"] != "none"
    ):
        raise ForgeProposalError("stored proposal request identity/authority mismatch")
    if request.get("request_digest") != _request_digest(request):
        raise ForgeProposalError("proposal request digest mismatch")
    return request_dir, request


def _assert_request_live(root: Path, unit_id: str, request: dict[str, Any]) -> None:
    record, verified, head = _live_authority(root, unit_id)
    if (
        request["contract_revision"] != verified["revision"]
        or request["contract_digest"] != verified["contract_digest"]
        or request["baseline_commit"] != head
        or request["authority"] != record["authority"]
    ):
        raise ForgeProposalError("proposal request is stale against live frozen authority")


def create_request(root: Path, unit_id: str) -> dict[str, Any]:
    root = root.resolve()
    record, verified, head = _live_authority(root, unit_id)
    request_dir = _request_dir(root, unit_id, create_parent=True)
    if request_dir.exists() or request_dir.is_symlink():
        raise ForgeProposalError("proposal request already exists; refusing overwrite")
    request = {
        "schema": REQUEST_SCHEMA,
        "request_id": REQUEST_ID,
        "unit_id": unit_id,
        "contract_revision": verified["revision"],
        "contract_digest": verified["contract_digest"],
        "baseline_commit": head,
        "authority": record["authority"],
        "output_protocol": TRACE_SCHEMA,
        "completion_authority": "none",
        "request_digest": None,
    }
    request["request_digest"] = _request_digest(request)
    request_dir.mkdir()
    (request_dir / "REQUEST.json").write_bytes(_pretty(request))
    return request


def submit_proposal(root: Path, unit_id: str, patch_file: Path, trace_file: Path) -> dict[str, Any]:
    root = root.resolve()
    request_dir, request = _load_request(root, unit_id)
    _assert_request_live(root, unit_id, request)
    proposal_dir = request_dir / PROPOSAL_ID
    if proposal_dir.exists() or proposal_dir.is_symlink():
        raise ForgeProposalError("proposal already exists; refusing overwrite")

    patch_bytes = _read_regular(patch_file, limit=PATCH_LIMIT_BYTES, label="proposal patch source")
    trace_bytes = _read_regular(trace_file, limit=TRACE_LIMIT_BYTES, label="proposal trace source")
    validate_trace_bytes(trace_bytes)
    changed_paths = _validate_patch(root, request["baseline_commit"], patch_bytes, request["authority"])
    _assert_request_live(root, unit_id, request)

    proposal = {
        "schema": PROPOSAL_SCHEMA,
        "proposal_id": PROPOSAL_ID,
        "unit_id": unit_id,
        "request_digest": request["request_digest"],
        "contract_revision": request["contract_revision"],
        "contract_digest": request["contract_digest"],
        "baseline_commit": request["baseline_commit"],
        "patch_sha256": _sha256(patch_bytes),
        "patch_bytes": len(patch_bytes),
        "trace_sha256": _sha256(trace_bytes),
        "trace_bytes": len(trace_bytes),
        "changed_paths": changed_paths,
        "proposal_state": "PROPOSAL_ACCEPTED",
        "completion_authority": "none",
        "checks_executed_by_forge": False,
        "candidate_authority": "none",
        "proposal_digest": None,
    }
    proposal["proposal_digest"] = _proposal_digest(proposal)
    proposal_dir.mkdir()
    (proposal_dir / "PATCH.diff").write_bytes(patch_bytes)
    (proposal_dir / "TRACE.json").write_bytes(trace_bytes)
    (proposal_dir / "PROPOSAL.json").write_bytes(_pretty(proposal))
    return {**proposal, "patch_file": (proposal_dir / "PATCH.diff").relative_to(root).as_posix()}


def verify_proposal(root: Path, unit_id: str) -> dict[str, Any]:
    root = root.resolve()
    request_dir, request = _load_request(root, unit_id)
    _assert_request_live(root, unit_id, request)
    proposal_dir = request_dir / PROPOSAL_ID
    if proposal_dir.is_symlink() or not proposal_dir.is_dir():
        raise ForgeProposalError("stored proposal is missing or unsafe")
    metadata_path = proposal_dir / "PROPOSAL.json"
    metadata_bytes = _read_regular(metadata_path, limit=256 * 1024, label="stored proposal metadata")
    try:
        proposal = json.loads(metadata_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ForgeProposalError("stored proposal metadata is unreadable JSON") from exc
    expected_keys = {
        "schema",
        "proposal_id",
        "unit_id",
        "request_digest",
        "contract_revision",
        "contract_digest",
        "baseline_commit",
        "patch_sha256",
        "patch_bytes",
        "trace_sha256",
        "trace_bytes",
        "changed_paths",
        "proposal_state",
        "completion_authority",
        "checks_executed_by_forge",
        "candidate_authority",
        "proposal_digest",
    }
    if not isinstance(proposal, dict) or set(proposal) != expected_keys:
        raise ForgeProposalError("stored proposal metadata keys do not match W1 schema")
    if (
        proposal["schema"] != PROPOSAL_SCHEMA
        or proposal["proposal_id"] != PROPOSAL_ID
        or proposal["unit_id"] != unit_id
        or proposal["proposal_state"] != "PROPOSAL_ACCEPTED"
        or proposal["completion_authority"] != "none"
        or proposal["checks_executed_by_forge"] is not False
        or proposal["candidate_authority"] != "none"
        or proposal["request_digest"] != request["request_digest"]
        or proposal["contract_revision"] != request["contract_revision"]
        or proposal["contract_digest"] != request["contract_digest"]
        or proposal["baseline_commit"] != request["baseline_commit"]
    ):
        raise ForgeProposalError("stored proposal authority mismatch")
    if proposal.get("proposal_digest") != _proposal_digest(proposal):
        raise ForgeProposalError("stored proposal digest mismatch")

    patch_path = proposal_dir / "PATCH.diff"
    trace_path = proposal_dir / "TRACE.json"
    patch_bytes = _read_regular(patch_path, limit=PATCH_LIMIT_BYTES, label="stored proposal patch")
    trace_bytes = _read_regular(trace_path, limit=TRACE_LIMIT_BYTES, label="stored proposal trace")
    validate_trace_bytes(trace_bytes)
    if len(patch_bytes) != proposal["patch_bytes"] or _sha256(patch_bytes) != proposal["patch_sha256"]:
        raise ForgeProposalError("stored proposal patch integrity mismatch")
    if len(trace_bytes) != proposal["trace_bytes"] or _sha256(trace_bytes) != proposal["trace_sha256"]:
        raise ForgeProposalError("stored proposal trace integrity mismatch")
    changed_paths = _validate_patch(root, request["baseline_commit"], patch_bytes, request["authority"])
    if changed_paths != proposal["changed_paths"]:
        raise ForgeProposalError("stored proposal changed-path evidence mismatch")
    _assert_request_live(root, unit_id, request)
    return {
        "unit_id": unit_id,
        "request_digest": request["request_digest"],
        "proposal_digest": proposal["proposal_digest"],
        "proposal_state": proposal["proposal_state"],
        "completion_authority": "none",
        "candidate_authority": "none",
        "checks_executed_by_forge": False,
        "proposal_verified": True,
        "patch_file": patch_path.relative_to(root).as_posix(),
        "changed_paths": changed_paths,
    }
