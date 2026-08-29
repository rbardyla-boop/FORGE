from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Sequence


ENVELOPE_SCHEMA = "forge.research-context-envelope.v0.1"
GRANT_SCHEMA = "forge.research-context-grant.v0.1"
ACCESS_CLASS = "READ_SNAPSHOT"
MAX_REASON_CHARS = 1024


class ForgeContextGrantError(RuntimeError):
    """A0 context authority is malformed, stale, tampered, or out of bounds."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _digest_payload(value: dict[str, Any], digest_key: str) -> str:
    return _sha256(_canonical({key: item for key, item in value.items() if key != digest_key}))


def _validate_pattern(pattern: Any, *, label: str) -> str:
    if not isinstance(pattern, str) or not pattern or len(pattern) > 512:
        raise ForgeContextGrantError(f"{label} must be a bounded non-empty string")
    if "\x00" in pattern:
        raise ForgeContextGrantError(f"{label} contains NUL")
    pure = PurePosixPath(pattern)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ForgeContextGrantError(f"{label} must be a safe relative POSIX pattern")
    return pattern


def _validate_relative_path(path: Any) -> str:
    if not isinstance(path, str) or not path or len(path) > 1024:
        raise ForgeContextGrantError("resource path must be a bounded non-empty string")
    if "\x00" in path:
        raise ForgeContextGrantError("resource path contains NUL")
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ForgeContextGrantError("resource path must be a safe relative POSIX path")
    normalized = pure.as_posix()
    if normalized != path:
        raise ForgeContextGrantError("resource path must already be normalized POSIX text")
    return normalized


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


def _validate_action_authority(authority: Any) -> dict[str, Any]:
    if not isinstance(authority, dict) or not authority:
        raise ForgeContextGrantError("action authority must be a non-empty object")
    try:
        _canonical(authority)
    except (TypeError, ValueError) as exc:
        raise ForgeContextGrantError("action authority must be canonical JSON data") from exc
    return authority


def create_context_envelope(
    action_authority: dict[str, Any],
    *,
    allowed_paths: Sequence[str],
    forbidden_paths: Sequence[str] = (),
    max_grants: int = 8,
    max_resource_bytes: int = 256 * 1024,
    max_total_bytes: int = 1024 * 1024,
) -> dict[str, Any]:
    authority = _validate_action_authority(action_authority)
    allowed = [_validate_pattern(item, label="allowed discovery pattern") for item in allowed_paths]
    forbidden = [_validate_pattern(item, label="forbidden discovery pattern") for item in forbidden_paths]
    if not allowed:
        raise ForgeContextGrantError("at least one allowed discovery pattern is required")
    if not isinstance(max_grants, int) or isinstance(max_grants, bool) or not 1 <= max_grants <= 64:
        raise ForgeContextGrantError("max_grants must be within [1, 64]")
    if (
        not isinstance(max_resource_bytes, int)
        or isinstance(max_resource_bytes, bool)
        or not 1 <= max_resource_bytes <= 16 * 1024 * 1024
    ):
        raise ForgeContextGrantError("max_resource_bytes is outside the research bound")
    if (
        not isinstance(max_total_bytes, int)
        or isinstance(max_total_bytes, bool)
        or max_total_bytes < max_resource_bytes
        or max_total_bytes > 64 * 1024 * 1024
    ):
        raise ForgeContextGrantError("max_total_bytes is outside the research bound")

    envelope = {
        "schema": ENVELOPE_SCHEMA,
        "action_authority": authority,
        "action_authority_digest": _sha256(_canonical(authority)),
        "discovery": {
            "allowed_paths": allowed,
            "forbidden_paths": forbidden,
        },
        "limits": {
            "max_grants": max_grants,
            "max_resource_bytes": max_resource_bytes,
            "max_total_bytes": max_total_bytes,
        },
        "envelope_digest": None,
    }
    envelope["envelope_digest"] = _digest_payload(envelope, "envelope_digest")
    verify_context_envelope(envelope)
    return envelope


def verify_context_envelope(envelope: Any) -> dict[str, Any]:
    expected = {
        "schema",
        "action_authority",
        "action_authority_digest",
        "discovery",
        "limits",
        "envelope_digest",
    }
    if not isinstance(envelope, dict) or set(envelope) != expected:
        raise ForgeContextGrantError("context envelope keys do not match schema")
    if envelope["schema"] != ENVELOPE_SCHEMA:
        raise ForgeContextGrantError("context envelope schema mismatch")
    authority = _validate_action_authority(envelope["action_authority"])
    if envelope["action_authority_digest"] != _sha256(_canonical(authority)):
        raise ForgeContextGrantError("action authority digest mismatch")

    discovery = envelope["discovery"]
    if not isinstance(discovery, dict) or set(discovery) != {"allowed_paths", "forbidden_paths"}:
        raise ForgeContextGrantError("context discovery policy schema mismatch")
    if not isinstance(discovery["allowed_paths"], list) or not discovery["allowed_paths"]:
        raise ForgeContextGrantError("allowed discovery policy must be a non-empty list")
    if not isinstance(discovery["forbidden_paths"], list):
        raise ForgeContextGrantError("forbidden discovery policy must be a list")
    for item in discovery["allowed_paths"]:
        _validate_pattern(item, label="allowed discovery pattern")
    for item in discovery["forbidden_paths"]:
        _validate_pattern(item, label="forbidden discovery pattern")

    limits = envelope["limits"]
    if not isinstance(limits, dict) or set(limits) != {"max_grants", "max_resource_bytes", "max_total_bytes"}:
        raise ForgeContextGrantError("context limits schema mismatch")
    if not isinstance(limits["max_grants"], int) or isinstance(limits["max_grants"], bool) or not 1 <= limits["max_grants"] <= 64:
        raise ForgeContextGrantError("context grant limit invalid")
    if (
        not isinstance(limits["max_resource_bytes"], int)
        or isinstance(limits["max_resource_bytes"], bool)
        or not 1 <= limits["max_resource_bytes"] <= 16 * 1024 * 1024
    ):
        raise ForgeContextGrantError("context per-resource limit invalid")
    if (
        not isinstance(limits["max_total_bytes"], int)
        or isinstance(limits["max_total_bytes"], bool)
        or limits["max_total_bytes"] < limits["max_resource_bytes"]
        or limits["max_total_bytes"] > 64 * 1024 * 1024
    ):
        raise ForgeContextGrantError("context total-byte limit invalid")
    if envelope["envelope_digest"] != _digest_payload(envelope, "envelope_digest"):
        raise ForgeContextGrantError("context envelope digest mismatch")
    return envelope


def _read_regular_nofollow(root: Path, relative_path: str, *, limit: int) -> bytes:
    root = root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ForgeContextGrantError("experiment root must be a real directory")

    current = root
    for part in PurePosixPath(relative_path).parts:
        current = current / part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise ForgeContextGrantError("requested context resource is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ForgeContextGrantError("context resource path must not contain symlinks")

    try:
        target = current.resolve(strict=True)
        target.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ForgeContextGrantError("context resource escapes experiment root") from exc

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(target, flags)
    except OSError as exc:
        raise ForgeContextGrantError("context resource cannot be opened safely") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ForgeContextGrantError("context resource must be a regular file")
        if metadata.st_size > limit:
            raise ForgeContextGrantError("context resource exceeds per-resource byte limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, limit + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise ForgeContextGrantError("context resource exceeds per-resource byte limit")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _verify_policy_path(envelope: dict[str, Any], relative_path: str) -> None:
    policy = envelope["discovery"]
    if not any(_path_matches(relative_path, pattern) for pattern in policy["allowed_paths"]):
        raise ForgeContextGrantError("requested resource is outside frozen discovery universe")
    if any(_path_matches(relative_path, pattern) for pattern in policy["forbidden_paths"]):
        raise ForgeContextGrantError("requested resource matches frozen forbidden discovery policy")


def _grant_digest(grant: dict[str, Any]) -> str:
    return _digest_payload(grant, "grant_digest")


def verify_context_grant_chain(envelope: dict[str, Any], grants: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    verify_context_envelope(envelope)
    if not isinstance(grants, (list, tuple)):
        raise ForgeContextGrantError("context grants must be an ordered sequence")
    if len(grants) > envelope["limits"]["max_grants"]:
        raise ForgeContextGrantError("context grant chain exceeds frozen grant-count limit")

    previous: str | None = None
    total_bytes = 0
    verified: list[dict[str, Any]] = []
    expected_keys = {
        "schema",
        "sequence",
        "parent_grant_digest",
        "envelope_digest",
        "action_authority_digest",
        "resource_path",
        "access",
        "content_sha256",
        "content_bytes",
        "reason",
        "grant_digest",
    }
    for index, grant in enumerate(grants, start=1):
        if not isinstance(grant, dict) or set(grant) != expected_keys:
            raise ForgeContextGrantError("context grant keys do not match schema")
        if grant["schema"] != GRANT_SCHEMA or grant["sequence"] != index:
            raise ForgeContextGrantError("context grant identity/sequence mismatch")
        if grant["parent_grant_digest"] != previous:
            raise ForgeContextGrantError("context grant parent chain mismatch")
        if grant["envelope_digest"] != envelope["envelope_digest"]:
            raise ForgeContextGrantError("context grant points at wrong envelope")
        if grant["action_authority_digest"] != envelope["action_authority_digest"]:
            raise ForgeContextGrantError("context grant attempts action-authority drift")
        path = _validate_relative_path(grant["resource_path"])
        _verify_policy_path(envelope, path)
        if grant["access"] != ACCESS_CLASS:
            raise ForgeContextGrantError("context grant access class is not READ_SNAPSHOT")
        if not isinstance(grant["content_sha256"], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", grant["content_sha256"]):
            raise ForgeContextGrantError("context grant content hash is malformed")
        if not isinstance(grant["content_bytes"], int) or isinstance(grant["content_bytes"], bool) or grant["content_bytes"] < 0:
            raise ForgeContextGrantError("context grant byte count is malformed")
        if grant["content_bytes"] > envelope["limits"]["max_resource_bytes"]:
            raise ForgeContextGrantError("context grant exceeds per-resource byte limit")
        reason = grant["reason"]
        if not isinstance(reason, str) or not reason.strip() or len(reason) > MAX_REASON_CHARS:
            raise ForgeContextGrantError("context grant reason is invalid")
        if grant["grant_digest"] != _grant_digest(grant):
            raise ForgeContextGrantError("context grant digest mismatch")
        total_bytes += grant["content_bytes"]
        if total_bytes > envelope["limits"]["max_total_bytes"]:
            raise ForgeContextGrantError("context grant chain exceeds total-byte budget")
        previous = grant["grant_digest"]
        verified.append(grant)
    return verified


def issue_context_grant(
    root: Path,
    envelope: dict[str, Any],
    grants: Sequence[dict[str, Any]],
    resource_path: str,
    *,
    reason: str,
) -> dict[str, Any]:
    verify_context_envelope(envelope)
    verified = verify_context_grant_chain(envelope, grants)
    if len(verified) >= envelope["limits"]["max_grants"]:
        raise ForgeContextGrantError("context grant-count budget exhausted")
    path = _validate_relative_path(resource_path)
    _verify_policy_path(envelope, path)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > MAX_REASON_CHARS:
        raise ForgeContextGrantError("context grant reason must be bounded non-empty text")

    data = _read_regular_nofollow(root, path, limit=envelope["limits"]["max_resource_bytes"])
    used = sum(item["content_bytes"] for item in verified)
    if used + len(data) > envelope["limits"]["max_total_bytes"]:
        raise ForgeContextGrantError("context cumulative byte budget exhausted")

    grant = {
        "schema": GRANT_SCHEMA,
        "sequence": len(verified) + 1,
        "parent_grant_digest": verified[-1]["grant_digest"] if verified else None,
        "envelope_digest": envelope["envelope_digest"],
        "action_authority_digest": envelope["action_authority_digest"],
        "resource_path": path,
        "access": ACCESS_CLASS,
        "content_sha256": _sha256(data),
        "content_bytes": len(data),
        "reason": reason,
        "grant_digest": None,
    }
    grant["grant_digest"] = _grant_digest(grant)
    verify_context_grant_chain(envelope, [*verified, grant])
    return grant


def read_granted_content(root: Path, envelope: dict[str, Any], grants: Sequence[dict[str, Any]], sequence: int) -> bytes:
    verified = verify_context_grant_chain(envelope, grants)
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1 or sequence > len(verified):
        raise ForgeContextGrantError("requested context grant sequence does not exist")
    grant = verified[sequence - 1]
    data = _read_regular_nofollow(root, grant["resource_path"], limit=envelope["limits"]["max_resource_bytes"])
    if len(data) != grant["content_bytes"] or _sha256(data) != grant["content_sha256"]:
        raise ForgeContextGrantError("context resource changed after grant; fresh grant required")
    return data
