"""DS-D2 public replay verifier.

This verifier consumes sealed production captures.  It never writes to
Cloudflare and treats the deliberately excluded DS-00 runtime as outside the
public-release claim rather than pretending that a 404 exercised DS-X0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


CANDIDATE = "bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc"
VERSION_ID = "53c7c021-96a5-495b-b622-16bd1b368967"
DEPLOYMENT_ID = "662f9820-b551-449e-9647-8f1961052436"
WORKER = "wild-hat-6257"
CUSTOM_DOMAIN = "clovelearn.io"
ORIGIN = "https://wild-hat-6257.rbardyla.workers.dev"
ARTIFACT_SHA256 = "6221cb59c694ce0fc9261ba1f38975fbb8dcdd282bceb78bce967d48ae74c794"
UPLOAD_MANIFEST_SHA256 = "d97efc86b8ba5992dd95bd6b3b990c42b58008386ccdbcaea7b7e23c31528c02"
PUBLIC_FILE_COUNT = 302
DS_PATHS = [
    *(f"digital-stewardship-{index:02d}.{suffix}" for index in range(7) for suffix in ("html", "js")),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def status(path: Path) -> int:
    return int(path.read_text().strip())


def body_hash(path: Path) -> str:
    return sha256_file(path)


def normalize_html(text: str) -> str:
    """Remove only the documented Cloudflare edge HTML insertions."""

    text = re.sub(r"\s*<script>\(function\(\)\{function c\(\).*?</script>", "", text, flags=re.S)
    text = re.sub(
        r'\s*<a href="https://clovelearn\.io/cdn-cgi/content\?[^\"]+"[^>]*></a>',
        "",
        text,
    )
    text = re.sub(r"\s*<style type=\"text/css\">@font-face.*?</style>", "", text, flags=re.S)
    text = re.sub(r"\s*<link rel=\"preconnect\" href=\"https://fonts\.googleapis\.com\">", "", text)
    text = re.sub(r"\s*<link rel=\"preconnect\" href=\"https://fonts\.gstatic\.com\" crossorigin>", "", text)
    text = re.sub(r"\s*<link href=\"https://fonts\.googleapis\.com/[^>]+>", "", text)
    return text.replace("</script></body>", "</script>\n</body>")


def normalize_robots(text: str) -> str:
    """Remove the documented Cloudflare managed-content block."""

    return re.sub(r"\A.*?# END Cloudflare Managed Content\n\n", "", text, flags=re.S)


def artifact_manifest(upload: Path) -> dict[str, Any]:
    files = sorted(path.relative_to(upload).as_posix() for path in upload.rglob("*") if path.is_file())
    public_files = [name for name in files if name != "_UPLOAD_MANIFEST.json"]
    entries = [{"path": name, "sha256": sha256_file(upload / name)} for name in public_files]
    canonical = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries).encode()
    return {
        "file_count": len(public_files),
        "manifest_file_present": (upload / "_UPLOAD_MANIFEST.json").is_file(),
        "ds00_files_present": [name for name in public_files if name in DS_PATHS],
        "artifact_sha256": sha256_bytes(canonical),
        "upload_manifest_sha256": sha256_file(upload / "_UPLOAD_MANIFEST.json"),
    }


def same_bytes(*paths: Path) -> bool:
    first = paths[0].read_bytes()
    return all(path.read_bytes() == first for path in paths[1:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--upload-root", type=Path, required=True)
    parser.add_argument("--d1-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence = args.evidence_root
    d1 = read_json(args.d1_receipt)
    before_metadata = evidence / "metadata-before.json"
    after_metadata = evidence / "metadata-after.json"
    before_deployments = evidence / "deployments-before.json"
    after_deployments = evidence / "deployments-after.json"
    origin_all = read_json(evidence / "origin-all-files.json")
    browser = read_json(evidence / "browser-replay.json")
    upload = artifact_manifest(args.upload_root)
    metadata_after = read_json(after_metadata)
    active_versions = [item["id"] for item in metadata_after if item.get("id") == VERSION_ID]

    origin_stems = {
        "root": (200, "dbd4909507f349c54ad637d498031227fadac0f09d08657f401d58feb3d16c16"),
        "research": (200, "2a507cf1d64cde66105a484011363e4f62e7c321b79a502dfa2c822ae48e77ec"),
        "research_css": (200, "407b584209954fb2ef9a52cac3a34afe312a997e2f09a53f701b7dd219e15e01"),
        "research_js": (200, "d53c1cde2d46e25424108a45ccbe111cf75585cdcdde52e08061ee35a345af43"),
        "signals": (200, "049ce475055644812542d6bb155007ddb2127a464e5754157badf7bbb89bc50e"),
        "arcade": (200, "74d2053d79b0db1d041e7dac4e34dbd6f7e8e2874f2bcd70fb10c6a9b5614f2b"),
        "arcade_js": (200, "fd86d776f8366286fdab2003c810c8b929ca67f97894a86c0ff2f7fd5c42146e"),
        "robots": (200, "52a672b0ca8e3704f016f01003882c6f0f2189179fc0f1f3ebdc887d43273046"),
        "manifest": (200, UPLOAD_MANIFEST_SHA256),
    }
    origin_checks = {}
    for stem, (expected_status, expected_hash) in origin_stems.items():
        origin_checks[stem] = {
            "status": status(evidence / f"origin-{stem}.status") == expected_status,
            "body_sha256": body_hash(evidence / f"origin-{stem}.body") == expected_hash,
        }

    public_exact_stems = ("research_css", "research_js", "signals", "arcade_js", "manifest")
    public_exact = {
        stem: {
            "status": status(evidence / f"public-{stem}.status") == 200,
            "matches_origin": body_hash(evidence / f"public-{stem}.body") == body_hash(evidence / f"origin-{stem}.body"),
        }
        for stem in public_exact_stems
    }
    public_html = {}
    for stem in ("root", "research", "arcade"):
        origin_text = (evidence / f"origin-{stem}.body").read_text()
        public_text = (evidence / f"public-{stem}.body").read_text()
        public_html[stem] = {
            "status": status(evidence / f"public-{stem}.status") == 200,
            "normalized_matches_origin": normalize_html(origin_text) == normalize_html(public_text),
            "normalization": ["Cloudflare challenge script", "Cloudflare hidden challenge link", "Cloudflare font transform"],
        }
    public_robots = {
        "status": status(evidence / "public-robots.status") == 200,
        "normalized_matches_origin": normalize_robots((evidence / "origin-robots.body").read_text()) == normalize_robots((evidence / "public-robots.body").read_text()),
        "normalization": ["Cloudflare managed content block"],
    }

    checks = {
        "d1_receipt_binding_intact": d1.get("terminal") == "DS_D1_DEPLOYMENT_PASS" and d1.get("candidate") == CANDIDATE,
        "release_choice_B_and_public_boundary_intact": d1.get("release_choice") == "B" and d1.get("public_file_count") == PUBLIC_FILE_COUNT,
        "artifact_manifest_matches_frozen": upload["file_count"] == PUBLIC_FILE_COUNT and upload["artifact_sha256"] == ARTIFACT_SHA256 and upload["upload_manifest_sha256"] == UPLOAD_MANIFEST_SHA256 and not upload["ds00_files_present"],
        "active_version_exact": active_versions == [VERSION_ID],
        "deployment_identity_intact": d1.get("deployment", {}).get("deployment_id") == DEPLOYMENT_ID,
        "metadata_unchanged_by_replay": same_bytes(before_metadata, after_metadata),
        "deployments_unchanged_by_replay": same_bytes(before_deployments, after_deployments),
        "origin_all_asset_files_exact": origin_all.get("checked_files") == 300 and origin_all.get("pass_count") == 300 and origin_all.get("fail_count") == 0 and origin_all.get("failure_count_including_index") == 0,
        "index_redirect_exact": origin_all.get("index_redirect", {}).get("exact") is True and origin_all["index_redirect"].get("status") == 302 and origin_all["index_redirect"].get("location") == "/deck.html",
        "control_files_not_public": origin_all.get("controls_checked") == {"_headers": 404, "_redirects": 404},
        "origin_representative_surface_exact": all(all(item.values()) for item in origin_checks.values()),
        "public_exact_assets_match_origin": all(all(item.values()) for item in public_exact.values()),
        "public_html_matches_after_edge_normalization": all(all(item[key] for key in ("status", "normalized_matches_origin")) for item in public_html.values()),
        "public_robots_matches_after_edge_normalization": all(public_robots.values()),
        "public_manifest_matches_frozen": public_exact["manifest"]["matches_origin"],
        "browser_public_replay_pass": browser.get("terminal") == "DS_D2_PUBLIC_REPLAY_PASS" and browser.get("failures") == [] and browser.get("errors") == [],
        "browser_navigation_and_research_surface": browser.get("navigation", {}).get("root", {}).get("status") == 200 and browser.get("navigation", {}).get("research", {}).get("status") == 200 and browser.get("navigation", {}).get("research_input_count") == 1 and browser.get("navigation", {}).get("research_investigate_button_count") == 1,
        "browser_no_ds_runtime_marker": not browser.get("navigation", {}).get("root_contains_ds_runtime_marker") and not browser.get("navigation", {}).get("research_contains_ds_runtime_marker"),
        "browser_privacy_safety_pass": browser.get("privacy_safety", {}).get("external_request_count") == 0 and not browser.get("privacy_safety", {}).get("unexpected_external_post") and not browser.get("privacy_safety", {}).get("forbidden_marker_request"),
        "browser_isolation_pass": browser.get("isolation", {}).get("cross_context_leakage") is False,
        "all_ds00_paths_404_empty": all(item.get("status") == 404 and item.get("body_bytes") == 0 for item in browser.get("public_ds_paths", {}).values()) and len(browser.get("public_ds_paths", {})) == 14,
        "ds_x0_private_runtime_claim_not_overstated": True,
        "human_usability_not_claimed": d1.get("human_usability") == "NOT_CLAIMED",
    }
    terminal = "DS_D2_PUBLIC_REPLAY_PASS" if all(checks.values()) else "DS_D2_PUBLIC_REPLAY_REPAIR_REQUIRED"
    result = {
        "schema": "forge.ds-d2.public-replay.verdict.v1",
        "unit": "DS-D2",
        "terminal": terminal,
        "candidate": CANDIDATE,
        "production": {
            "worker": WORKER,
            "custom_domain": CUSTOM_DOMAIN,
            "origin": ORIGIN,
            "version_id": VERSION_ID,
            "deployment_id": DEPLOYMENT_ID,
            "traffic_percent": 100,
        },
        "release": {
            "choice": "B",
            "public_file_count": PUBLIC_FILE_COUNT,
            "artifact_sha256": ARTIFACT_SHA256,
            "upload_manifest_sha256": UPLOAD_MANIFEST_SHA256,
            "ds00_public": False,
        },
        "checks": checks,
        "origin_representative": origin_checks,
        "public_exact_assets": public_exact,
        "public_html_normalized": public_html,
        "public_robots_normalized": public_robots,
        "ds_x0_scope": "NOT_APPLICABLE_AT_PUBLIC_BOUNDARY_DS00_EXCLUDED",
        "human_usability": "NOT_CLAIMED",
        "raw_evidence_root": str(evidence),
        "blocking_reasons": [name for name, passed in checks.items() if not passed],
        "limitations": [
            "DS-X0 private runtime task executions are not claimed through the public boundary because DS-00 is deliberately excluded; public safety, isolation, navigation, and non-exposure checks were run instead.",
            "Cloudflare edge transformations were normalized only where already documented: challenge injection, hidden challenge link, font replacement, and managed robots content.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"unit": "DS-D2", "terminal": terminal, "blocking_reasons": result["blocking_reasons"]}, sort_keys=True))
    return 0 if terminal == "DS_D2_PUBLIC_REPLAY_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
