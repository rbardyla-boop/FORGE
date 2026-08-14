from __future__ import annotations

import argparse
import hmac
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import time
from typing import Any
from urllib.parse import urlsplit

ALLOWED_PATH = "/v1/responses"
DEFAULT_MAX_REQUESTS = 8
DEFAULT_MAX_REQUEST_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 16 * 1024 * 1024
DEFAULT_TTL_SECONDS = 300


class GatePolicyError(RuntimeError):
    pass


class GateState:
    def __init__(
        self,
        *,
        client_token: str,
        upstream_host: str,
        upstream_port: int,
        max_requests: int,
        max_request_bytes: int,
        max_response_bytes: int,
        max_total_bytes: int,
        ttl_seconds: int,
    ) -> None:
        if len(client_token) < 43:
            raise GatePolicyError("client capability token is too short")
        if upstream_host not in {"127.0.0.1", "localhost"}:
            raise GatePolicyError("front gate upstream must be loopback credential proxy")
        if not (1 <= upstream_port <= 65535):
            raise GatePolicyError("invalid loopback proxy port")
        for value, label in (
            (max_requests, "max_requests"),
            (max_request_bytes, "max_request_bytes"),
            (max_response_bytes, "max_response_bytes"),
            (max_total_bytes, "max_total_bytes"),
            (ttl_seconds, "ttl_seconds"),
        ):
            if value <= 0:
                raise GatePolicyError(f"{label} must be positive")
        self.client_token = client_token.encode("utf-8")
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.max_requests = max_requests
        self.max_request_bytes = max_request_bytes
        self.max_response_bytes = max_response_bytes
        self.max_total_bytes = max_total_bytes
        self.expires_at = time.monotonic() + ttl_seconds
        self.request_count = 0
        self.total_bytes = 0

    def authorize(self, header: str | None) -> bool:
        if header is None or not header.startswith("Bearer "):
            return False
        presented = header[7:].encode("utf-8", errors="strict")
        return hmac.compare_digest(presented, self.client_token)

    def reserve(self, request_bytes: int) -> str | None:
        if time.monotonic() > self.expires_at:
            return "expired"
        if self.request_count >= self.max_requests:
            return "request_budget"
        if request_bytes > self.max_request_bytes:
            return "request_size"
        if self.total_bytes + request_bytes > self.max_total_bytes:
            return "total_budget"
        self.request_count += 1
        self.total_bytes += request_bytes
        return None

    def account_response(self, response_bytes: int) -> str | None:
        if response_bytes > self.max_response_bytes:
            return "response_size"
        if self.total_bytes + response_bytes > self.max_total_bytes:
            return "total_budget"
        self.total_bytes += response_bytes
        return None


def _json_log(event: str, **fields: Any) -> None:
    safe = {"event": event, **fields}
    print(json.dumps(safe, sort_keys=True, separators=(",", ":")), flush=True)


