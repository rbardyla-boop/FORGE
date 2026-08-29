from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.w4_support import W4Topology, _run


class ForgeW4BrokerBridgeTests(unittest.TestCase):
    def test_b00_broker_has_no_repository_or_workspace_mount(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            inspect = topology.broker_inspect()
            self.assertEqual(inspect.get("Mounts"), [])
            rendered = json.dumps(inspect, sort_keys=True)
            self.assertNotIn(str(topology.root), rendered)
            self.assertNotIn(str(topology.workspace), rendered)

    def test_b01_b02_upstream_secret_is_absent_from_provider_and_broker_docker_inspect(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            result = topology.run_provider("secret_probe")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            provider = json.dumps(topology.provider_inspect(), sort_keys=True)
            broker = json.dumps(topology.broker_inspect(), sort_keys=True)
            self.assertNotIn(topology.upstream_secret, provider)
            self.assertNotIn(topology.upstream_secret, broker)
            self.assertNotIn("OPENAI_API_KEY", provider)
            self.assertNotIn("CODEX_API_KEY", provider)
            self.assertIn(topology.client_token, provider)

    def test_b03_missing_capability_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            result = topology.run_provider("missing_capability")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn("invalid_forge_capability", topology.broker_logs())

    def test_b04_wrong_capability_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            result = topology.run_provider("wrong_capability")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn("invalid_forge_capability", topology.broker_logs())

    def test_b05_correct_ephemeral_capability_reaches_fake_upstream_through_broker(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            result = topology.run_provider("good")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn("gate_forward", topology.broker_logs())
            self.assertIn('"credential_verified":true', topology.upstream_logs())

    def test_b07_b09_only_responses_json_shape_is_accepted(self):
        with self.subTest("non-json"):
            with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
                result = topology.run_provider("non_json")
                self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
                self.assertIn("content_type_not_allowed", topology.broker_logs())
        with self.subTest("query"):
            with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
                result = topology.run_provider("query")
                self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
                logs = topology.broker_logs()
                self.assertTrue("path_not_allowed" in logs or "query_not_allowed" in logs)

    def test_b18_provider_has_no_direct_public_internet_but_broker_remains_reachable(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            result = topology.run_provider("direct_internet")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn("gate_forward", topology.broker_logs())

    def test_b19_b20_provider_reaches_broker_but_not_fake_upstream_directly(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            result = topology.run_provider("direct_upstream")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn("gate_forward", topology.broker_logs())
            provider_networks = topology.provider_inspect()["NetworkSettings"]["Networks"]
            broker_networks = topology.broker_inspect()["NetworkSettings"]["Networks"]
            upstream_networks = topology.upstream_inspect()["NetworkSettings"]["Networks"]
            self.assertEqual(set(provider_networks), {topology.private_network})
            self.assertEqual(set(upstream_networks), {topology.egress_network})
            self.assertEqual(set(broker_networks), {topology.private_network, topology.egress_network})

    def test_b22_b23_broker_and_provider_evidence_do_not_contain_upstream_secret(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            result = topology.run_provider("good")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            combined = topology.broker_logs() + topology.upstream_logs() + result.stdout + result.stderr
            self.assertNotIn(topology.upstream_secret, combined)
            self.assertNotIn(topology.upstream_secret, (topology.output / "TRACE.json").read_text())

    def test_b30_b31_b32_workspace_bytes_feed_w2_collector_and_end_at_w1_proposal_only(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp, W4Topology(Path(tmp)) as topology:
            result = topology.run_provider("good")
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            proposal, changed, patch_file = topology.derive_and_submit()
            self.assertEqual(changed, ["calc.py"])
            self.assertIn(b"safe_divide", patch_file.read_bytes())
            self.assertEqual(proposal["proposal_state"], "PROPOSAL_ACCEPTED")
            self.assertEqual(proposal["completion_authority"], "none")
            self.assertEqual(proposal["candidate_authority"], "none")
            self.assertFalse((topology.root / ".forge/runs/U-0001/attempt-0001").exists())
            self.assertFalse((topology.root / ".forge/final/U-0001").exists())

    def test_b34_repeated_topology_gets_fresh_capability_and_names(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as first_tmp, tempfile.TemporaryDirectory(prefix="forge-w4-") as second_tmp:
            first = W4Topology(Path(first_tmp))
            second = W4Topology(Path(second_tmp))
            try:
                self.assertNotEqual(first.client_token, second.client_token)
                self.assertNotEqual(first.private_network, second.private_network)
                self.assertNotEqual(first.egress_network, second.egress_network)
                self.assertNotEqual(first.broker_name, second.broker_name)
            finally:
                first.cleanup(); second.cleanup()

    def test_b33_cleanup_removes_broker_provider_upstream_and_networks(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-") as tmp:
            topology = W4Topology(Path(tmp))
            topology.start()
            names = (topology.provider_name, topology.broker_name, topology.upstream_name)
            networks = (topology.private_network, topology.egress_network)
            docker = topology.docker
            topology.cleanup()
            for name in names:
                self.assertNotEqual(_run([docker, "inspect", name]).returncode, 0)
            for network in networks:
                self.assertNotEqual(_run([docker, "network", "inspect", network]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
