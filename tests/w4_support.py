from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid
from typing import Any

from forge_core.containment import (
    _derive_patch,
    _host_identity,
    _output_trace,
    _prepare_workspace,
    _reclaim_provider_tree,
    _validate_workspace,
)
from forge_core.proposal import _load_request, submit_proposal
from tests.w2_support import setup_request

BROKER_IMAGE_ENV = "FORGE_W4_BROKER_IMAGE_ID"
PROVIDER_IMAGE_ENV = "FORGE_W4_PROVIDER_IMAGE_ID"
UPSTREAM_IMAGE_ENV = "FORGE_W4_UPSTREAM_IMAGE_ID"


def _docker() -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise AssertionError("docker required for W4 fixture tests")
    result = subprocess.run([docker, "info"], capture_output=True, check=False, timeout=15)
    if result.returncode != 0:
        raise AssertionError("docker daemon unavailable")
    return docker


def _image(name: str) -> str:
    value = os.environ.get(name, "")
    if not value.startswith("sha256:"):
        raise AssertionError(f"{name} must be an immutable local image ID")
    return value


def _run(argv: list[str], *, input_text: str | None = None, timeout: float = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def _inspect(docker: str, name: str) -> dict[str, Any]:
    result = _run([docker, "inspect", name])
    if result.returncode != 0:
        raise AssertionError((name, result.stdout, result.stderr))
    values = json.loads(result.stdout)
    return values[0]


class W4Topology:
    def __init__(
        self,
        base: Path,
        *,
        max_requests: int = 8,
        max_request_bytes: int = 2 * 1024 * 1024,
        max_response_bytes: int = 8 * 1024 * 1024,
        max_total_bytes: int = 16 * 1024 * 1024,
        ttl_seconds: int = 300,
    ) -> None:
        self.base = base
        self.docker = _docker()
        self.broker_image = _image(BROKER_IMAGE_ENV)
        self.provider_image = _image(PROVIDER_IMAGE_ENV)
        self.upstream_image = _image(UPSTREAM_IMAGE_ENV)
        self.suffix = uuid.uuid4().hex[:12]
        self.private_network = f"forge-w4-private-{self.suffix}"
        self.egress_network = f"forge-w4-egress-{self.suffix}"
        self.broker_name = f"forge-w4-broker-{self.suffix}"
        self.upstream_name = f"forge-w4-upstream-{self.suffix}"
        self.provider_name = f"forge-w4-provider-{self.suffix}"
        self.client_token = secrets.token_urlsafe(32)
        self.upstream_secret = "UPSTREAM_SECRET_SENTINEL_" + secrets.token_urlsafe(24)
        self.max_requests = max_requests
        self.max_request_bytes = max_request_bytes
        self.max_response_bytes = max_response_bytes
        self.max_total_bytes = max_total_bytes
        self.ttl_seconds = ttl_seconds
        self.root = setup_request(base)
        request_dir, request = _load_request(self.root, "U-0001")
        self.request = request
        self.parent = Path(tempfile.mkdtemp(prefix="forge-w4-fixture-"))
        self.workspace, self.request_path, self.output, self.snapshot_digest = _prepare_workspace(
            self.root,
            request["baseline_commit"],
            (request_dir / "REQUEST.json").read_bytes(),
            self.parent,
        )
        self.broker_attach: subprocess.Popen[str] | None = None
        self.provider_result: subprocess.CompletedProcess[str] | None = None
        self._started = False

    def start(self) -> None:
        uid, gid = _host_identity()
        for network, internal in ((self.private_network, True), (self.egress_network, False)):
            argv = [self.docker, "network", "create"]
            if internal:
                argv.append("--internal")
            argv.append(network)
            result = _run(argv)
            if result.returncode != 0:
                raise AssertionError((argv, result.stdout, result.stderr))

        upstream = _run(
            [
                self.docker,
                "run",
                "-d",
                "--name",
                self.upstream_name,
                "--network",
                self.egress_network,
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "32",
                "--memory",
                "128m",
                "--cpus",
                "0.5",
                "--user",
                "65534:65534",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=16m",
                "--env",
                f"FORGE_W4_EXPECTED_UPSTREAM_SECRET={self.upstream_secret}",
                self.upstream_image,
            ]
        )
        if upstream.returncode != 0:
            raise AssertionError((upstream.stdout, upstream.stderr))

        created = _run(
            [
                self.docker,
                "create",
                "-i",
                "--name",
                self.broker_name,
                "--network",
                self.private_network,
                "--network-alias",
                "forge-broker",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "64",
                "--memory",
                "256m",
                "--cpus",
                "1.0",
                "--user",
                f"{uid}:{gid}",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=32m",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
                "--env",
                f"FORGE_W4_CLIENT_TOKEN={self.client_token}",
                "--env",
                f"FORGE_W4_MAX_REQUESTS={self.max_requests}",
                "--env",
                f"FORGE_W4_MAX_REQUEST_BYTES={self.max_request_bytes}",
                "--env",
                f"FORGE_W4_MAX_RESPONSE_BYTES={self.max_response_bytes}",
                "--env",
                f"FORGE_W4_MAX_TOTAL_BYTES={self.max_total_bytes}",
                "--env",
                f"FORGE_W4_TTL_SECONDS={self.ttl_seconds}",
                self.broker_image,
            ]
        )
        if created.returncode != 0:
            raise AssertionError((created.stdout, created.stderr))
        connected = _run([self.docker, "network", "connect", self.egress_network, self.broker_name])
        if connected.returncode != 0:
            raise AssertionError((connected.stdout, connected.stderr))

        self.broker_attach = subprocess.Popen(
            [self.docker, "start", "-a", "-i", self.broker_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        assert self.broker_attach.stdin is not None
        self.broker_attach.stdin.write(json.dumps({"upstream_secret": self.upstream_secret}) + "\n")
        self.broker_attach.stdin.flush()
        self.broker_attach.stdin.close()
        self._wait_ready(self.upstream_name, "fake_upstream_ready")
        self._wait_ready(self.broker_name, "gate_ready")
        self._wait_ready(self.broker_name, "fake_proxy_ready")
        self._started = True

    def _wait_ready(self, container: str, marker: str, timeout: float = 15.0) -> None:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            logs = _run([self.docker, "logs", container], timeout=5)
            last = logs.stdout + logs.stderr
            if marker in last:
                return
            state = _inspect(self.docker, container)["State"]
            if not state.get("Running", False):
                raise AssertionError(f"{container} exited before {marker}: {last}")
            time.sleep(0.1)
        raise AssertionError(f"timeout waiting for {marker}: {last}")

    def run_provider(self, mode: str) -> subprocess.CompletedProcess[str]:
        if not self._started:
            self.start()
        uid, gid = _host_identity()
        created = _run(
            [
                self.docker,
                "create",
                "--name",
                self.provider_name,
                "--network",
                self.private_network,
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "64",
                "--memory",
                "256m",
                "--cpus",
                "1.0",
                "--user",
                f"{uid}:{gid}",
                "--mount",
                f"type=bind,src={self.workspace},dst=/workspace",
                "--mount",
                f"type=bind,src={self.request_path},dst=/input/REQUEST.json,readonly",
                "--mount",
                f"type=bind,src={self.output},dst=/output",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=32m",
                "--env",
                "FORGE_WORKSPACE=/workspace",
                "--env",
                "FORGE_OUTPUT=/output",
                "--env",
                "FORGE_REQUEST=/input/REQUEST.json",
                "--env",
                "FORGE_W4_BROKER_URL=http://forge-broker:8080",
                "--env",
                f"FORGE_W4_CLIENT_TOKEN={self.client_token}",
                self.provider_image,
                mode,
            ]
        )
        if created.returncode != 0:
            raise AssertionError((created.stdout, created.stderr))
        self.provider_result = _run([self.docker, "start", "-a", self.provider_name], timeout=30)
        _reclaim_provider_tree(self.workspace)
        _reclaim_provider_tree(self.output)
        return self.provider_result

    def broker_inspect(self) -> dict[str, Any]:
        return _inspect(self.docker, self.broker_name)

    def provider_inspect(self) -> dict[str, Any]:
        return _inspect(self.docker, self.provider_name)

    def upstream_inspect(self) -> dict[str, Any]:
        return _inspect(self.docker, self.upstream_name)

    def broker_logs(self) -> str:
        result = _run([self.docker, "logs", self.broker_name])
        return result.stdout + result.stderr

    def upstream_logs(self) -> str:
        result = _run([self.docker, "logs", self.upstream_name])
        return result.stdout + result.stderr

    def derive_and_submit(self):
        _validate_workspace(self.workspace)
        trace = _output_trace(self.output)
        with tempfile.TemporaryDirectory(prefix="forge-w4-collector-") as collector_tmp:
            patch_bytes, changed_paths = _derive_patch(
                self.root,
                self.request["baseline_commit"],
                self.workspace,
                Path(collector_tmp),
            )
        patch_file = self.base / "W4_DERIVED.patch"
        patch_file.write_bytes(patch_bytes)
        proposal = submit_proposal(self.root, "U-0001", patch_file, trace)
        return proposal, changed_paths, patch_file

    def cleanup(self) -> None:
        for name in (self.provider_name, self.broker_name, self.upstream_name):
            _run([self.docker, "rm", "-f", name], timeout=10)
        if self.broker_attach is not None:
            try:
                self.broker_attach.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.broker_attach.kill()
        for network in (self.private_network, self.egress_network):
            _run([self.docker, "network", "rm", network], timeout=10)
        try:
            _reclaim_provider_tree(self.parent)
        except Exception:
            pass
        shutil.rmtree(self.parent, ignore_errors=True)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()
        return False
