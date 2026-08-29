#!/usr/bin/python3
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

bootstrap_line = sys.stdin.readline()
try:
    bootstrap = json.loads(bootstrap_line)
except json.JSONDecodeError as exc:
    raise SystemExit(f"invalid broker bootstrap: {exc}")
if not isinstance(bootstrap, dict) or set(bootstrap) != {"upstream_secret"}:
    raise SystemExit("invalid broker bootstrap schema")
secret = bootstrap.get("upstream_secret")
if not isinstance(secret, str) or not secret:
    raise SystemExit("missing fixture upstream secret")

base = Path(__file__).resolve().parent
proxy_env = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "FORGE_W4_FAKE_UPSTREAM_HOST": os.environ.get("FORGE_W4_FAKE_UPSTREAM_HOST", "fake-upstream"),
    "FORGE_W4_FAKE_UPSTREAM_PORT": os.environ.get("FORGE_W4_FAKE_UPSTREAM_PORT", "8090"),
}
gate_env = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PYTHONPATH": "/opt/forge",
    "FORGE_W4_CLIENT_TOKEN": os.environ["FORGE_W4_CLIENT_TOKEN"],
}
proxy = subprocess.Popen(
    ["/usr/local/bin/python3", str(base / "fake_credential_proxy.py")],
    stdin=subprocess.PIPE,
    stdout=sys.stdout,
    stderr=sys.stderr,
    env=proxy_env,
    text=True,
    start_new_session=True,
)
assert proxy.stdin is not None
proxy.stdin.write(secret + "\n")
proxy.stdin.flush()
proxy.stdin.close()
secret = ""
bootstrap = {}
bootstrap_line = ""

gate = subprocess.Popen(
    [
        "/usr/local/bin/python3",
        "-m",
        "forge_core.w4_gate",
        "--host",
        "0.0.0.0",
        "--port",
        "8080",
        "--upstream-port",
        "9090",
        "--max-requests",
        os.environ.get("FORGE_W4_MAX_REQUESTS", "8"),
        "--max-request-bytes",
        os.environ.get("FORGE_W4_MAX_REQUEST_BYTES", str(2 * 1024 * 1024)),
        "--max-response-bytes",
        os.environ.get("FORGE_W4_MAX_RESPONSE_BYTES", str(8 * 1024 * 1024)),
        "--max-total-bytes",
        os.environ.get("FORGE_W4_MAX_TOTAL_BYTES", str(16 * 1024 * 1024)),
        "--ttl-seconds",
        os.environ.get("FORGE_W4_TTL_SECONDS", "300"),
    ],
    stdin=subprocess.DEVNULL,
    stdout=sys.stdout,
    stderr=sys.stderr,
    env=gate_env,
    start_new_session=True,
)

children = [proxy, gate]


def terminate(*_args):
    for child in children:
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and any(child.poll() is None for child in children):
        time.sleep(0.05)
    for child in children:
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    raise SystemExit(0)


signal.signal(signal.SIGTERM, terminate)
signal.signal(signal.SIGINT, terminate)
print(json.dumps({"event": "broker_supervisor_started"}, separators=(",", ":")), flush=True)
while True:
    for child in children:
        code = child.poll()
        if code is not None:
            for other in children:
                if other is not child and other.poll() is None:
                    try:
                        os.killpg(other.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            raise SystemExit(code or 1)
    time.sleep(0.1)
