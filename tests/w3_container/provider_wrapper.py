#!/usr/bin/python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "good"
    request_path = Path(os.environ["FORGE_REQUEST"])
    request_bytes = request_path.read_bytes()
    codex_home = Path("/tmp/codex-home")
    home = Path("/tmp/home")
    codex_home.mkdir(mode=0o700, exist_ok=True)
    home.mkdir(mode=0o700, exist_ok=True)

    env = {
        "HOME": str(home),
        "CODEX_HOME": str(codex_home),
        "TMPDIR": "/tmp",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TERM": "dumb",
        "NO_COLOR": "1",
        "FORGE_W3_FIXTURE_MODE": mode,
    }
    argv = [
        "/usr/local/bin/fake-codex",
        "exec",
        "--ephemeral",
        "--json",
        "--sandbox",
        "workspace-write",
        "--ask-for-approval",
        "never",
        "--ignore-user-config",
        "--ignore-rules",
        "--color",
        "never",
        "--cd",
        "/workspace",
        "-",
    ]
    process = subprocess.run(
        argv,
        input=request_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        shell=False,
        check=False,
        timeout=20,
    )
    sys.stdout.buffer.write(process.stdout)
    sys.stdout.buffer.flush()
    sys.stderr.buffer.write(process.stderr)
    sys.stderr.buffer.flush()
    if process.returncode != 0:
        return process.returncode

    events = []
    try:
        for raw_line in process.stdout.splitlines():
            if raw_line.strip():
                value = json.loads(raw_line.decode("utf-8"))
                if not isinstance(value, dict):
                    return 72
                events.append(value)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 73
    types = [event.get("type") for event in events]
    if types.count("turn.completed") != 1 or "turn.failed" in types or "error" in types:
        return 74

    trace = {
        "schema": "forge.builder-trace.v0.1",
        "adapter": "w3-contained-codex-fixture",
        "provider_run_id": f"w3-contained-{mode}",
        "events": [
            {"seq": 1, "kind": "PLAN", "summary": "invoked frozen Codex-shaped argv inside W2"},
            {"seq": 2, "kind": "EDIT", "summary": "Codex-shaped workspace mutation returned to W2 collector"},
        ],
    }
    Path(os.environ["FORGE_OUTPUT"]).joinpath("TRACE.json").write_text(
        json.dumps(trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
