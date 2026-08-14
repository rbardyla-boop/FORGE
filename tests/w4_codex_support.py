from __future__ import annotations

import os
from pathlib import Path
import subprocess

from forge_core.containment import _host_identity, _reclaim_provider_tree
from forge_core.w4_codex_config import create_codex_home
from tests.w4_support import W4Topology, _image, _run

CODEX_PROVIDER_IMAGE_ENV = "FORGE_W4_CODEX_PROVIDER_IMAGE_ID"


class W4CodexTopology(W4Topology):
    def __init__(self, base: Path, **kwargs):
        super().__init__(base, **kwargs)
        self.codex_provider_image = _image(CODEX_PROVIDER_IMAGE_ENV)
        self.codex_config_report = create_codex_home(self.parent, model="fixture-model")
        self.codex_home = Path(self.codex_config_report["codex_home"])

    def run_codex(self, mode: str, *, timeout: float = 15.0):
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
                "--mount",
                f"type=bind,src={self.codex_home},dst=/codex-home,readonly",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=32m",
                "--env",
                "FORGE_WORKSPACE=/workspace",
                "--env",
                "FORGE_OUTPUT=/output",
                "--env",
                "FORGE_REQUEST=/input/REQUEST.json",
                "--env",
                "CODEX_HOME=/codex-home",
                "--env",
                f"FORGE_W4_CLIENT_TOKEN={self.client_token}",
                self.codex_provider_image,
                mode,
            ],
            timeout=10,
        )
        if created.returncode != 0:
            raise AssertionError((created.stdout, created.stderr))
        start_argv = [self.docker, "start", "-a", self.provider_name]
        try:
            result = _run(start_argv, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            _run([self.docker, "rm", "-f", self.provider_name], timeout=10)
            stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            result = subprocess.CompletedProcess(
                start_argv,
                124,
                stdout,
                stderr + "\nFORGE_W4_PROVIDER_TIMEOUT\n",
            )
        _reclaim_provider_tree(self.workspace)
        _reclaim_provider_tree(self.output)
        return result
