#!/usr/bin/python3
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys
import urllib.error
import urllib.request


def trace(summary: str) -> None:
    payload = {
        "schema": "forge.builder-trace.v0.1",
        "adapter": "w4-brokered-fixture",
        "provider_run_id": f"w4-{MODE}",
        "events": [
            {"seq": 1, "kind": "PLAN", "summary": "used only the W4 broker capability"},
            {"seq": 2, "kind": "EDIT", "summary": summary},
        ],
    }
    (OUTPUT / "TRACE.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def good_edit() -> None:
    (WORKSPACE / "calc.py").write_text(
        "def divide(a, b):\n"
        "    return a / b\n\n\n"
        "def safe_divide(a, b):\n"
        "    if b == 0:\n"
        "        return None\n"
        "    return a / b\n",
        encoding="utf-8",
    )


def broker_request(mode: str = "good", *, token: str | None = None, content_type: str = "application/json", path: str = "/v1/responses"):
    body = json.dumps({"model": "fixture-model", "input": "fixture", "fixture_mode": mode}).encode("utf-8")
    headers = {"Content-Type": content_type}
    selected = TOKEN if token is None else token
    if selected:
        headers["Authorization"] = f"Bearer {selected}"
    request = urllib.request.Request(BROKER_URL + path, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def direct_http(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            response.read(16)
        return True
    except Exception:
        return False


MODE = sys.argv[1] if len(sys.argv) > 1 else "good"
WORKSPACE = Path(os.environ["FORGE_WORKSPACE"])
OUTPUT = Path(os.environ["FORGE_OUTPUT"])
BROKER_URL = os.environ["FORGE_W4_BROKER_URL"].rstrip("/")
TOKEN = os.environ.get("FORGE_W4_CLIENT_TOKEN", "")

UPSTREAM_SECRET_NAMES = {
    "OPENAI_API_KEY",
    "FORGE_W4_UPSTREAM_SECRET",
    "FORGE_W4_EXPECTED_UPSTREAM_SECRET",
    "CODEX_API_KEY",
}

if MODE == "secret_probe":
    if UPSTREAM_SECRET_NAMES.intersection(os.environ):
        raise SystemExit(81)
    rendered_env = json.dumps(dict(os.environ), sort_keys=True)
    if "UPSTREAM_SECRET_SENTINEL" in rendered_env:
        raise SystemExit(82)
    status, body = broker_request()
    if status != 200 or b"fixture-upstream-ok" not in body:
        raise SystemExit(83)
    good_edit(); trace("upstream account secret absent from provider")
    raise SystemExit(0)

if MODE == "direct_internet":
    if direct_http("http://1.1.1.1/"):
        raise SystemExit(84)
    status, body = broker_request()
    if status != 200:
        raise SystemExit(85)
    good_edit(); trace("direct Internet unavailable while broker remained reachable")
    raise SystemExit(0)

if MODE == "direct_upstream":
    try:
        socket.getaddrinfo("fake-upstream", 8090)
    except socket.gaierror:
        pass
    else:
        if direct_http("http://fake-upstream:8090/v1/responses"):
            raise SystemExit(86)
    status, body = broker_request()
    if status != 200:
        raise SystemExit(87)
    good_edit(); trace("fake upstream unreachable directly from provider")
    raise SystemExit(0)

if MODE == "missing_capability":
    status, _ = broker_request(token="")
    if status != 401:
        raise SystemExit(88)
    raise SystemExit(0)

if MODE == "wrong_capability":
    status, _ = broker_request(token="wrong-capability-value-that-is-not-authorized")
    if status != 401:
        raise SystemExit(89)
    raise SystemExit(0)

if MODE == "non_json":
    status, _ = broker_request(content_type="text/plain")
    if status != 415:
        raise SystemExit(90)
    raise SystemExit(0)

if MODE == "query":
    status, _ = broker_request(path="/v1/responses?x=1")
    if status not in {404, 400}:
        raise SystemExit(91)
    raise SystemExit(0)

if MODE == "non_2xx":
    status, _ = broker_request(mode="non_2xx")
    if status != 429:
        raise SystemExit(92)
    raise SystemExit(0)

if MODE == "malformed_upstream":
    status, body = broker_request(mode="malformed")
    if status != 200 or body != b"{not-json":
        raise SystemExit(93)
    raise SystemExit(0)

if MODE == "good":
    status, body = broker_request()
    if status != 200 or b"fixture-upstream-ok" not in body:
        raise SystemExit(94)
    good_edit(); trace("brokered fake Responses request produced scoped implementation")
    raise SystemExit(0)

print(f"unknown provider mode: {MODE}", file=sys.stderr)
raise SystemExit(64)
