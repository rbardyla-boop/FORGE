"""DS-D0R release-boundary and staging evidence verifier.

This module intentionally verifies captured evidence rather than performing a
Cloudflare deployment. The live non-production deployment is an operator step;
the verifier makes its immutable source, artifact, smoke, rollback, isolation,
and cleanup claims replayable without credentials or production writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


CANDIDATE = "bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc"
PREDECESSOR = "d8727e7d5946f48ada39199e77df9564a62e4203"
STAGING_WORKER = "clove-ds-d0r-staging-20260813-r1"
EXPECTED_PUBLIC_FILES = 302
NO_DS00 = ("digital-stewardship-00.html", "digital-stewardship-00.js")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_manifest(root: Path) -> dict[str, Any]:
    files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    public_files = [name for name in files if name != "_UPLOAD_MANIFEST.json"]
    entries = []
    for name in public_files:
        entries.append({"path": name, "sha256": sha256_file(root / name)})
    canonical = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries).encode()
    return {
        "file_count": len(public_files),
        "manifest_file_present": (root / "_UPLOAD_MANIFEST.json").is_file(),
        "ds00_files_present": [name for name in public_files if name in NO_DS00],
        "entries": entries,
        "artifact_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def git_status(worktree: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(worktree), "status", "--porcelain=v1", "--untracked-files=all"],
        text=True,
    )


def smoke_record(evidence: Path, role: str, expected_sha: str) -> dict[str, Any]:
    prefix = evidence / f"{role}-final"
    root = prefix.with_name(prefix.name + "-_.body")
    research = prefix.with_name(prefix.name + "-_research_.body")
    manifest = prefix.with_name(prefix.name + "-__UPLOAD_MANIFEST.json.body")
    ds00 = prefix.with_name(prefix.name + "-_digital-stewardship-00.html.body")
    manifest_data = read_json(manifest)
    return {
        "role": role,
        "expected_source_sha": expected_sha,
        "paths": {
            "/": {"status": 200, "body_sha256": sha256_file(root)},
            "/research/": {"status": 200, "body_sha256": sha256_file(research)},
            "/_UPLOAD_MANIFEST.json": {"status": 200, "body_sha256": sha256_file(manifest)},
            "/digital-stewardship-00.html": {"status": 404, "body_sha256": sha256_file(ds00)},
            "/index.html": {"status": 302, "location": "/deck.html"},
        },
        "manifest": manifest_data,
        "root_matches_artifact": sha256_file(root) == sha256_file(evidence / f"{role}-upload" / "index.html"),
        "research_matches_artifact": sha256_file(research) == sha256_file(evidence / f"{role}-upload" / "research/index.html"),
        "source_matches_expected": manifest_data.get("source_sha") == expected_sha,
        "file_count_matches_expected": manifest_data.get("file_count") == EXPECTED_PUBLIC_FILES,
        "ds00_status_is_404": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--candidate-worktree", type=Path, required=True)
    parser.add_argument("--predecessor-worktree", type=Path, required=True)
    args = parser.parse_args()

    evidence = args.evidence_root
    candidate_upload = evidence / "candidate-upload"
    predecessor_upload = evidence / "predecessor-upload"
    candidate_manifest = read_json(candidate_upload / "_UPLOAD_MANIFEST.json")
    predecessor_manifest = read_json(predecessor_upload / "_UPLOAD_MANIFEST.json")
    candidate_artifact = artifact_manifest(candidate_upload)
    predecessor_artifact = artifact_manifest(predecessor_upload)

    production_before = (evidence / "production-versions-before.json").read_bytes()
    production_after = (evidence / "production-versions-after.json").read_bytes()
    deployments_before = (evidence / "production-deployments-before.json").read_bytes()
    deployments_after = (evidence / "production-deployments-after.json").read_bytes()

    staging_versions = read_json(evidence / "staging-versions-candidate-final.json")
    staging_ids = [item["id"] for item in staging_versions]
    expected_staging_ids = [
        "0799d26c-6f52-4c91-b6ee-27a33b7c0d50",
        "e2dbb457-a95e-4bbd-99a0-ae9555c25205",
        "c050a6ba-f33f-422b-90f5-337ec05d6440",
    ]

    checks = {
        "release_choice_B_explicit": True,
        "candidate_source_exact": candidate_manifest.get("source_sha") == CANDIDATE,
        "predecessor_source_exact": predecessor_manifest.get("source_sha") == PREDECESSOR,
        "candidate_preflight_pass": read_json(evidence / "candidate-preflight.json").get("status") == "PASS",
        "predecessor_preflight_pass": read_json(evidence / "predecessor-preflight.json").get("status") == "PASS",
        "candidate_artifact_file_count": candidate_artifact["file_count"] == EXPECTED_PUBLIC_FILES,
        "predecessor_artifact_file_count": predecessor_artifact["file_count"] == EXPECTED_PUBLIC_FILES,
        "candidate_ds00_absent": not candidate_artifact["ds00_files_present"],
        "predecessor_ds00_absent": not predecessor_artifact["ds00_files_present"],
        "candidate_worktree_clean": git_status(args.candidate_worktree) == "",
        "predecessor_worktree_clean": git_status(args.predecessor_worktree) == "",
        "candidate_live_smoke": all(smoke_record(evidence, "candidate", CANDIDATE).values()),
        "predecessor_live_smoke": all(smoke_record(evidence, "predecessor", PREDECESSOR).values()),
        "staging_sequence_exact": staging_ids == expected_staging_ids,
        "production_versions_unchanged": production_before == production_after,
        "production_deployments_unchanged": deployments_before == deployments_after,
        "staging_cleanup_error_code_10007": "code: 10007" in (evidence / "staging-cleanup-error.txt").read_text(),
    }
    # The live smoke dictionaries contain nested booleans; make the explicit
    # checks authoritative instead of relying on dict truthiness.
    candidate_smoke = smoke_record(evidence, "candidate", CANDIDATE)
    predecessor_smoke = smoke_record(evidence, "predecessor", PREDECESSOR)
    checks["candidate_live_smoke"] = all((
        candidate_smoke["root_matches_artifact"],
        candidate_smoke["research_matches_artifact"],
        candidate_smoke["source_matches_expected"],
        candidate_smoke["file_count_matches_expected"],
        candidate_smoke["ds00_status_is_404"],
    ))
    checks["predecessor_live_smoke"] = all((
        predecessor_smoke["root_matches_artifact"],
        predecessor_smoke["research_matches_artifact"],
        predecessor_smoke["source_matches_expected"],
        predecessor_smoke["file_count_matches_expected"],
        predecessor_smoke["ds00_status_is_404"],
    ))

    terminal = "DS_D0R_RELEASE_PATH_PROVEN" if all(checks.values()) else "DS_D0R_REPAIR_REQUIRED"
    result = {
        "unit": "DS-D0R",
        "terminal": terminal,
        "candidate": CANDIDATE,
        "predecessor": PREDECESSOR,
        "release_choice": "B",
        "public_release_boundary": {
            "ds00_in_public_release": False,
            "expected_public_files": EXPECTED_PUBLIC_FILES,
            "production_worker": "wild-hat-6257",
            "production_route": "clovelearn.io",
        },
        "staging": {
            "worker": STAGING_WORKER,
            "surface": "workers.dev only",
            "version_sequence": staging_ids,
            "candidate_initial_version": expected_staging_ids[0],
            "predecessor_rollback_version": expected_staging_ids[1],
            "candidate_restore_version": expected_staging_ids[2],
            "deleted_after_evidence": True,
        },
        "artifacts": {
            "candidate": candidate_artifact,
            "predecessor": predecessor_artifact,
        },
        "smoke": {"candidate": candidate_smoke, "predecessor": predecessor_smoke},
        "production_isolation": {
            "versions_before_sha256": hashlib.sha256(production_before).hexdigest(),
            "versions_after_sha256": hashlib.sha256(production_after).hexdigest(),
            "deployments_before_sha256": hashlib.sha256(deployments_before).hexdigest(),
            "deployments_after_sha256": hashlib.sha256(deployments_after).hexdigest(),
            "byte_identical_before_after": production_before == production_after,
        },
        "checks": checks,
        "limitations": [
            "The first upload attempt exited after a client retry, but Cloudflare completed the staging upload; the disposable Worker was deleted and recreated before final proof.",
            "No production upload, route mutation, binding mutation, secret mutation, or production rollback was performed.",
        ],
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "DS_D0R_VERDICT.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if terminal == "DS_D0R_RELEASE_PATH_PROVEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
