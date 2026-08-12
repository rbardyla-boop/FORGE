from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .lifecycle import (
    CANDIDATE_VERIFIED,
    REPAIR_REQUIRED,
    ForgeLifecycleError,
    run_unit_attempt as _run_legacy_unit_attempt,
)

ATTEMPT = "attempt-0001"
ZERO_OID = "0" * 40


def candidate_ref(unit_id: str) -> str:
    return f"refs/forge/candidates/{unit_id}/{ATTEMPT}"


def _git_text(git_exe: str, root: Path, *args: str, env: dict[str, str] | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [git_exe, "-C", str(root), *args],
        text=True,
        input=input_text,
        capture_output=True,
        check=False,
        timeout=10,
        env=env,
    )


def _git_bytes(git_exe: str, root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [os.fsencode(git_exe), b"-C", os.fsencode(root), *[os.fsencode(arg) for arg in args]],
        capture_output=True,
        check=False,
        timeout=10,
    )


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _attempt_dir(root: Path, unit_id: str) -> Path:
    return root / ".forge" / "runs" / unit_id / ATTEMPT


def _write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    if path.is_symlink():
        raise ForgeLifecycleError("F4 evidence must not be a symlink during candidate sealing")
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _seal_commit(
    git_exe: str,
    root: Path,
    unit_id: str,
    baseline: str,
    contract_digest: str,
    applied_diff: bytes,
) -> tuple[str, str]:
    ref = candidate_ref(unit_id)
    existing = _git_text(git_exe, root, "rev-parse", "--verify", "--quiet", ref)
    if existing.returncode == 0:
        raise ForgeLifecycleError("authoritative candidate ref already exists for attempt")

    temp_parent = Path(tempfile.mkdtemp(prefix="forge-seal-"))
    worktree = temp_parent / "candidate"
    diff_path = temp_parent / "APPLIED.diff"
    diff_path.write_bytes(applied_diff)
    added = False
    try:
        result = _git_text(git_exe, root, "worktree", "add", "--detach", "--quiet", str(worktree), baseline)
        if result.returncode != 0:
            raise ForgeLifecycleError("candidate seal worktree creation failed")
        added = True
        applied = _git_text(
            git_exe,
            worktree,
            "apply",
            "--index",
            "--whitespace=error-all",
            str(diff_path),
        )
        if applied.returncode != 0:
            raise ForgeLifecycleError("candidate seal diff replay failed")
        staged = _git_bytes(
            git_exe,
            worktree,
            "diff",
            "--cached",
            "--binary",
            "--full-index",
            "--no-ext-diff",
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
        if staged.returncode != 0 or unstaged.returncode != 0:
            raise ForgeLifecycleError("candidate seal diff verification failed")
        if staged.stdout != applied_diff or unstaged.stdout:
            raise ForgeLifecycleError("candidate seal does not reproduce exact F4 diff")

        tree = _git_text(git_exe, worktree, "write-tree")
        if tree.returncode != 0 or not tree.stdout.strip():
            raise ForgeLifecycleError("candidate seal tree creation failed")

        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "Forge Candidate Seal",
                "GIT_AUTHOR_EMAIL": "forge-candidate@local.invalid",
                "GIT_COMMITTER_NAME": "Forge Candidate Seal",
                "GIT_COMMITTER_EMAIL": "forge-candidate@local.invalid",
                "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
                "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
            }
        )
        message = f"FORGE CANDIDATE {unit_id}\ncontract {contract_digest}\n"
        commit = _git_text(
            git_exe,
            worktree,
            "commit-tree",
            tree.stdout.strip(),
            "-p",
            baseline,
            env=env,
            input_text=message,
        )
        candidate_commit = commit.stdout.strip()
        if commit.returncode != 0 or len(candidate_commit) != 40:
            raise ForgeLifecycleError("candidate seal commit creation failed")

        updated = _git_text(git_exe, root, "update-ref", ref, candidate_commit, ZERO_OID)
        if updated.returncode != 0:
            raise ForgeLifecycleError("candidate seal ref creation failed")
        return ref, candidate_commit
    finally:
        if added:
            _git_text(git_exe, root, "worktree", "remove", "--force", str(worktree))
        shutil.rmtree(temp_parent, ignore_errors=True)


def run_unit_attempt(
    root: Path,
    unit_id: str,
    patch_file: Path,
    **kwargs: Any,
) -> tuple[dict[str, Any], int]:
    root = root.resolve()
    git_exe = shutil.which("git")
    captured_baseline: str | None = None
    if git_exe is not None:
        head = _git_text(git_exe, root, "rev-parse", "--verify", "HEAD")
        if head.returncode == 0 and head.stdout.strip():
            captured_baseline = head.stdout.strip()

    evidence, code = _run_legacy_unit_attempt(root, unit_id, patch_file, **kwargs)
    if evidence.get("terminal_state") != CANDIDATE_VERIFIED:
        return evidence, code

    evidence_path = _attempt_dir(root, unit_id) / "EVIDENCE.json"
    ref_created: str | None = None
    try:
        if git_exe is None or captured_baseline is None:
            raise ForgeLifecycleError("candidate sealing requires captured Git HEAD authority")
        if evidence.get("baseline_commit") != captured_baseline:
            raise ForgeLifecycleError("F4 baseline changed between command entry and verified attempt")
        diff_path = _attempt_dir(root, unit_id) / "APPLIED.diff"
        if diff_path.is_symlink() or not diff_path.is_file():
            raise ForgeLifecycleError("candidate sealing requires exact F4 applied diff")
        applied_diff = diff_path.read_bytes()
        if evidence.get("applied_diff_sha256") != _sha256(applied_diff):
            raise ForgeLifecycleError("candidate sealing detected applied-diff binding mismatch")
        ref, commit = _seal_commit(
            git_exe,
            root,
            unit_id,
            captured_baseline,
            str(evidence.get("contract_digest")),
            applied_diff,
        )
        ref_created = ref
        evidence["candidate_ref"] = ref
        evidence["candidate_commit"] = commit
        evidence["candidate_seal_authority"] = "git_ref"
        _write_evidence(evidence_path, evidence)
        return evidence, 0
    except (OSError, subprocess.TimeoutExpired, ForgeLifecycleError) as exc:
        if ref_created and git_exe:
            _git_text(git_exe, root, "update-ref", "-d", ref_created)
        evidence["terminal_state"] = REPAIR_REQUIRED
        evidence["reason_code"] = "CANDIDATE_SEAL_FAILED"
        evidence["candidate_ref"] = None
        evidence["candidate_commit"] = None
        evidence["candidate_seal_authority"] = "git_ref"
        evidence["candidate_seal_detail"] = str(exc)[:4096]
        _write_evidence(evidence_path, evidence)
        return evidence, 3
