#!/usr/bin/python3
from __future__ import annotations

from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import sys
from typing import Any

UPSTREAM_HOST = os.environ.get("FORGE_W4_FAKE_UPSTREAM_HOST", "fake-upstream")
UPSTREAM_PORT = int(os.environ.get("FORGE_W4_FAKE_UPSTREAM_PORT", "8090"))
SECRET = sys.stdin.readline().rstrip("\n")
if not SECRET:
    raise SystemExit("fixture upstream secret missing on stdin")


def log(event: str, **fields: Any) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True, separators=(",", ":")), flush=True)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ForgeW4FakeCredentialProxy/0.1"

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
            self.reply(403, b'{"error":"proxy_path_rejected"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            self.reply(400, b'{"error":"bad_length"}')
            return
        if length < 0 or length > 2 * 1024 * 1024:
            self.reply(413, b'{"error":"bad_length"}')
            return
        body = self.rfile.read(length)
        connection = HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=15)
        try:
            connection.request(
                "POST",
                "/v1/responses",
                body=body,
                headers={
                    "Authorization": f"Bearer {SECRET}",
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            response_body = response.read(16 * 1024 * 1024)
            content_type = response.getheader("Content-Type") or "application/json"
            log("fake_proxy_forward", status=response.status, request_bytes=len(body), response_bytes=len(response_body))
            self.reply(response.status, response_body, content_type)
        except OSError as exc:
            log("fake_proxy_error", error=type(exc).__name__)
            self.reply(502, b'{"error":"fake_upstream_unavailable"}')
        finally:
            connection.close()

    def do_GET(self) -> None:
        self.reply(403, b'{"error":"proxy_method_rejected"}')


server = ThreadingHTTPServer(("127.0.0.1", 9090), Handler)
log("fake_proxy_ready", port=9090)
server.serve_forever(poll_interval=0.1)
