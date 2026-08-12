from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from forge_core.containment import execute_provider
from tests.w2_support import setup_request


def image_id() -> str:
    value = os.environ.get("FORGE_W3_IMAGE_ID", "")
    if not value.startswith("sha256:"):
        raise AssertionError("FORGE_W3_IMAGE_ID must be the exact local W3 fixture image ID")
    return value


def execute(root: Path, mode: str):
    return execute_provider(
        root,
        "U-0001",
        image_id(),
        [mode],
        adapter_id=f"w3-contained:{mode}",
        timeout_seconds=30,
    )


class ForgeW3ContainedCompositionTests(unittest.TestCase):
    def test_codex_shaped_good_run_is_inside_w2_and_ends_at_proposal_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-contained-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "good")
            self.assertEqual(code, 0, report)
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(report["completion_authority"], "none")
            self.assertEqual(report["candidate_authority"], "none")
            profile = report["containment_profile"]
            self.assertIn("--network", profile)
            self.assertEqual(profile[profile.index("--network") + 1], "none")
            events = [json.loads(line) for line in report["stdout"].splitlines() if line.strip()]
            self.assertEqual(sum(event.get("type") == "turn.completed" for event in events), 1)
            self.assertFalse((root / ".forge/runs/U-0001/attempt-0001").exists())

    def test_codex_authority_claims_remain_inert_inside_w2(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-contained-") as tmp:
            base = Path(tmp); root = setup_request(base)
            report, code = execute(root, "authority_claims")
            self.assertEqual(code, 0, report)
            self.assertIn("PASS DONE CANDIDATE_VERIFIED MERGE DEPLOY", report["stdout"])
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(report["completion_authority"], "none")
            self.assertEqual(report["candidate_authority"], "none")

    def test_codex_shaped_provider_receives_no_host_credentials_inside_w2(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-contained-") as tmp:
            base = Path(tmp); root = setup_request(base)
            prior = {key: os.environ.get(key) for key in ("CODEX_API_KEY", "OPENAI_API_KEY", "GITHUB_TOKEN")}
            try:
                os.environ["CODEX_API_KEY"] = "HOST_CODEX_SECRET"
                os.environ["OPENAI_API_KEY"] = "HOST_OPENAI_SECRET"
                os.environ["GITHUB_TOKEN"] = "HOST_GITHUB_SECRET"
                report, code = execute(root, "secret_probe")
            finally:
                for key, value in prior.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            self.assertEqual(code, 0, report)
            self.assertEqual(report["execution_state"], "PROPOSAL_ACCEPTED")
            rendered = json.dumps(report, sort_keys=True)
            self.assertNotIn("HOST_CODEX_SECRET", rendered)
            self.assertNotIn("HOST_OPENAI_SECRET", rendered)
            self.assertNotIn("HOST_GITHUB_SECRET", rendered)


if __name__ == "__main__":
    unittest.main()
