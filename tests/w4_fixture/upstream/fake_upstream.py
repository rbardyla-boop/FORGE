#!/usr/bin/python3
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import time
from typing import Any

EXPECTED_SECRET = os.environ.get("FORGE_W4_EXPECTED_UPSTREAM_SECRET", "")
if not EXPECTED_SECRET:
    raise SystemExit("FORGE_W4_EXPECTED_UPSTREAM_SECRET required")


def log(event: str, **fields: Any) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True, separators=(",", ":")), flush=True)


def sse_event(event_type: str, data: dict[str, Any]) -> bytes:
    return (
        f"event: {event_type}\n"
        f"data: {json.dumps(data, sort_keys=True, separators=(',', ':'))}\n\n"
    ).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ForgeW4FakeUpstream/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def reply(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_POST(self) -> None:
        if self.path != "/v1/responses":
            self.reply(404, b'{"error":"bad_path"}')
            return
        if self.headers.get("Authorization") != f"Bearer {EXPECTED_SECRET}":
            log("upstream_reject", reason="bad_credential")
            self.reply(401, b'{"error":"bad_upstream_credential"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            self.reply(400, b'{"error":"bad_length"}')
            return
        if length < 0 or length > 4 * 1024 * 1024:
            self.reply(413, b'{"error":"bad_length"}')
            return
        body = self.rfile.read(length)
        try:
            request = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.reply(400, b'{"error":"bad_json"}')
            return
        mode = request.get("fixture_mode", "good") if isinstance(request, dict) else "good"
        streaming = bool(request.get("stream", False)) if isinstance(request, dict) else False
        log("upstream_request", mode=str(mode)[:64], bytes=len(body), credential_verified=True, streaming=streaming)
        if mode == "non_2xx":
            self.reply(429, b'{"error":"fixture_rate_limit"}')
            return
        if mode == "timeout":
            time.sleep(20)
            self.reply(200, b'{"id":"late"}')
            return
        if mode == "malformed":
            self.reply(200, b'{not-json')
            return
        if mode == "oversize_response":
            self.reply(200, b'{"blob":"' + (b"x" * (9 * 1024 * 1024)) + b'"}')
            return
        response = {
            "id": "resp_w4_fixture",
            "object": "response",
            "status": "completed",
            "output_text": "fixture-upstream-ok",
            "model": request.get("model", "fixture-model") if isinstance(request, dict) else "fixture-model",
        }
        if streaming:
            stream_body = b"".join(
                [
                    sse_event("response.created", {"type": "response.created", "response": {"id": response["id"], "status": "in_progress"}}),
                    sse_event("response.output_text.delta", {"type": "response.output_text.delta", "delta": "fixture-upstream-ok"}),
                    sse_event("response.completed", {"type": "response.completed", "response": response}),
                ]
            )
            self.reply(200, stream_body, "text/event-stream")
            return
        self.reply(200, json.dumps(response, sort_keys=True).encode("utf-8"))


server = ThreadingHTTPServer(("0.0.0.0", 8090), Handler)
log("fake_upstream_ready", port=8090)
server.serve_forever(poll_interval=0.1)
