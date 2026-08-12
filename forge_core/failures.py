from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
from typing import Any

FAILURE_SCHEMA = "forge.failure.v0.1"
CLOSURE_SCHEMA = "forge.failure-closure.v0.1"
REPLAY_SCHEMA = "forge.failure-replay.v0.1"
FAILURES_DIR = "failures"
EVALUATOR_LIMIT_BYTES = 64 * 1024
OUTPUT_LIMIT = 4096
EVALUATOR_LAYERS = (
    "MINIMAL_REPRODUCTION",
    "ORIGINAL_BROADER_CHECK",
    "UNRELATED_REGRESSIONS",
    "PERMANENT_EVALUATION",
)
FAILURE_ID_RE = re.compile(r"^FAIL-[A-Z0-9][A-Z0-9._-]{0,58}$")


class ForgeFailureError(RuntimeError):
    """Failure-memory authority is missing, invalid, tampered, or unsafe."""


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _bounded(value: str | None) -> tuple[str, bool]:
    text = value or ""
    if len(text) <= OUTPUT_LIMIT:
        return text, False
    return text[:OUTPUT_LIMIT], True


def _pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    if path.is_symlink():
        raise ForgeFailureError(f"refusing to replace symlinked failure artifact: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    if tmp.is_symlink():
        raise ForgeFailureError("unsafe temporary failure path")
    with tmp.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _failure_id(value: str) -> str:
    if not FAILURE_ID_RE.fullmatch(value):
        raise ForgeFailureError("failure ID must match FAIL-[A-Z0-9][A-Z0-9._-]{0,58}")
    return value


def _failures_root(root: Path, *, create: bool) -> Path:
    forge = root.resolve() / ".forge"
    if forge.is_symlink() or not forge.is_dir():
        raise ForgeFailureError("canonical .forge state must exist as a real directory")
    failures = forge / FAILURES_DIR
    if failures.is_symlink() or (failures.exists() and not failures.is_dir()):
        raise ForgeFailureError("failure ledger path is unsafe")
    if create:
        failures.mkdir(exist_ok=True)
    return failures


def _read_regular_file(path: Path, *, limit: int, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if path.is_symlink():
            raise ForgeFailureError(f"{label} must not be a symlink") from exc
        raise ForgeFailureError(f"{label} is unreadable") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ForgeFailureError(f"{label} must be a regular file")
        if metadata.st_size > limit:
            raise ForgeFailureError(f"{label} exceeds {limit} bytes")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise ForgeFailureError(f"{label} exceeds {limit} bytes")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _registration_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": record["schema"],
        "failure_id": record["failure_id"],
        "unit_id": record["unit_id"],
        "scenario": record["scenario"],
        "expected_behavior": record["expected_behavior"],
        "observed_behavior": record["observed_behavior"],
        "root_cause": record["root_cause"],
        "evaluators": record["evaluators"],
    }


def _registration_digest(record: dict[str, Any]) -> str:
    return _sha256(_canonical(_registration_payload(record)))


def _load_spec(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ForgeFailureError("failure spec must not be a symlink")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ForgeFailureError("failure spec does not exist") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ForgeFailureError("failure spec is unreadable JSON") from exc
    if not isinstance(raw, dict):
        raise ForgeFailureError("failure spec must be a JSON object")
    expected = {
        "unit_id",
        "scenario",
        "expected_behavior",
        "observed_behavior",
        "root_cause",
        "evaluators",
    }
    if set(raw) != expected:
        raise ForgeFailureError("failure spec keys do not match F6 schema")
    for key in ("unit_id", "scenario", "expected_behavior", "observed_behavior", "root_cause"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise ForgeFailureError(f"failure spec {key} must be a non-empty string")
    evaluators = raw["evaluators"]
    if not isinstance(evaluators, dict) or set(evaluators) != set(EVALUATOR_LAYERS):
        raise ForgeFailureError("failure spec must define exactly the four F6 evaluator layers")
    for layer, value in evaluators.items():
        if not isinstance(value, str) or not value.strip():
            raise ForgeFailureError(f"evaluator path for {layer} must be a non-empty string")
    return raw


def register_failure(root: Path, failure_id: str, spec_file: Path) -> dict[str, Any]:
    root = root.resolve()
    failure_id = _failure_id(failure_id)
    failures = _failures_root(root, create=True)
    failure_dir = failures / failure_id
    if failure_dir.exists() or failure_dir.is_symlink():
        raise ForgeFailureError(f"failure already registered: {failure_id}")
    spec = _load_spec(spec_file)
    evaluator_bytes: dict[str, bytes] = {}
    evaluator_meta: dict[str, dict[str, Any]] = {}
    for layer in EVALUATOR_LAYERS:
        source = Path(spec["evaluators"][layer])
        data = _read_regular_file(source, limit=EVALUATOR_LIMIT_BYTES, label=f"{layer} evaluator")
        evaluator_bytes[layer] = data
        evaluator_meta[layer] = {
            "file": f"evaluators/{layer}.py",
            "sha256": _sha256(data),
            "bytes": len(data),
        }

    failure_dir.mkdir()
    evaluators_dir = failure_dir / "evaluators"
    evaluators_dir.mkdir()
    for layer in EVALUATOR_LAYERS:
        (evaluators_dir / f"{layer}.py").write_bytes(evaluator_bytes[layer])

    record: dict[str, Any] = {
        "schema": FAILURE_SCHEMA,
        "failure_id": failure_id,
        "unit_id": spec["unit_id"].strip(),
        "scenario": spec["scenario"].strip(),
        "expected_behavior": spec["expected_behavior"].strip(),
        "observed_behavior": spec["observed_behavior"].strip(),
        "root_cause": spec["root_cause"].strip(),
        "evaluators": evaluator_meta,
        "status": "OPEN",
        "registration_digest": None,
        "locked_by_closure": None,
    }
    record["registration_digest"] = _registration_digest(record)
    _atomic_write(failure_dir / "record.json", _pretty(record))
    return record


def _read_record(root: Path, failure_id: str) -> tuple[Path, dict[str, Any]]:
    failure_id = _failure_id(failure_id)
    failures = _failures_root(root, create=False)
    failure_dir = failures / failure_id
    if failure_dir.is_symlink() or not failure_dir.is_dir():
        raise ForgeFailureError(f"failure not found or unsafe: {failure_id}")
    record_path = failure_dir / "record.json"
    if record_path.is_symlink():
        raise ForgeFailureError("failure record must not be a symlink")
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ForgeFailureError("failure record is unreadable") from exc
    if not isinstance(record, dict):
        raise ForgeFailureError("failure record must be a JSON object")
    expected = {
        "schema",
        "failure_id",
        "unit_id",
        "scenario",
        "expected_behavior",
        "observed_behavior",
        "root_cause",
        "evaluators",
        "status",
        "registration_digest",
        "locked_by_closure",
    }
    if set(record) != expected or record.get("schema") != FAILURE_SCHEMA or record.get("failure_id") != failure_id:
        raise ForgeFailureError("failure record schema/identity mismatch")
    if record.get("status") not in {"OPEN", "LOCKED"}:
        raise ForgeFailureError("failure status is invalid")
    if record.get("registration_digest") != _registration_digest(record):
        raise ForgeFailureError("failure registration digest mismatch")
    if set(record.get("evaluators", {})) != set(EVALUATOR_LAYERS):
        raise ForgeFailureError("failure evaluator layers changed")
    if record["status"] == "OPEN" and record["locked_by_closure"] is not None:
        raise ForgeFailureError("open failure may not claim closure authority")
    if record["status"] == "LOCKED" and not isinstance(record["locked_by_closure"], str):
        raise ForgeFailureError("locked failure is missing closure authority")
    return failure_dir, record


def _verified_evaluator(failure_dir: Path, record: dict[str, Any], layer: str) -> Path:
    meta = record["evaluators"][layer]
    if not isinstance(meta, dict) or set(meta) != {"file", "sha256", "bytes"}:
        raise ForgeFailureError(f"evaluator metadata changed for {layer}")
    path = failure_dir / meta["file"]
    expected = failure_dir / "evaluators" / f"{layer}.py"
    if path != expected:
        raise ForgeFailureError(f"evaluator path changed for {layer}")
    data = _read_regular_file(path, limit=EVALUATOR_LIMIT_BYTES, label=f"stored {layer} evaluator")
    if len(data) != meta["bytes"] or _sha256(data) != meta["sha256"]:
        raise ForgeFailureError(f"evaluator integrity mismatch for {layer}")
    return path


def verify_failure(root: Path, failure_id: str) -> dict[str, Any]:
    failure_dir, record = _read_record(root.resolve(), failure_id)
    for layer in EVALUATOR_LAYERS:
        _verified_evaluator(failure_dir, record, layer)
    return {
        "failure_id": failure_id,
        "status": record["status"],
        "registration_digest": record["registration_digest"],
        "verified": True,
    }


def _git_status(candidate: Path) -> bytes:
    git_exe = shutil.which("git")
    if git_exe is None:
        raise ForgeFailureError("Git is required for F6 evaluator mutation checks")
    probe = subprocess.run(
        [git_exe, "-C", str(candidate), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if probe.returncode != 0 or Path(probe.stdout.strip()).resolve() != candidate.resolve():
        raise ForgeFailureError("F6 candidate must be a Git repository root")
    result = subprocess.run(
        [git_exe, "-C", str(candidate), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        raise ForgeFailureError("unable to snapshot candidate status")
    return result.stdout


def _run_evaluator(path: Path, candidate: Path, layer: str, *, timeout_seconds: float = 20.0) -> dict[str, Any]:
    before = _git_status(candidate)
    env = os.environ.copy()
    env["PWD"] = str(candidate)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    try:
        process = subprocess.Popen(
            [sys.executable, str(path), str(candidate.resolve())],
            cwd=candidate,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=(os.name == "posix"),
        )
    except OSError as exc:
        return {
            "layer": layer,
            "passed": False,
            "exit_code": None,
            "reason_code": "EVALUATOR_LAUNCH_FAILED",
            "stdout": "",
            "stderr": str(exc),
            "stdout_truncated": False,
            "stderr_truncated": False,
            "candidate_mutated": False,
        }
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
        return {
            "layer": layer,
            "passed": False,
            "exit_code": process.returncode,
            "reason_code": "EVALUATOR_TIMEOUT",
            "stdout": out,
            "stderr": err,
            "stdout_truncated": out_truncated,
            "stderr_truncated": err_truncated,
            "candidate_mutated": False,
        }
    after = _git_status(candidate)
    mutated = after != before
    out, out_truncated = _bounded(stdout)
    err, err_truncated = _bounded(stderr)
    passed = process.returncode == 0 and not mutated
    return {
        "layer": layer,
        "passed": passed,
        "exit_code": process.returncode,
        "reason_code": "PASS" if passed else ("EVALUATOR_MUTATED_CANDIDATE" if mutated else "EVALUATOR_FAILED"),
        "stdout": out,
        "stderr": err,
        "stdout_truncated": out_truncated,
        "stderr_truncated": err_truncated,
        "candidate_mutated": mutated,
    }


def _next_attempt_dir(failure_dir: Path) -> tuple[Path, str]:
    closures = failure_dir / "closures"
    if closures.is_symlink() or (closures.exists() and not closures.is_dir()):
        raise ForgeFailureError("failure closure directory is unsafe")
    closures.mkdir(exist_ok=True)
    index = 1
    while True:
        name = f"attempt-{index:04d}"
        path = closures / name
        if not path.exists() and not path.is_symlink():
            return path, name
        index += 1


def close_failure(root: Path, failure_id: str, candidate: Path) -> tuple[dict[str, Any], int]:
    root = root.resolve()
    candidate = candidate.resolve()
    failure_dir, record = _read_record(root, failure_id)
    if record["status"] == "LOCKED":
        raise ForgeFailureError("failure is already LOCKED; use replay")
    evaluators = {layer: _verified_evaluator(failure_dir, record, layer) for layer in EVALUATOR_LAYERS}
    attempt_dir, attempt_name = _next_attempt_dir(failure_dir)
    results: list[dict[str, Any]] = []
    for layer in EVALUATOR_LAYERS:
        results.append(_run_evaluator(evaluators[layer], candidate, layer))
    passed = all(result["passed"] for result in results)
    evidence = {
        "schema": CLOSURE_SCHEMA,
        "failure_id": failure_id,
        "attempt": attempt_name,
        "registration_digest": record["registration_digest"],
        "candidate_root": str(candidate),
        "layers": results,
        "closure_passed": passed,
        "completion_authority": "failure_ledger",
    }
    attempt_dir.mkdir()
    _atomic_write(attempt_dir / "EVIDENCE.json", _pretty(evidence))
    if passed:
        record["status"] = "LOCKED"
        record["locked_by_closure"] = attempt_name
        _atomic_write(failure_dir / "record.json", _pretty(record))
    return evidence, 0 if passed else 3


def replay_failure(root: Path, failure_id: str, candidate: Path) -> tuple[dict[str, Any], int]:
    root = root.resolve()
    candidate = candidate.resolve()
    failure_dir, record = _read_record(root, failure_id)
    if record["status"] != "LOCKED":
        raise ForgeFailureError("failure is not LOCKED")
    evaluator = _verified_evaluator(failure_dir, record, "PERMANENT_EVALUATION")
    result = _run_evaluator(evaluator, candidate, "PERMANENT_EVALUATION")
    evidence = {
        "schema": REPLAY_SCHEMA,
        "failure_id": failure_id,
        "registration_digest": record["registration_digest"],
        "candidate_root": str(candidate),
        "result": result,
        "regression_passed": result["passed"],
        "completion_authority": "failure_ledger",
    }
    return evidence, 0 if result["passed"] else 3


def run_locked_regressions(root: Path, candidate: Path) -> tuple[list[dict[str, Any]], bool]:
    root = root.resolve()
    failures = _failures_root(root, create=False)
    if not failures.exists():
        return [], True
    results: list[dict[str, Any]] = []
    for entry in sorted(failures.iterdir(), key=lambda path: path.name):
        if not entry.is_dir() or entry.is_symlink():
            raise ForgeFailureError("failure ledger contains an unsafe entry")
        _, record = _read_record(root, entry.name)
        if record["status"] != "LOCKED":
            continue
        replay, code = replay_failure(root, entry.name, candidate)
        results.append(replay)
        if code != 0:
            return results, False
    return results, True
