"""DS-X0 autonomous operator gate.

This module deliberately has no repair or deployment authority.  It creates a
temporary git-archive snapshot, runs the bounded Firefox operator, and emits a
machine-checkable engineering verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import Any


CANDIDATE_COMMIT = "bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc"
PARENT_COMMIT = "d8727e7d5946f48ada39199e77df9564a62e4203"
DS_E1_PACKET_SHA256 = "2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817"
CONTRACT_PATH = Path("docs/ds/DS_X0_CONTRACT.json")
DRIVER_PATH = Path("tests/ds_x0_browser_operator.mjs")
DS_FILES = tuple(
    f"digital-stewardship-{index:02d}.{suffix}"
    for index in range(7)
    for suffix in ("html", "js")
)
EXPECTED_EXECUTIONS = 50


class DSX0Error(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if check and result.returncode != 0:
        raise DSX0Error(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def worktree_fingerprint(repo: Path) -> dict[str, str]:
    return {
        "head": run_git(repo, "rev-parse", "HEAD"),
        "status": run_git(repo, "status", "--porcelain=v1", "--untracked-files=all"),
        "ds_manifest": sha256_bytes(
            b"".join(
                f"{relative}\0".encode() + (repo / relative).read_bytes()
                for relative in DS_FILES
            )
        ),
    }


def _safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r") as handle:
        members = handle.getmembers()
        root = destination.resolve()
        for member in members:
            target = (destination / member.name).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise DSX0Error("candidate archive contains unsafe path") from exc
        handle.extractall(destination)


def make_snapshot(repo: Path, commit: str, destination: Path) -> None:
    archive = destination / "candidate.tar"
    with archive.open("wb") as output:
        result = subprocess.run(
            ["git", "-C", str(repo), "archive", "--format=tar", commit],
            stdout=output,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    if result.returncode != 0:
        raise DSX0Error(result.stderr.decode(errors="replace").strip())
    snapshot = destination / "candidate"
    snapshot.mkdir()
    _safe_extract(archive, snapshot)
    for relative in DS_FILES:
        path = snapshot / relative
        if not path.is_file() or path.is_symlink():
            raise DSX0Error(f"snapshot missing regular file: {relative}")


def verify_candidate(repo: Path) -> dict[str, Any]:
    parent = run_git(repo, "rev-parse", f"{CANDIDATE_COMMIT}^")
    if parent != PARENT_COMMIT:
        raise DSX0Error(f"candidate parent mismatch: {parent}")
    changed = run_git(repo, "diff", "--name-only", f"{PARENT_COMMIT}..{CANDIDATE_COMMIT}").splitlines()
    expected_changed = ["digital-stewardship-00.js"]
    if changed != expected_changed:
        raise DSX0Error(f"candidate delta mismatch: {changed}")
    delta = run_git(repo, "diff", f"{PARENT_COMMIT}..{CANDIDATE_COMMIT}", "--", "digital-stewardship-00.js")
    expected_delta = (
        "-  const recoveryText=state.recoveryCheckResult==='current'?'Recovery verified':"
        "state.recoveryCheckResult==='location'?'Recovery location found':'Recovery still unknown';"
        "\n+  const recoveryText=state.recoveryCheckResult==='current'?'Recovery state inspected':"
        "state.recoveryCheckResult==='location'?'Recovery location found':'Recovery still unknown';"
    )
    if expected_delta not in delta:
        raise DSX0Error("candidate delta does not match the authorized DS-00 Variant C")
    manifest = []
    for relative in DS_FILES:
        blob = run_git(repo, "show", f"{CANDIDATE_COMMIT}:{relative}", check=True)
        # git show text is only used for existence; the byte-accurate manifest
        # is generated from the archive below.
        manifest.append(relative)
    return {
        "commit": CANDIDATE_COMMIT,
        "parent": parent,
        "authorized_delta": expected_changed,
        "source_files": manifest,
        "ds_e1_packet_sha256": DS_E1_PACKET_SHA256,
    }


def load_contract(root: Path) -> tuple[dict[str, Any], str]:
    path = root / CONTRACT_PATH
    raw = path.read_bytes()
    contract = json.loads(raw)
    if contract["unit"] != "DS-X0" or contract["version"] != "1.0":
        raise DSX0Error("DS-X0 contract identity mismatch")
    if contract["execution_count"] != EXPECTED_EXECUTIONS:
        raise DSX0Error("DS-X0 execution count mismatch")
    if contract["candidate"]["commit"] != CANDIDATE_COMMIT:
        raise DSX0Error("DS-X0 candidate binding mismatch")
    if contract["candidate"]["ds_e1_packet_sha256"] != DS_E1_PACKET_SHA256:
        raise DSX0Error("DS-X0 DS-E1 packet binding mismatch")
    return contract, sha256_bytes(raw)


def run_node_driver(snapshot: Path, playwright_root: Path, output: Path) -> dict[str, Any]:
    command = [
        "node",
        str(DRIVER_PATH),
        "--candidate",
        str(snapshot),
        "--playwright-root",
        str(playwright_root),
        "--output",
        str(output),
    ]
    env = os.environ.copy()
    result = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
        env=env,
    )
    if not output.is_file():
        raise DSX0Error(f"browser operator did not produce evidence: {result.stderr.strip()}")
    try:
        evidence = json.loads(output.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DSX0Error("browser operator evidence is not JSON") from exc
    evidence["driver_exit_code"] = result.returncode
    evidence["driver_stderr"] = result.stderr[-4000:]
    evidence["driver_stdout"] = result.stdout[-4000:]
    return evidence


def run_ds_i0(repo: Path, playwright_root: Path) -> dict[str, Any]:
    # Run from the exact temporary archive, never from a potentially different
    # working-tree checkout. Only the already-installed Playwright dependency
    # is mounted into the disposable snapshot.
    for relative in DS_FILES:
        if not (repo / relative).is_file() or (repo / relative).is_symlink():
            raise DSX0Error(f"snapshot source is missing or symlinked: {relative}")
    # The release-boundary tests intentionally ask Git for the curated file
    # list. A temporary index makes that check meaningful for an archive while
    # keeping the archive itself read-only with respect to candidate content.
    subprocess.run(["git", "-C", str(repo), "init", "--quiet"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    node_modules = repo / "node_modules"
    if node_modules.exists() or node_modules.is_symlink():
        raise DSX0Error("candidate archive unexpectedly contains node_modules")
    node_modules.symlink_to(playwright_root.parent, target_is_directory=True)
    tests = sorted(str(path.relative_to(repo)) for path in (repo / "tests/static").glob("ds-i0-*.test.mjs"))
    env = os.environ.copy()
    env["DS_BROWSER"] = "firefox"
    result = subprocess.run(
        ["node", "--test", *tests],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return {
        "command": ["node", "--test", *tests],
        "browser": "firefox",
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def score(contract: dict[str, Any], evidence: dict[str, Any], ds_i0: dict[str, Any], *, candidate_before: dict[str, str], candidate_after: dict[str, str], candidate_meta: dict[str, Any], contract_sha256: str) -> dict[str, Any]:
    records = evidence.get("executions")
    if not isinstance(records, list) or len(records) != EXPECTED_EXECUTIONS:
        raise DSX0Error(f"expected exactly {EXPECTED_EXECUTIONS} execution records")
    by_family: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_family.setdefault(record.get("family", "UNKNOWN"), []).append(record)
    def passed(family: str) -> int:
        return sum(bool(record.get("passed")) for record in by_family.get(family, []))
    def total(family: str) -> int:
        return len(by_family.get(family, []))

    core_total = total("core_task")
    recovery_total = total("failure_recovery")
    core_rate = passed("core_task") / core_total if core_total else 0.0
    recovery_rate = passed("failure_recovery") / recovery_total if recovery_total else 0.0
    replay_records = by_family.get("deterministic_replay", [])
    replay_rate = sum(bool(record.get("passed")) and record.get("replay_equal") is True for record in replay_records) / len(replay_records) if replay_records else 0.0
    false_successes = sum(bool(record.get("false_success")) for record in records)
    safety_failures = sum(bool(record.get("safety_or_privacy_failure")) for record in records)
    corruption = sum(bool(record.get("irrecoverable_corruption")) for record in records)
    leakage = sum(bool(record.get("cross_run_leakage")) for record in records)
    candidate_unchanged = candidate_before == candidate_after
    ds_e1_properties = candidate_meta["authorized_delta"] == ["digital-stewardship-00.js"] and candidate_meta["parent"] == PARENT_COMMIT
    criteria = {
        "critical_safety_privacy_failures": safety_failures == 0,
        "false_successes": false_successes == 0,
        "irrecoverable_state_corruption": corruption == 0,
        "candidate_mutations": candidate_unchanged and evidence.get("candidate_mutated") is False,
        "cross_run_leakage": leakage == 0,
        "core_task_completion_rate": core_rate >= 0.95,
        "recovery_task_completion_rate": recovery_rate >= 0.95,
        "deterministic_replay_rate": replay_rate == 1.0,
        "ds_i0_regression": bool(ds_i0.get("passed")),
        "ds_e1_properties": ds_e1_properties,
    }
    terminal = (
        "ENGINEERING_RELEASE_SUPPORTED / HUMAN_USABILITY_NOT_CLAIMED"
        if all(criteria.values()) and evidence.get("driver_exit_code") == 0
        else "ENGINEERING_REPAIR_REQUIRED / HUMAN_USABILITY_NOT_CLAIMED"
    )
    return {
        "schema": "forge.ds-x0.verdict.v1",
        "unit": "DS-X0",
        "terminal": terminal,
        "human_usability": "NOT_CLAIMED",
        "candidate": candidate_meta,
        "contract_sha256": contract_sha256,
        "execution_count": len(records),
        "family_counts": {family: len(items) for family, items in sorted(by_family.items())},
        "metrics": {
            "core_task": {"passed": passed("core_task"), "total": core_total, "rate": core_rate},
            "failure_recovery": {"passed": passed("failure_recovery"), "total": recovery_total, "rate": recovery_rate},
            "deterministic_replay": {"passed": sum(bool(r.get("passed")) for r in replay_records), "total": len(replay_records), "rate": replay_rate},
            "false_successes": false_successes,
            "safety_or_privacy_failures": safety_failures,
            "irrecoverable_corruption": corruption,
            "cross_run_leakage": leakage,
        },
        "criteria": criteria,
        "ds_i0": ds_i0,
        "candidate_fingerprint_before": candidate_before,
        "candidate_fingerprint_after": candidate_after,
        "operator_evidence_sha256": sha256_file(Path(evidence["evidence_path"])),
    }


def run(root: Path, candidate_repo: Path, playwright_root: Path, output_dir: Path) -> dict[str, Any]:
    root = root.resolve()
    candidate_repo = candidate_repo.resolve()
    playwright_root = playwright_root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract, contract_sha256 = load_contract(root)
    candidate_meta = verify_candidate(candidate_repo)
    candidate_before = worktree_fingerprint(candidate_repo)
    if candidate_before["head"] != run_git(candidate_repo, "rev-parse", "HEAD"):
        raise DSX0Error("candidate HEAD could not be read consistently")

    with tempfile.TemporaryDirectory(prefix="forge-ds-x0-") as temp:
        temp_root = Path(temp)
        make_snapshot(candidate_repo, CANDIDATE_COMMIT, temp_root)
        snapshot = temp_root / "candidate"
        manifest = b"".join(
            f"{relative}\0".encode() + (snapshot / relative).read_bytes() for relative in DS_FILES
        )
        candidate_meta["snapshot_ds_manifest_sha256"] = sha256_bytes(manifest)
        operator_path = output_dir / "DS_X0_OPERATOR_EVIDENCE.json"
        evidence = run_node_driver(snapshot, playwright_root, operator_path)
        evidence["evidence_path"] = str(operator_path)
        ds_i0 = run_ds_i0(snapshot, playwright_root)
    candidate_after = worktree_fingerprint(candidate_repo)
    verdict = score(
        contract,
        evidence,
        ds_i0,
        candidate_before=candidate_before,
        candidate_after=candidate_after,
        candidate_meta=candidate_meta,
        contract_sha256=contract_sha256,
    )
    verdict_path = output_dir / "DS_X0_VERDICT.json"
    verdict_path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verdict["verdict_path"] = str(verdict_path)
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m forge_core.ds_x0")
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--playwright-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(Path(__file__).resolve().parents[1], args.candidate_repo, args.playwright_root, args.output_dir)
    except (DSX0Error, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"unit": "DS-X0", "terminal": "ENGINEERING_REPAIR_REQUIRED / HUMAN_USABILITY_NOT_CLAIMED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["terminal"].startswith("ENGINEERING_RELEASE_SUPPORTED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
