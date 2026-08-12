from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .failures import (
    EVALUATOR_LAYERS,
    ForgeFailureError,
    close_failure as _legacy_close_failure,
    register_failure as _legacy_register_failure,
    replay_failure as _legacy_replay_failure,
    verify_failure as _legacy_verify_failure,
)

REGISTERED_PREFIX = "refs/forge/failures/registered/"
LOCKED_PREFIX = "refs/forge/failures/locked/"
ZERO_OID = "0" * 40


def registered_ref(failure_id: str) -> str:
    return f"{REGISTERED_PREFIX}{failure_id}"


def locked_ref(failure_id: str) -> str:
    return f"{LOCKED_PREFIX}{failure_id}"


def _git_text(
    git_exe: str,
    root: Path,
    *args: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [git_exe, "-C", str(root), *args],
        text=True,
        input=input_text,
        capture_output=True,
        check=False,
        timeout=10,
    )


def _git(root: Path) -> str:
    git_exe = shutil.which("git")
    if git_exe is None:
        raise ForgeFailureError("Git is required for F6 failure anchors")
    probe = _git_text(git_exe, root, "rev-parse", "--show-toplevel")
    if probe.returncode != 0 or Path(probe.stdout.strip()).resolve() != root.resolve():
        raise ForgeFailureError("F6 failure anchors require repository root")
    return git_exe


def _record(root: Path, failure_id: str) -> dict[str, Any]:
    path = root / ".forge" / "failures" / failure_id / "record.json"
    if path.is_symlink():
        raise ForgeFailureError("failure record must not be symlinked")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ForgeFailureError("failure anchor cannot read matching failure record") from exc
    if not isinstance(value, dict):
        raise ForgeFailureError("failure anchor requires object failure record")
    return value


def _registered_payload(record: dict[str, Any]) -> dict[str, Any]:
    evaluators = record.get("evaluators")
    if not isinstance(evaluators, dict) or set(evaluators) != set(EVALUATOR_LAYERS):
        raise ForgeFailureError("failure anchor evaluator set mismatch")
    return {
        "schema": "forge.failure-anchor.registered.v0.1",
        "failure_id": record.get("failure_id"),
        "registration_digest": record.get("registration_digest"),
        "evaluators": {layer: evaluators[layer].get("sha256") for layer in EVALUATOR_LAYERS},
    }


def _locked_payload(record: dict[str, Any]) -> dict[str, Any]:
    permanent = record.get("evaluators", {}).get("PERMANENT_EVALUATION", {})
    return {
        "schema": "forge.failure-anchor.locked.v0.1",
        "failure_id": record.get("failure_id"),
        "registration_digest": record.get("registration_digest"),
        "locked_by_closure": record.get("locked_by_closure"),
        "permanent_evaluator_sha256": permanent.get("sha256"),
    }


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def _create_anchor(root: Path, ref: str, payload: dict[str, Any]) -> str:
    git_exe = _git(root)
    existing = _git_text(git_exe, root, "rev-parse", "--verify", "--quiet", ref)
    if existing.returncode == 0:
        raise ForgeFailureError(f"failure anchor already exists: {ref}")
    blob = _git_text(git_exe, root, "hash-object", "-w", "--stdin", input_text=_canonical(payload))
    oid = blob.stdout.strip()
    if blob.returncode != 0 or len(oid) != 40:
        raise ForgeFailureError("failure anchor blob creation failed")
    updated = _git_text(git_exe, root, "update-ref", ref, oid, ZERO_OID)
    if updated.returncode != 0:
        raise ForgeFailureError("failure anchor ref creation failed")
    return oid


def _read_anchor(root: Path, ref: str) -> dict[str, Any]:
    git_exe = _git(root)
    resolved = _git_text(git_exe, root, "rev-parse", "--verify", ref)
    if resolved.returncode != 0 or not resolved.stdout.strip():
        raise ForgeFailureError(f"required failure anchor is missing: {ref}")
    oid = resolved.stdout.strip()
    kind = _git_text(git_exe, root, "cat-file", "-t", oid)
    if kind.returncode != 0 or kind.stdout.strip() != "blob":
        raise ForgeFailureError(f"failure anchor does not resolve to a blob: {ref}")
    payload = _git_text(git_exe, root, "cat-file", "-p", oid)
    if payload.returncode != 0:
        raise ForgeFailureError(f"failure anchor blob is unreadable: {ref}")
    try:
        value = json.loads(payload.stdout)
    except json.JSONDecodeError as exc:
        raise ForgeFailureError(f"failure anchor blob is invalid JSON: {ref}") from exc
    if not isinstance(value, dict):
        raise ForgeFailureError(f"failure anchor payload must be an object: {ref}")
    return value


