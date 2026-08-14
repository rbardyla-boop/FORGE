"""Read-only DS-D0 deployment authorization gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from typing import Any


CANDIDATE = "bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc"
PARENT = "d8727e7d5946f48ada39199e77df9564a62e4203"
EXPECTED_DS_E1_PACKET = "2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817"
EXPECTED_DS_X0_CONTRACT = "37a6fd797702511d842fd8c25bf650f2159fd0b316b527535d8be17a0b6b4567"
EXPECTED_DS_X0_VERDICT = "590304137f648a5f62ea8d06f69f4537e9146cfa613947ad83b11edfd238aadd"
EXPECTED_DS_H2 = "8591fddf8cdef4224b97b68e374052efb6596ce6281a58535ac78784ee31b549"
EXPECTED_DS_MANIFEST = "2e566f69b9f67f21f642549a409c4fb3ea569e5d067a3db9988172bc3879031d"
EXPECTED_PUBLIC_SURFACE = 302
DS_FILES = tuple(
    f"digital-stewardship-{index:02d}.{suffix}"
    for index in range(7)
    for suffix in ("html", "js")
)
FORGE_ROOT = Path(__file__).resolve().parents[1]
H2_PATH = FORGE_ROOT / "docs/ds/DS_H2_HUMAN_EVIDENCE_DEPENDENCY_RETIREMENT_2026-08-13.md"
X0_CONTRACT_PATH = FORGE_ROOT / "docs/ds/DS_X0_CONTRACT.json"
X0_VERDICT_PATH = FORGE_ROOT / "docs/ds/artifacts/DS_X0_2026-08-13/DS_X0_VERDICT.json"


class DSD0Error(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise DSD0Error(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def run_node(root: Path, script: str, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["node", script, *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


def extract_candidate(repo: Path, commit: str, destination: Path) -> tuple[Path, str]:
    archive = destination / f"{commit}.tar"
    with archive.open("wb") as output:
        result = subprocess.run(
            ["git", "-C", str(repo), "archive", "--format=tar", commit],
            stdout=output,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
    if result.returncode != 0:
        raise DSD0Error(result.stderr.decode(errors="replace").strip())
    root = destination / commit
    root.mkdir()
    with tarfile.open(archive, "r") as handle:
        members = handle.getmembers()
        base = root.resolve()
        for member in members:
            target = (root / member.name).resolve()
            try:
                target.relative_to(base)
            except ValueError as exc:
                raise DSD0Error("candidate archive contains unsafe path") from exc
        handle.extractall(root)
    # The production-curation scripts intentionally read Git's tracked-file
    # list. Recreate that read-only source identity inside the disposable
    # archive rather than accidentally consulting the operator checkout.
    subprocess.run(["git", "init", "--quiet"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True, capture_output=True)
    return root, hashlib.sha256(archive.read_bytes()).hexdigest()


def ds_manifest(root: Path) -> str:
    payload = b"".join(f"{relative}\0".encode() + (root / relative).read_bytes() for relative in DS_FILES)
    return hashlib.sha256(payload).hexdigest()


def verify_candidate(repo: Path) -> dict[str, Any]:
    parent = git(repo, "rev-parse", f"{CANDIDATE}^")
    changed = git(repo, "diff", "--name-only", f"{PARENT}..{CANDIDATE}").splitlines()
    current = git(repo, "rev-parse", "HEAD")
    git(repo, "cat-file", "-e", f"{CANDIDATE}^{{commit}}")
    return {
        "commit_exists": True,
        "candidate_commit": CANDIDATE,
        "candidate_parent": parent,
        "expected_parent": PARENT,
        "authorized_delta": changed,
        "authorized_delta_pass": changed == ["digital-stewardship-00.js"],
        "current_head": current,
        "current_head_is_candidate": current == CANDIDATE,
    }


def verify_evidence() -> dict[str, Any]:
    expected = {
        "ds_h2": (H2_PATH, EXPECTED_DS_H2),
        "ds_x0_contract": (X0_CONTRACT_PATH, EXPECTED_DS_X0_CONTRACT),
        "ds_x0_verdict": (X0_VERDICT_PATH, EXPECTED_DS_X0_VERDICT),
    }
    result = {}
    for name, (path, expected_hash) in expected.items():
        actual = sha256(path)
        result[name] = {"path": str(path.relative_to(FORGE_ROOT)), "expected": expected_hash, "actual": actual, "pass": actual == expected_hash}
    verdict = json.loads(X0_VERDICT_PATH.read_text(encoding="utf-8"))
    result["ds_x0_terminal"] = verdict.get("terminal")
    result["ds_x0_human_boundary"] = verdict.get("human_usability") == "NOT_CLAIMED"
    result["ds_e1_packet_binding"] = EXPECTED_DS_E1_PACKET
    return result


def inspect_candidate_package(candidate_root: Path) -> dict[str, Any]:
    preflight_exit, preflight_stdout, preflight_stderr = run_node(candidate_root, "scripts/release-preflight.mjs")
    upload_exit, upload_stdout, upload_stderr = run_node(candidate_root, "scripts/build-production-upload.mjs", "--list")
    try:
        preflight = json.loads(preflight_stdout)
    except json.JSONDecodeError:
        preflight = {"status": "INVALID_OUTPUT", "raw": preflight_stdout[-2000:]}
    included = [line[4:] for line in upload_stdout.splitlines() if line.startswith("  + ")]
    return {
        "release_preflight_exit": preflight_exit,
        "release_preflight": preflight,
        "release_preflight_stderr": preflight_stderr,
        "upload_list_exit": upload_exit,
        "upload_included_count": len(included),
        "upload_includes_ds00_html": "digital-stewardship-00.html" in included,
        "upload_includes_ds00_js": "digital-stewardship-00.js" in included,
        "upload_stderr": upload_stderr,
    }


def run_gate(clove_repo: Path, output: Path) -> dict[str, Any]:
    clove_repo = clove_repo.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate = verify_candidate(clove_repo)
    evidence = verify_evidence()
    current_status = git(clove_repo, "status", "--porcelain=v1", "--untracked-files=all")
    current_preflight_exit, current_preflight_stdout, current_preflight_stderr = run_node(clove_repo, "scripts/release-preflight.mjs")
    try:
        current_preflight = json.loads(current_preflight_stdout)
    except json.JSONDecodeError:
        current_preflight = {"status": "INVALID_OUTPUT", "raw": current_preflight_stdout[-2000:]}

    with tempfile.TemporaryDirectory(prefix="forge-ds-d0-") as temporary:
        temp_root = Path(temporary)
        candidate_root, archive_hash = extract_candidate(clove_repo, CANDIDATE, temp_root)
        candidate_package = inspect_candidate_package(candidate_root)
        candidate_manifest = ds_manifest(candidate_root)
        parent_root, parent_archive_hash = extract_candidate(clove_repo, PARENT, temp_root)
        parent_manifest = ds_manifest(parent_root)
        candidate_source_clean = all((candidate_root / path).is_file() and not (candidate_root / path).is_symlink() for path in DS_FILES)
        rollback_source_reconstructed = candidate_source_clean and all((parent_root / path).is_file() for path in DS_FILES) and parent_manifest != candidate_manifest

    checks = {
        "exact_candidate_and_delta": candidate["commit_exists"] and candidate["candidate_parent"] == PARENT and candidate["authorized_delta_pass"],
        "ds_e1_ds_x0_ds_h2_evidence_intact": all(item.get("pass", False) for name, item in evidence.items() if isinstance(item, dict) and "pass" in item) and evidence["ds_x0_human_boundary"],
        "candidate_hash_manifest_intact": candidate_manifest == EXPECTED_DS_MANIFEST,
        "candidate_archive_source_clean": candidate_source_clean,
        "clove_checkout_clean": current_status == "",
        "current_head_bound_to_candidate": candidate["current_head_is_candidate"],
        "candidate_production_preflight": candidate_package["release_preflight_exit"] == 0 and candidate_package["release_preflight"].get("status") == "PASS",
        "public_surface_matches_302": candidate_package["upload_included_count"] == EXPECTED_PUBLIC_SURFACE,
        "ds_runtime_not_public_without_explicit_release": not candidate_package["upload_includes_ds00_html"] and not candidate_package["upload_includes_ds00_js"],
        "public_ds_release_boundary_authorized": False,
        "current_production_preflight": current_preflight_exit == 0 and current_preflight.get("status") == "PASS",
        "secrets_and_config_unmodified": current_status == "",
        "deployment_target_identified": True,
        "source_rollback_reconstructed": rollback_source_reconstructed,
        "production_rollback_operator_path_proven": False,
        "post_deploy_smoke_specified": True,
        "human_usability_claim_absent": (
            evidence["ds_x0_human_boundary"]
            and "HUMAN USABILITY NOT CLAIMED" in H2_PATH.read_text(encoding="utf-8")
            and "HUMAN_USABILITY_PASS" not in H2_PATH.read_text(encoding="utf-8")
        ),
        "w2_w4_dependency_non_blocking": True,
    }
    blocking_reasons = []
    if not checks["current_head_bound_to_candidate"]:
        blocking_reasons.append("current Clove HEAD is not the frozen DS-E1 candidate; deployment must use an explicitly bound candidate staging source")
    if not checks["public_surface_matches_302"]:
        blocking_reasons.append(f"exact candidate production upload contains {candidate_package['upload_included_count']} files, not the frozen 302-file baseline")
    if not checks["public_ds_release_boundary_authorized"]:
        blocking_reasons.append("the existing production upload deliberately excludes DS-00; no public DS release-boundary authorization exists in DS-D0")
    if not checks["production_rollback_operator_path_proven"]:
        blocking_reasons.append("Cloudflare production upload/rollback was not executed or proven; this gate has no deployment credential/action")
    terminal = "DS_D0_DEPLOYMENT_AUTHORIZED" if all(checks.values()) else "DS_D0_DEPLOYMENT_BLOCKED"
    result = {
        "schema": "forge.ds-d0.verdict.v1",
        "unit": "DS-D0",
        "terminal": terminal,
        "candidate": candidate,
        "candidate_archive_sha256": archive_hash,
        "rollback_parent_archive_sha256": parent_archive_hash,
        "candidate_ds_manifest_sha256": candidate_manifest,
        "expected_candidate_ds_manifest_sha256": EXPECTED_DS_MANIFEST,
        "candidate_package": candidate_package,
        "current_preflight": current_preflight,
        "current_checkout_status": current_status,
        "checks": checks,
        "blocking_reasons": blocking_reasons,
        "w2_w4_classification": "NON_BLOCKING: DS-D0 uses local Git/archive/Node preflight only; it does not traverse W2/W4 Docker fixture paths.",
        "deployment_target": {
            "host": "clovelearn.io",
            "cloudflare_resource": "wild-hat-6257",
            "path": "owner dashboard static-file upload",
            "write_performed": False,
        },
        "human_usability": "NOT_CLAIMED",
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m forge_core.ds_d0")
    parser.add_argument("--clove-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_gate(args.clove_repo, args.output)
    except (DSD0Error, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"unit": "DS-D0", "terminal": "DS_D0_DEPLOYMENT_BLOCKED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"unit": "DS-D0", "terminal": result["terminal"], "checks": result["checks"], "blocking_reasons": result["blocking_reasons"]}, sort_keys=True))
    return 0 if result["terminal"] == "DS_D0_DEPLOYMENT_AUTHORIZED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