class GateHandler(BaseHTTPRequestHandler):
    server_version = "ForgeW4Gate/0.1"
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> GateState:
        return self.server.gate_state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _reply(self, status: int, body: bytes, *, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _policy_error(self, status: int, code: str) -> None:
        _json_log("gate_reject", code=code, status=status)
        self._reply(status, json.dumps({"error": code}).encode("utf-8"))

    def do_CONNECT(self) -> None:
        self._policy_error(405, "method_not_allowed")

    def do_GET(self) -> None:
        self._policy_error(405, "method_not_allowed")

    def do_PUT(self) -> None:
        self._policy_error(405, "method_not_allowed")

    def do_DELETE(self) -> None:
        self._policy_error(405, "method_not_allowed")

    def do_PATCH(self) -> None:
        self._policy_error(405, "method_not_allowed")

    def do_POST(self) -> None:
        if self.path != ALLOWED_PATH:
            self._policy_error(404, "path_not_allowed")
            return
        if "?" in self.path:
            self._policy_error(404, "query_not_allowed")
            return
        if self.headers.get("Upgrade") or self.headers.get("Connection", "").lower() == "upgrade":
            self._policy_error(400, "upgrade_not_allowed")
            return
        host = self.headers.get("Host", "")
        if "/" in host or "://" in self.path:
            self._policy_error(400, "absolute_proxy_target_not_allowed")
            return
        if not self.state.authorize(self.headers.get("Authorization")):
            self._policy_error(401, "invalid_forge_capability")
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._policy_error(415, "content_type_not_allowed")
            return
        transfer_encoding = self.headers.get("Transfer-Encoding", "")
        if transfer_encoding:
            self._policy_error(400, "chunked_request_not_allowed")
            return
        try:
            content_length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            self._policy_error(400, "invalid_content_length")
            return
        if content_length < 0:
            self._policy_error(411, "content_length_required")
            return
        reserved = self.state.reserve(content_length)
        if reserved:
            status = 429 if reserved in {"expired", "request_budget", "total_budget"} else 413
            self._policy_error(status, reserved)
            return
        body = self.rfile.read(content_length)
        if len(body) != content_length:
            self._policy_error(400, "truncated_request")
            return
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._policy_error(400, "invalid_json")
            return
        if not isinstance(parsed, dict):
            self._policy_error(400, "json_object_required")
            return

        forwarded_headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Connection": "close",
        }
        connection = HTTPConnection(self.state.upstream_host, self.state.upstream_port, timeout=60)
        try:
            connection.request("POST", ALLOWED_PATH, body=body, headers=forwarded_headers)
            response = connection.getresponse()
            response_body = response.read(self.state.max_response_bytes + 1)
            over_budget = self.state.account_response(len(response_body))
            if over_budget:
                self._policy_error(502, over_budget)
                return
            content_type_out = response.getheader("Content-Type") or "application/octet-stream"
            _json_log(
                "gate_forward",
                status=response.status,
                request_count=self.state.request_count,
                request_bytes=len(body),
                response_bytes=len(response_body),
            )
            self._reply(response.status, response_body, content_type=content_type_out)
        except OSError as exc:
            _json_log("gate_upstream_error", error=type(exc).__name__)
            self._policy_error(502, "credential_proxy_unavailable")
        finally:
            connection.close()


def serve(
    *,
    host: str,
    port: int,
    client_token: str,
    upstream_host: str = "127.0.0.1",
    upstream_port: int = 9090,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> None:
    state = GateState(
        client_token=client_token,
        upstream_host=upstream_host,
        upstream_port=upstream_port,
        max_requests=max_requests,
        max_request_bytes=max_request_bytes,
        max_response_bytes=max_response_bytes,
        max_total_bytes=max_total_bytes,
        ttl_seconds=ttl_seconds,
    )
    server = ThreadingHTTPServer((host, port), GateHandler)
    server.gate_state = state  # type: ignore[attr-defined]
    _json_log("gate_ready", host=host, port=server.server_port)
    server.serve_forever(poll_interval=0.1)


def main() -> int:
    parser = argparse.ArgumentParser(prog="forge-w4-gate")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--upstream-port", type=int, default=9090)
    parser.add_argument("--max-requests", type=int, default=DEFAULT_MAX_REQUESTS)
    parser.add_argument("--max-request-bytes", type=int, default=DEFAULT_MAX_REQUEST_BYTES)
    parser.add_argument("--max-response-bytes", type=int, default=DEFAULT_MAX_RESPONSE_BYTES)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    args = parser.parse_args()
    token = os.environ.get("FORGE_W4_CLIENT_TOKEN", "")
    if not token:
        raise SystemExit("FORGE_W4_CLIENT_TOKEN is required")
    serve(
        host=args.host,
        port=args.port,
        client_token=token,
        upstream_port=args.upstream_port,
        max_requests=args.max_requests,
        max_request_bytes=args.max_request_bytes,
        max_response_bytes=args.max_response_bytes,
        max_total_bytes=args.max_total_bytes,
        ttl_seconds=args.ttl_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
