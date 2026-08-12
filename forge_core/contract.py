from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from typing import Any

from .state import STATE_DIR

CONTRACT_SCHEMA = "forge.contract.v0.1"
CONTRACTS_DIR = "contracts"
HISTORY_DIR = "history"
UNIT_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
ITEM_ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{0,63}$")
ALLOWED_TERMINAL_STATES = {
    "PASS",
    "PASS_WITH_DISCLOSED_LIMITS",
    "REPAIR_REQUIRED",
    "SEALED_NEGATIVE_RESULT",
    "BLOCKED_EXTERNAL",
    "ABANDONED_BY_OWNER",
}
AUTHORITY_KEYS = {
    "objective",
    "deliverables",
    "success_criteria",
    "scope",
    "checks",
    "terminal_states",
    "non_goals",
    "forbidden_actions",
}


class ForgeContractError(RuntimeError):
    """Contract authority is missing, invalid, tampered, or unsafe."""


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _pretty_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _atomic_write(path: Path, content: bytes) -> None:
    if path.is_symlink():
        raise ForgeContractError(f"refusing to replace symlinked contract artifact: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    if tmp.is_symlink():
        raise ForgeContractError("unsafe temporary contract path")
    with tmp.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _safe_state_dir(root: Path) -> Path:
    root = root.resolve()
    state_dir = root / STATE_DIR
    if state_dir.is_symlink() or not state_dir.is_dir():
        raise ForgeContractError("canonical .forge state must exist as a real directory")
    return state_dir


def _contracts_dir(root: Path, *, create: bool) -> Path:
    state_dir = _safe_state_dir(root)
    contracts = state_dir / CONTRACTS_DIR
    if contracts.is_symlink():
        raise ForgeContractError("contracts directory must not be a symlink")
    if contracts.exists() and not contracts.is_dir():
        raise ForgeContractError("contracts path exists but is not a directory")
    if create:
        contracts.mkdir(exist_ok=True)
    return contracts


def _unit_id(value: str) -> str:
    if not UNIT_ID_RE.fullmatch(value):
        raise ForgeContractError("unit ID must match [A-Z0-9][A-Z0-9._-]{0,63}")
    return value


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.fullmatch(value):
        raise ForgeContractError(f"{label} must be a bounded uppercase identifier")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ForgeContractError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ForgeContractError(f"{label} must be a {'non-empty ' if not allow_empty else ''}list")
    result = [_string(item, f"{label} item") for item in value]
    if len(result) != len(set(result)):
        raise ForgeContractError(f"{label} contains duplicates")
    return result


def _scope_path(value: Any, label: str) -> str:
    path = _string(value, label)
    if "\\" in path or path.startswith("/") or path.startswith("./"):
        raise ForgeContractError(f"{label} must be a canonical relative POSIX path/pattern")
    parts = PurePosixPath(path).parts
    if not parts or any(part in {".", ".."} for part in parts):
        raise ForgeContractError(f"{label} contains unsafe path traversal")
    return path


def _argv_token(value: Any, label: str) -> str:
    token = _string(value, label)
    if "\x00" in token:
        raise ForgeContractError(f"{label} contains a NUL byte")

    candidates = [token]
    if "=" in token:
        candidates.append(token.split("=", 1)[1])

    for candidate in candidates:
        if not candidate:
            continue
        if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
            raise ForgeContractError(
                f"{label} may not contain an absolute machine-specific path"
            )
    return token


def _allowed_path_targets_authority(path: str) -> bool:
    first = PurePosixPath(path).parts[0]
    return first == STATE_DIR or first.startswith(f"{STATE_DIR}[")


def validate_authority(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != AUTHORITY_KEYS:
        missing = sorted(AUTHORITY_KEYS - set(value if isinstance(value, dict) else {}))
        extra = sorted(set(value if isinstance(value, dict) else {}) - AUTHORITY_KEYS)
        raise ForgeContractError(f"authority keys mismatch; missing={missing} extra={extra}")

    objective = _string(value["objective"], "objective")
    deliverables = _string_list(value["deliverables"], "deliverables", allow_empty=False)
    non_goals = _string_list(value["non_goals"], "non_goals")
    forbidden_actions = _string_list(value["forbidden_actions"], "forbidden_actions")

    scope = value["scope"]
    if not isinstance(scope, dict) or set(scope) != {"allowed_paths", "forbidden_paths"}:
        raise ForgeContractError("scope must contain exactly allowed_paths and forbidden_paths")
    allowed_paths = [
        _scope_path(item, "allowed_paths item")
        for item in _string_list(scope["allowed_paths"], "allowed_paths", allow_empty=False)
    ]
    forbidden_paths = [
        _scope_path(item, "forbidden_paths item")
        for item in _string_list(scope["forbidden_paths"], "forbidden_paths")
    ]
    if any(_allowed_path_targets_authority(path) for path in allowed_paths):
        raise ForgeContractError("allowed_paths may not authorize writes under .forge")

    checks_value = value["checks"]
    if not isinstance(checks_value, list) or not checks_value:
        raise ForgeContractError("checks must be a non-empty list")
    checks: list[dict[str, Any]] = []
    check_ids: set[str] = set()
    required_checks: set[str] = set()
    for item in checks_value:
        if not isinstance(item, dict) or set(item) != {"id", "required", "argv"}:
            raise ForgeContractError("each check must contain exactly id, required, argv")
        check_id = _item_id(item["id"], "check id")
        if check_id in check_ids:
            raise ForgeContractError("check IDs must be unique")
        check_ids.add(check_id)
        required = item["required"]
        if not isinstance(required, bool):
            raise ForgeContractError("check required must be boolean")
        raw_argv = _string_list(item["argv"], f"check {check_id} argv", allow_empty=False)
        argv = [
            _argv_token(token, f"check {check_id} argv token") for token in raw_argv
        ]
        if required:
            required_checks.add(check_id)
        checks.append({"id": check_id, "required": required, "argv": argv})
    if not required_checks:
        raise ForgeContractError("at least one required check is mandatory")

    criteria_value = value["success_criteria"]
    if not isinstance(criteria_value, list) or not criteria_value:
        raise ForgeContractError("success_criteria must be a non-empty list")
    criteria: list[dict[str, Any]] = []
    criterion_ids: set[str] = set()
    for item in criteria_value:
        if not isinstance(item, dict) or set(item) != {"id", "statement", "check_ids"}:
            raise ForgeContractError(
                "each success criterion must contain exactly id, statement, check_ids"
            )
        criterion_id = _item_id(item["id"], "criterion id")
        if criterion_id in criterion_ids:
            raise ForgeContractError("criterion IDs must be unique")
        criterion_ids.add(criterion_id)
        statement = _string(item["statement"], f"criterion {criterion_id} statement")
        references = _string_list(
            item["check_ids"], f"criterion {criterion_id} check_ids", allow_empty=False
        )
        missing = sorted(set(references) - check_ids)
        if missing:
            raise ForgeContractError(
                f"criterion {criterion_id} references missing checks: {missing}"
            )
        advisory = sorted(set(references) - required_checks)
        if advisory:
            raise ForgeContractError(
                f"criterion {criterion_id} may reference only required checks: {advisory}"
            )
        criteria.append(
            {"id": criterion_id, "statement": statement, "check_ids": references}
        )

    terminal_states = _string_list(
        value["terminal_states"], "terminal_states", allow_empty=False
    )
    unknown = sorted(set(terminal_states) - ALLOWED_TERMINAL_STATES)
    if unknown:
        raise ForgeContractError(f"unknown terminal states: {unknown}")
    if "PASS" not in terminal_states:
        raise ForgeContractError("terminal_states must include PASS")
    if len(terminal_states) < 2:
        raise ForgeContractError("terminal_states must include at least one failure state")

    return {
        "objective": objective,
        "deliverables": deliverables,
        "success_criteria": criteria,
        "scope": {
            "allowed_paths": allowed_paths,
            "forbidden_paths": forbidden_paths,
        },
        "checks": checks,
        "terminal_states": terminal_states,
        "non_goals": non_goals,
        "forbidden_actions": forbidden_actions,
    }


def _load_authority_file(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ForgeContractError("authority source file must not be a symlink")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ForgeContractError("authority source file does not exist") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ForgeContractError("authority source file is unreadable JSON") from exc
    return validate_authority(raw)


def _record_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": record["schema"],
        "unit_id": record["unit_id"],
        "revision": record["revision"],
        "state": record["state"],
        "parent_digest": record["parent_digest"],
        "amendment_reason": record["amendment_reason"],
        "authority": record["authority"],
    }


def _contract_digest(record: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(_record_payload(record))).hexdigest()
    return f"sha256:{digest}"


def _contract_path(root: Path, unit_id: str, *, create_dir: bool) -> Path:
    unit_id = _unit_id(unit_id)
    contracts = _contracts_dir(root, create=create_dir)
    return contracts / f"{unit_id}.json"


def _read_record(root: Path, unit_id: str) -> tuple[Path, dict[str, Any]]:
    path = _contract_path(root, unit_id, create_dir=False)
    if path.is_symlink():
        raise ForgeContractError("contract file must not be a symlink")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ForgeContractError(f"contract not found: {unit_id}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ForgeContractError(f"contract unreadable: {unit_id}") from exc
    if not isinstance(record, dict):
        raise ForgeContractError("contract record must be a JSON object")
    return path, record


def _validate_record_shape(record: dict[str, Any], unit_id: str) -> None:
    expected = {
        "schema",
        "unit_id",
        "revision",
        "state",
        "parent_digest",
        "amendment_reason",
        "authority",
        "contract_digest",
    }
    if set(record) != expected:
        raise ForgeContractError("contract record keys do not match schema")
    if record["schema"] != CONTRACT_SCHEMA or record["unit_id"] != unit_id:
        raise ForgeContractError("contract identity/schema mismatch")
    if not isinstance(record["revision"], int) or record["revision"] < 1:
        raise ForgeContractError("contract revision must be a positive integer")
    if record["state"] not in {"DRAFT", "FROZEN"}:
        raise ForgeContractError("contract state must be DRAFT or FROZEN")
    if record["revision"] == 1:
        if record["parent_digest"] is not None or record["amendment_reason"] is not None:
            raise ForgeContractError("revision 1 may not claim an amendment parent/reason")
    else:
        if not isinstance(record["parent_digest"], str) or not record["parent_digest"].startswith(
            "sha256:"
        ):
            raise ForgeContractError("amended revision requires parent digest")
        _string(record["amendment_reason"], "amendment reason")
    validate_authority(record["authority"])


def _verify_frozen_record(record: dict[str, Any], unit_id: str) -> str:
    _validate_record_shape(record, unit_id)
    if record["state"] != "FROZEN":
        raise ForgeContractError("contract is DRAFT; implementation readiness is denied")
    digest = record["contract_digest"]
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise ForgeContractError("frozen contract is missing a valid digest")
    expected = _contract_digest(record)
    if digest != expected:
        raise ForgeContractError("contract digest mismatch; frozen authority was modified")
    return digest


def _verify_history_chain(root: Path, current: dict[str, Any], unit_id: str) -> None:
    revision = current["revision"]
    if revision == 1:
        return
    contracts = _contracts_dir(root, create=False)
    history = contracts / HISTORY_DIR
    unit_history = history / unit_id
    if history.is_symlink() or unit_history.is_symlink():
        raise ForgeContractError("contract history must not be symlinked")
    if not history.is_dir() or not unit_history.is_dir():
        raise ForgeContractError("contract amendment history is missing")

    previous_digest: str | None = None
    for expected_revision in range(1, revision):
        archive = unit_history / f"revision-{expected_revision:04d}.json"
        if archive.is_symlink():
            raise ForgeContractError("archived contract revision must not be a symlink")
        try:
            archived = json.loads(archive.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ForgeContractError(
                f"archived contract revision missing: {expected_revision}"
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ForgeContractError(
                f"archived contract revision unreadable: {expected_revision}"
            ) from exc
        if not isinstance(archived, dict) or archived.get("revision") != expected_revision:
            raise ForgeContractError("archived contract revision identity mismatch")
        archived_digest = _verify_frozen_record(archived, unit_id)
        if expected_revision == 1:
            if archived["parent_digest"] is not None:
                raise ForgeContractError("revision 1 archive has unexpected parent digest")
        elif archived["parent_digest"] != previous_digest:
            raise ForgeContractError("archived contract parent chain mismatch")
        previous_digest = archived_digest

    if current["parent_digest"] != previous_digest:
        raise ForgeContractError("current contract parent digest does not match history")


def create_contract(root: Path, unit_id: str, authority_file: Path) -> dict[str, Any]:
    unit_id = _unit_id(unit_id)
    authority = _load_authority_file(authority_file)
    path = _contract_path(root, unit_id, create_dir=True)
    if path.exists() or path.is_symlink():
        raise ForgeContractError(f"contract already exists: {unit_id}")
    record = {
        "schema": CONTRACT_SCHEMA,
        "unit_id": unit_id,
        "revision": 1,
        "state": "DRAFT",
        "parent_digest": None,
        "amendment_reason": None,
        "authority": authority,
        "contract_digest": None,
    }
    _atomic_write(path, _pretty_json(record))
    return record


def freeze_contract(root: Path, unit_id: str) -> dict[str, Any]:
    path, record = _read_record(root, _unit_id(unit_id))
    _validate_record_shape(record, unit_id)
    if record["state"] == "FROZEN":
        _verify_frozen_record(record, unit_id)
        return record
    if record["contract_digest"] is not None:
        raise ForgeContractError("draft contract may not carry a digest")
    record["state"] = "FROZEN"
    record["contract_digest"] = _contract_digest(record)
    _atomic_write(path, _pretty_json(record))
    return record


def verify_contract(root: Path, unit_id: str) -> dict[str, Any]:
    _, record = _read_record(root, _unit_id(unit_id))
    digest = _verify_frozen_record(record, unit_id)
    _verify_history_chain(root, record, unit_id)
    return {
        "unit_id": unit_id,
        "revision": record["revision"],
        "state": record["state"],
        "contract_digest": digest,
        "verified": True,
    }


def contract_ready(root: Path, unit_id: str) -> dict[str, Any]:
    result = verify_contract(root, unit_id)
    return {**result, "implementation_eligible": True}


def amend_contract(
    root: Path, unit_id: str, authority_file: Path, reason: str
) -> dict[str, Any]:
    unit_id = _unit_id(unit_id)
    reason = _string(reason, "amendment reason")
    path, current = _read_record(root, unit_id)
    current_digest = _verify_frozen_record(current, unit_id)
    _verify_history_chain(root, current, unit_id)
    authority = _load_authority_file(authority_file)

    contracts = _contracts_dir(root, create=True)
    history = contracts / HISTORY_DIR
    if history.is_symlink():
        raise ForgeContractError("contract history directory must not be a symlink")
    history.mkdir(exist_ok=True)
    unit_history = history / unit_id
    if unit_history.is_symlink():
        raise ForgeContractError("unit history directory must not be a symlink")
    unit_history.mkdir(exist_ok=True)
    archive = unit_history / f"revision-{current['revision']:04d}.json"
    current_bytes = _pretty_json(current)
    if archive.exists() or archive.is_symlink():
        if archive.is_symlink() or archive.read_bytes() != current_bytes:
            raise ForgeContractError("existing amendment archive does not match current revision")
    else:
        _atomic_write(archive, current_bytes)

    next_record = {
        "schema": CONTRACT_SCHEMA,
        "unit_id": unit_id,
        "revision": current["revision"] + 1,
        "state": "DRAFT",
        "parent_digest": current_digest,
        "amendment_reason": reason,
        "authority": authority,
        "contract_digest": None,
    }
    _atomic_write(path, _pretty_json(next_record))
    return next_record