def _ref_ids(root: Path, prefix: str) -> set[str]:
    git_exe = _git(root)
    refs = _git_text(git_exe, root, "for-each-ref", "--format=%(refname)", prefix)
    if refs.returncode != 0:
        raise ForgeFailureError("unable to enumerate failure anchors")
    result: set[str] = set()
    for line in refs.stdout.splitlines():
        if line:
            if not line.startswith(prefix):
                raise ForgeFailureError("unexpected failure anchor namespace")
            result.add(line[len(prefix):])
    return result


def verify_failure_anchors(root: Path) -> dict[str, Any]:
    root = root.resolve()
    _git(root)
    failures = root / ".forge" / "failures"
    if failures.is_symlink() or (failures.exists() and not failures.is_dir()):
        raise ForgeFailureError("failure ledger directory is unsafe")
    directory_ids: set[str] = set()
    if failures.is_dir():
        for entry in failures.iterdir():
            if entry.is_symlink() or not entry.is_dir():
                raise ForgeFailureError("failure ledger contains an unsafe non-directory entry")
            directory_ids.add(entry.name)

    registered_ids = _ref_ids(root, REGISTERED_PREFIX)
    locked_ids = _ref_ids(root, LOCKED_PREFIX)
    if directory_ids != registered_ids:
        missing_records = sorted(registered_ids - directory_ids)
        missing_anchors = sorted(directory_ids - registered_ids)
        raise ForgeFailureError(
            f"failure registration set mismatch; missing_records={missing_records} missing_anchors={missing_anchors}"
        )
    if not locked_ids.issubset(registered_ids):
        raise ForgeFailureError("locked failure anchor exists without registration anchor")

    for failure_id in sorted(directory_ids):
        _legacy_verify_failure(root, failure_id)
        record = _record(root, failure_id)
        if _read_anchor(root, registered_ref(failure_id)) != _registered_payload(record):
            raise ForgeFailureError(f"registered failure anchor mismatch: {failure_id}")
        if record.get("status") == "LOCKED":
            if failure_id not in locked_ids:
                raise ForgeFailureError(f"LOCKED failure is missing locked anchor: {failure_id}")
            if _read_anchor(root, locked_ref(failure_id)) != _locked_payload(record):
                raise ForgeFailureError(f"locked failure anchor mismatch: {failure_id}")
        elif record.get("status") == "OPEN":
            if failure_id in locked_ids:
                raise ForgeFailureError(f"locked anchor exists for OPEN failure: {failure_id}")
        else:
            raise ForgeFailureError(f"unknown failure status: {failure_id}")
    return {
        "verified": True,
        "registered_failures": sorted(registered_ids),
        "locked_failures": sorted(locked_ids),
    }


def register_failure(root: Path, failure_id: str, spec_file: Path):
    root = root.resolve()
    record = _legacy_register_failure(root, failure_id, spec_file)
    failure_dir = root / ".forge" / "failures" / failure_id
    try:
        _create_anchor(root, registered_ref(failure_id), _registered_payload(record))
        verify_failure_anchors(root)
        return record
    except ForgeFailureError:
        shutil.rmtree(failure_dir, ignore_errors=True)
        git_exe = shutil.which("git")
        if git_exe:
            _git_text(git_exe, root, "update-ref", "-d", registered_ref(failure_id))
        raise


def close_failure(root: Path, failure_id: str, candidate: Path):
    root = root.resolve()
    verify_failure_anchors(root)
    evidence, code = _legacy_close_failure(root, failure_id, candidate)
    if code == 0:
        record = _record(root, failure_id)
        _create_anchor(root, locked_ref(failure_id), _locked_payload(record))
        verify_failure_anchors(root)
    return evidence, code


def verify_failure(root: Path, failure_id: str):
    root = root.resolve()
    overall = verify_failure_anchors(root)
    result = _legacy_verify_failure(root, failure_id)
    return {**result, "anchor_verified": True, "locked_failures": overall["locked_failures"]}


def replay_failure(root: Path, failure_id: str, candidate: Path):
    root = root.resolve()
    verify_failure_anchors(root)
    return _legacy_replay_failure(root, failure_id, candidate)
