from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .gate import ForgeGateError, run_final_gate as _run_legacy_final_gate
from .lifecycle import CANDIDATE_VERIFIED
from .sealed_lifecycle import ATTEMPT, candidate_ref


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


def _load_f4_evidence(root: Path, unit_id: str) -> tuple[Path, dict[str, Any], bytes]:
    attempt = root / ".forge" / "runs" / unit_id / ATTEMPT
    evidence_path = attempt / "EVIDENCE.json"
    diff_path = attempt / "APPLIED.diff"
    if evidence_path.is_symlink() or diff_path.is_symlink():
        raise ForgeGateError("sealed final gate refuses symlinked F4 evidence")
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        diff = diff_path.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise ForgeGateError("sealed final gate cannot read F4 evidence") from exc
    if not isinstance(evidence, dict):
        raise ForgeGateError("sealed final gate requires object F4 evidence")
    if evidence.get("terminal_state") != CANDIDATE_VERIFIED:
        raise ForgeGateError("sealed final gate requires CANDIDATE_VERIFIED evidence")
    return attempt, evidence, diff


def _verify_candidate_lineage(root: Path, unit_id: str) -> tuple[str, str, str]:
    _, evidence, applied_diff = _load_f4_evidence(root, unit_id)
    expected_ref = candidate_ref(unit_id)
    if evidence.get("candidate_ref") != expected_ref:
        raise ForgeGateError("F4 candidate ref evidence mismatch")
    if evidence.get("candidate_seal_authority") != "git_ref":
        raise ForgeGateError("F4 candidate seal authority mismatch")
    recorded_commit = evidence.get("candidate_commit")
    if not isinstance(recorded_commit, str) or len(recorded_commit) != 40:
        raise ForgeGateError("F4 candidate commit evidence is missing or invalid")

    git_exe = shutil.which("git")
    if git_exe is None:
        raise ForgeGateError("Git is required for sealed final gate")
    resolved = _git_text(git_exe, root, "rev-parse", "--verify", f"{expected_ref}^{{commit}}")
    if resolved.returncode != 0 or resolved.stdout.strip() != recorded_commit:
        raise ForgeGateError("authoritative candidate ref does not match F4 candidate commit")

    parents = _git_text(git_exe, root, "rev-list", "--parents", "-n", "1", recorded_commit)
    parts = parents.stdout.strip().split()
    if parents.returncode != 0 or len(parts) != 2 or parts[0] != recorded_commit:
        raise ForgeGateError("sealed candidate must be a single-parent commit")
    baseline = parts[1]
    if evidence.get("baseline_commit") != baseline:
        raise ForgeGateError("F4 baseline evidence does not match sealed candidate parent")

    sealed_diff = _git_bytes(
        git_exe,
        root,
        "diff",
        "--binary",
        "--full-index",
        "--no-ext-diff",
        "--no-renames",
        baseline,
        recorded_commit,
    )
    if sealed_diff.returncode != 0 or sealed_diff.stdout != applied_diff:
        raise ForgeGateError("sealed candidate lineage does not match exact F4 applied diff")
    return expected_ref, recorded_commit, baseline


def run_final_gate(root: Path, unit_id: str, evaluator_file: Path, **kwargs: Any):
    root = root.resolve()
    ref, commit, baseline = _verify_candidate_lineage(root, unit_id)
    report, code = _run_legacy_final_gate(root, unit_id, evaluator_file, **kwargs)
    report["candidate_ref"] = ref
    report["candidate_commit"] = commit
    report["sealed_baseline_commit"] = baseline
    report["candidate_lineage_authority"] = "git_ref"
    final_path = root / ".forge" / "runs" / unit_id / ATTEMPT / "FINAL_EVALUATION.json"
    if final_path.is_symlink() or not final_path.is_file():
        raise ForgeGateError("legacy final gate did not persist final evidence safely")
    final_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report, code
