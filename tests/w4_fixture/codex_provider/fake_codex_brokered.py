#!/usr/bin/python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import tomllib
import urllib.error
import urllib.request


def emit(value: dict) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")), flush=True)


def fail(message: str, code: int) -> int:
    emit({"type": "turn.failed", "error": {"message": message}})
    return code


def parse_sse(body: bytes) -> list[dict]:
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("non-utf8 stream") from exc
    events: list[dict] = []
    current_event = None
    for raw in text.splitlines():
        if raw.startswith("event: "):
            current_event = raw[7:]
        elif raw.startswith("data: "):
            value = json.loads(raw[6:])
            if not isinstance(value, dict):
                raise ValueError("non-object SSE data")
            if current_event is not None and value.get("type") != current_event:
                raise ValueError("SSE event/type mismatch")
            events.append(value)
    return events


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "good"
    codex_home = Path(os.environ["CODEX_HOME"])
    config_path = codex_home / "config.toml"
    if not config_path.is_file() or (codex_home / "auth.json").exists():
        return fail("invalid disposable CODEX_HOME", 70)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if set(config) != {"model", "model_provider", "approval_policy", "sandbox_mode", "model_providers"}:
        return fail("unexpected top-level config", 71)
    provider_id = config["model_provider"]
    providers = config["model_providers"]
    if provider_id != "forge_broker" or set(providers) != {"forge_broker"}:
        return fail("unexpected provider selection", 72)
    provider = providers["forge_broker"]
    expected_keys = {
        "name",
        "base_url",
        "env_key",
        "wire_api",
        "requires_openai_auth",
        "request_max_retries",
        "stream_max_retries",
    }
    if set(provider) != expected_keys:
        return fail("unexpected provider keys", 73)
    if provider["base_url"] != "http://forge-broker:8080/v1":
        return fail("unexpected broker URL", 74)
    if provider["wire_api"] != "responses" or provider["requires_openai_auth"] is not False:
        return fail("unexpected provider auth/wire policy", 75)
    env_key = provider["env_key"]
    if env_key != "FORGE_W4_CLIENT_TOKEN":
        return fail("unexpected capability environment name", 76)
    token = os.environ.get(env_key, "")
    if not token:
        return fail("missing Forge client capability", 77)
    for forbidden in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        if forbidden in os.environ:
            return fail("upstream credential leaked to Codex-shaped provider", 78)
    if mode == "provider_hang":
        time.sleep(999)
        return 79

    request_body = json.dumps(
        {
            "model": config["model"],
            "input": "Implement the frozen safe_divide fixture task.",
            "stream": True,
            "fixture_mode": mode,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        provider["base_url"] + "/responses",
        data=request_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    emit({"type": "thread.started", "thread_id": "w4-brokered-fixture"})
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            body = response.read(8 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        return fail(f"broker returned HTTP {exc.code}", 80)
    except Exception as exc:
        return fail(f"broker request failed: {type(exc).__name__}", 81)
    if status != 200 or not content_type.startswith("text/event-stream"):
        return fail("unexpected Responses stream envelope", 82)
    if len(body) > 8 * 1024 * 1024:
        return fail("stream exceeded fixture bound", 83)
    try:
        events = parse_sse(body)
    except (ValueError, json.JSONDecodeError):
        return fail("malformed Responses stream", 84)
    completed = [event for event in events if event.get("type") == "response.completed"]
    deltas = [event.get("delta") for event in events if event.get("type") == "response.output_text.delta"]
    if len(completed) != 1 or "fixture-upstream-ok" not in deltas:
        return fail("Responses stream did not complete correctly", 85)

    workspace = Path(os.environ["FORGE_WORKSPACE"])
    (workspace / "calc.py").write_text(
        "def divide(a, b):\n"
        "    return a / b\n\n\n"
        "def safe_divide(a, b):\n"
        "    if b == 0:\n"
        "        return None\n"
        "    return a / b\n",
        encoding="utf-8",
    )
    emit({"type": "item.completed", "item": {"type": "file_change", "changes": [{"path": "calc.py", "kind": "update"}]}})
    emit({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}})
    trace = {
        "schema": "forge.builder-trace.v0.1",
        "adapter": "w4-codex-brokered-fixture",
        "provider_run_id": f"w4-codex-{mode}",
        "events": [
            {"seq": 1, "kind": "PLAN", "summary": "loaded only Forge-generated disposable Codex provider config"},
            {"seq": 2, "kind": "EDIT", "summary": "completed fake Responses stream through authenticated W4 broker"},
        ],
    }
    Path(os.environ["FORGE_OUTPUT"]).joinpath("TRACE.json").write_text(
        json.dumps(trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
