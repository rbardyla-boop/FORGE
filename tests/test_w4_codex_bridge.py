from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.f5_support import git
from tests.w4_codex_support import W4CodexTopology
from tests.w4_support import _run


class ForgeW4CodexBridgeTests(unittest.TestCase):
    def test_b28_b29_codex_shaped_fixture_uses_generated_config_and_streams_through_broker(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-codex-") as tmp, W4CodexTopology(Path(tmp)) as topology:
            result = topology.run_codex("good")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            self.assertEqual(sum(event.get("type") == "turn.completed" for event in events), 1)
            self.assertIn("gate_forward", topology.broker_logs())
            self.assertIn('"streaming":true', topology.upstream_logs())
            self.assertEqual(topology.codex_config_report["provider_id"], "forge_broker")
            self.assertFalse(topology.codex_config_report["auth_json_present"])
            self.assertIn("safe_divide", (topology.workspace / "calc.py").read_text())

    def test_b30_b31_b32_codex_shaped_workspace_still_ends_at_w1_proposal_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-codex-") as tmp, W4CodexTopology(Path(tmp)) as topology:
            result = topology.run_codex("good")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            proposal, changed, patch_file = topology.derive_and_submit()
            self.assertEqual(changed, ["calc.py"])
            self.assertIn(b"safe_divide", patch_file.read_bytes())
            self.assertEqual(proposal["proposal_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(proposal["completion_authority"], "none")
            self.assertEqual(proposal["candidate_authority"], "none")
            self.assertFalse((topology.root / ".forge/runs/U-0001/attempt-0001").exists())
            self.assertFalse((topology.root / ".forge/final/U-0001").exists())

    def test_b35_malformed_fake_upstream_stream_fails_closed_before_workspace_edit(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-codex-") as tmp, W4CodexTopology(Path(tmp)) as topology:
            before = (topology.workspace / "calc.py").read_bytes()
            result = topology.run_codex("malformed")
            self.assertNotEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn("turn.failed", result.stdout)
            self.assertEqual((topology.workspace / "calc.py").read_bytes(), before)
            self.assertFalse((topology.output / "TRACE.json").exists())

    def test_b36_upstream_non_2xx_fails_closed_before_workspace_edit(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-codex-") as tmp, W4CodexTopology(Path(tmp)) as topology:
            before = (topology.workspace / "calc.py").read_bytes()
            result = topology.run_codex("non_2xx")
            self.assertNotEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn("HTTP 429", result.stdout)
            self.assertEqual((topology.workspace / "calc.py").read_bytes(), before)

    def test_b37_upstream_timeout_fails_closed_without_workspace_edit(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-codex-") as tmp, W4CodexTopology(Path(tmp)) as topology:
            before = (topology.workspace / "calc.py").read_bytes()
            result = topology.run_codex("timeout", timeout=10)
            self.assertNotEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn("turn.failed", result.stdout)
            self.assertEqual((topology.workspace / "calc.py").read_bytes(), before)

    def test_b38_provider_timeout_is_killed_and_container_removed(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-codex-") as tmp, W4CodexTopology(Path(tmp)) as topology:
            result = topology.run_codex("provider_hang", timeout=0.5)
            self.assertEqual(result.returncode, 124, (result.stdout, result.stderr))
            self.assertIn("FORGE_W4_PROVIDER_TIMEOUT", result.stderr)
            self.assertNotEqual(_run([topology.docker, "inspect", topology.provider_name]).returncode, 0)

    def test_b39_operator_tracked_state_and_worktree_registry_remain_unchanged(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-codex-") as tmp, W4CodexTopology(Path(tmp)) as topology:
            status_before = git(topology.root, "status", "--porcelain=v1", "--untracked-files=no").stdout
            worktrees_before = git(topology.root, "worktree", "list", "--porcelain").stdout
            calc_before = (topology.root / "calc.py").read_bytes()
            result = topology.run_codex("good")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertEqual(git(topology.root, "status", "--porcelain=v1", "--untracked-files=no").stdout, status_before)
            self.assertEqual(git(topology.root, "worktree", "list", "--porcelain").stdout, worktrees_before)
            self.assertEqual((topology.root / "calc.py").read_bytes(), calc_before)

    def test_b40_fixture_gate_contains_no_real_openai_request_or_account_key(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-codex-") as tmp, W4CodexTopology(Path(tmp)) as topology:
            result = topology.run_codex("good")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            provider = json.dumps(topology.provider_inspect(), sort_keys=True)
            broker = json.dumps(topology.broker_inspect(), sort_keys=True)
            logs = topology.broker_logs() + topology.upstream_logs() + result.stdout + result.stderr
            self.assertNotIn("api.openai.com", provider)
            self.assertNotIn("api.openai.com", broker)
            self.assertNotIn("OPENAI_API_KEY", provider)
            self.assertNotIn("OPENAI_API_KEY", broker)
            self.assertNotIn(topology.upstream_secret, logs)
            self.assertIn("fake_upstream_ready", topology.upstream_logs())


if __name__ == "__main__":
    unittest.main()
