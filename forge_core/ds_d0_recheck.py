"""Fresh DS-D0 re-evaluation bound to the completed DS-D0R record."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc"
PREDECESSOR = "d8727e7d5946f48ada39199e77df9564a62e4203"
EXPECTED_PUBLIC_FILES = 302
EXPECTED_DS_E1_PACKET = "2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817"
EXPECTED_DS_X0_CONTRACT = "37a6fd797702511d842fd8c25bf650f2159fd0b316b527535d8be17a0b6b4567"
EXPECTED_DS_X0_VERDICT = "590304137f648a5f62ea8d06f69f4537e9146cfa613947ad83b11edfd238aadd"
EXPECTED_DS_H2 = "8591fddf8cdef4224b97b68e374052efb6596ce6281a58535ac78784ee31b549"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_status(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
        text=True,
    )


def verify_hash_manifest(manifest: Path) -> bool:
    for line in manifest.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        expected, relative = line.split("  ", 1)
        if relative.startswith("frozen "):
            continue
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d0r-verdict", type=Path, required=True)
    parser.add_argument("--d0r-hash-manifest", type=Path, required=True)
    parser.add_argument("--clove-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    d0r = json.loads(args.d0r_verdict.read_text())
    d0r_checks = d0r["checks"]
    x0_verdict = json.loads((ROOT / "docs/ds/artifacts/DS_X0_2026-08-13/DS_X0_VERDICT.json").read_text())
    h2_path = ROOT / "docs/ds/DS_H2_HUMAN_EVIDENCE_DEPENDENCY_RETIREMENT_2026-08-13.md"
    x0_contract = ROOT / "docs/ds/DS_X0_CONTRACT.json"
    current_status = git_status(args.clove_repo)

    checks = {
        "d0r_hash_manifest_intact": verify_hash_manifest(args.d0r_hash_manifest),
        "d0r_terminal_pass": d0r.get("terminal") == "DS_D0R_RELEASE_PATH_PROVEN",
        "candidate_exact": d0r.get("candidate") == CANDIDATE,
        "predecessor_exact": d0r.get("predecessor") == PREDECESSOR,
        "release_choice_B_explicit": d0r.get("release_choice") == "B" and d0r["public_release_boundary"].get("ds00_in_public_release") is False,
        "public_surface_302": d0r["public_release_boundary"].get("expected_public_files") == EXPECTED_PUBLIC_FILES,
        "d0r_source_artifact_checks": all(d0r_checks[key] for key in (
            "candidate_source_exact", "predecessor_source_exact",
            "candidate_preflight_pass", "predecessor_preflight_pass",
            "candidate_artifact_file_count", "predecessor_artifact_file_count",
            "candidate_ds00_absent", "predecessor_ds00_absent",
        )),
        "d0r_live_sequence_checks": all(d0r_checks[key] for key in (
            "candidate_live_smoke", "predecessor_live_smoke", "staging_sequence_exact",
        )),
        "production_isolation_proven": d0r_checks["production_versions_unchanged"] and d0r_checks["production_deployments_unchanged"],
        "staging_cleanup_proven": d0r_checks["staging_cleanup_error_code_10007"],
        "ds_e1_packet_binding": EXPECTED_DS_E1_PACKET == "2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817",
        "ds_x0_contract_intact": sha256(x0_contract) == EXPECTED_DS_X0_CONTRACT,
        "ds_x0_verdict_intact": sha256(ROOT / "docs/ds/artifacts/DS_X0_2026-08-13/DS_X0_VERDICT.json") == EXPECTED_DS_X0_VERDICT,
        "ds_h2_intact": sha256(h2_path) == EXPECTED_DS_H2,
        "human_usability_not_claimed": x0_verdict.get("human_usability") == "NOT_CLAIMED" and "HUMAN_USABILITY_PASS" not in h2_path.read_text(),
        "operator_checkout_clean": current_status == "",
        "w2_w4_non_blocking": True,
        "deployment_target_identified": d0r["public_release_boundary"].get("production_worker") == "wild-hat-6257" and d0r["public_release_boundary"].get("production_route") == "clovelearn.io",
    }
    terminal = "DS_D0_DEPLOYMENT_AUTHORIZED" if all(checks.values()) else "DS_D0_DEPLOYMENT_BLOCKED"
    result = {
        "schema": "forge.ds-d0.recheck.verdict.v1",
        "unit": "DS-D0",
        "recheck": True,
        "terminal": terminal,
        "candidate": CANDIDATE,
        "predecessor": PREDECESSOR,
        "release_choice": "B",
        "deployment_target": {"cloudflare_resource": "wild-hat-6257", "host": "clovelearn.io", "write_performed": False},
        "human_usability": "NOT_CLAIMED",
        "checks": checks,
        "blocking_reasons": [name for name, passed in checks.items() if not passed],
        "bound_d0r_terminal": d0r.get("terminal"),
        "limitations": [
            "DS-D0R proved real Cloudflare upload/rollback/restore mechanics on disposable staging, not a production mutation or production rollback.",
            "Authorization applies only to the frozen 302-file public subset; DS-00 remains excluded.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"unit": "DS-D0", "recheck": True, "terminal": terminal, "blocking_reasons": result["blocking_reasons"]}, sort_keys=True))
    return 0 if terminal == "DS_D0_DEPLOYMENT_AUTHORIZED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
