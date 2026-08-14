from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tests.w4_support import W4Topology, _run


class ForgeW4RoutingTests(unittest.TestCase):
    def test_b21_dual_homed_broker_does_not_route_provider_packets_to_egress_ip(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-route-") as tmp, W4Topology(Path(tmp)) as topology:
            upstream_network = topology.upstream_inspect()["NetworkSettings"]["Networks"][topology.egress_network]
            target_ip = upstream_network["IPAddress"]
            self.assertTrue(target_ip)
            broker = topology.broker_inspect()
            self.assertFalse(broker["HostConfig"]["Privileged"])
            self.assertIn("ALL", broker["HostConfig"].get("CapDrop") or [])
            code = (
                "import socket,sys; "
                f"target=({target_ip!r},8090); "
                "s=socket.socket(); s.settimeout(2); "
                "\ntry:\n s.connect(target)\nexcept OSError:\n sys.exit(0)\nelse:\n sys.exit(1)\n"
            )
            result = _run(
                [
                    topology.docker,
                    "run",
                    "--rm",
                    "--network",
                    topology.private_network,
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "--pids-limit",
                    "16",
                    "--memory",
                    "64m",
                    "--cpus",
                    "0.25",
                    "--entrypoint",
                    "/usr/local/bin/python3",
                    topology.provider_image,
                    "-c",
                    code,
                ],
                timeout=8,
            )
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr, target_ip))


if __name__ == "__main__":
    unittest.main()
