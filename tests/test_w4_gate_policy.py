from __future__ import annotations

from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
import unittest

from forge_core.w4_gate import GateHandler, GateState


class CaptureUpstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    captured: list[dict] = []

    def log_message(self, format, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        CaptureUpstream.captured.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "content_type": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        try:
            request = json.loads(body.decode("utf-8"))
        except Exception:
            request = {}
        size = int(request.get("response_bytes", 32)) if isinstance(request, dict) else 32
        payload = b"x" * size
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.close_connection = True


class GateFixture:
    def __init__(
        self,
        *,
        max_requests=8,
        max_request_bytes=1024,
        max_response_bytes=1024,
        max_total_bytes=4096,
        ttl_seconds=60,
    ):
        CaptureUpstream.captured = []
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), CaptureUpstream)
        self.upstream_thread = threading.Thread(target=self.upstream.serve_forever, daemon=True)
        self.upstream_thread.start()
        state = GateState(
            client_token="t" * 43,
            upstream_host="127.0.0.1",
            upstream_port=self.upstream.server_port,
            max_requests=max_requests,
            max_request_bytes=max_request_bytes,
            max_response_bytes=max_response_bytes,
            max_total_bytes=max_total_bytes,
            ttl_seconds=ttl_seconds,
        )
        self.gate = ThreadingHTTPServer(("127.0.0.1", 0), GateHandler)
        self.gate.gate_state = state  # type: ignore[attr-defined]
        self.gate_thread = threading.Thread(target=self.gate.serve_forever, daemon=True)
        self.gate_thread.start()
        self.state = state
        self.token = "t" * 43

    def request(self, method="POST", path="/v1/responses", body=b"{}", headers=None):
        selected = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
        if headers:
            selected.update(headers)
        connection = HTTPConnection("127.0.0.1", self.gate.server_port, timeout=5)
        connection.request(method, path, body=body, headers=selected)
        response = connection.getresponse()
        payload = response.read()
        status = response.status
        connection.close()
        return status, payload

    def close(self):
        self.gate.shutdown(); self.gate.server_close()
        self.upstream.shutdown(); self.upstream.server_close()
        self.gate_thread.join(timeout=2); self.upstream_thread.join(timeout=2)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False


class ForgeW4GatePolicyTests(unittest.TestCase):
    def test_b06_alternate_auth_headers_cannot_bypass_missing_capability(self):
        with GateFixture() as fixture:
            status, _ = fixture.request(
                headers={
                    "Authorization": "",
                    "X-Authorization": f"Bearer {fixture.token}",
                    "Proxy-Authorization": f"Bearer {fixture.token}",
                }
            )
            self.assertEqual(status, 401)
            self.assertEqual(CaptureUpstream.captured, [])

    def test_b07_only_post_responses_path_is_forwarded(self):
        with GateFixture() as fixture:
            for method in ("GET", "PUT", "DELETE", "PATCH"):
                with self.subTest(method=method):
                    status, _ = fixture.request(method=method)
                    self.assertEqual(status, 405)
            status, _ = fixture.request(path="/v1/other")
            self.assertEqual(status, 404)
            self.assertEqual(CaptureUpstream.captured, [])

    def test_b08_query_strings_are_rejected(self):
        with GateFixture() as fixture:
            status, _ = fixture.request(path="/v1/responses?x=1")
            self.assertEqual(status, 404)
            self.assertEqual(CaptureUpstream.captured, [])

    def test_b09_non_json_content_type_is_rejected(self):
        with GateFixture() as fixture:
            status, _ = fixture.request(headers={"Content-Type": "text/plain"})
            self.assertEqual(status, 415)
            self.assertEqual(CaptureUpstream.captured, [])

    def test_b10_absolute_form_proxy_target_is_not_forwarded(self):
        with GateFixture() as fixture:
            status, _ = fixture.request(path="http://attacker.invalid/v1/responses")
            self.assertIn(status, {400, 404})
            self.assertEqual(CaptureUpstream.captured, [])

    def test_b11_provider_authorization_is_consumed_and_not_forwarded(self):
        with GateFixture() as fixture:
            status, _ = fixture.request(body=b'{"model":"fixture"}')
            self.assertEqual(status, 200)
            self.assertEqual(len(CaptureUpstream.captured), 1)
            self.assertIsNone(CaptureUpstream.captured[0]["authorization"])

    def test_b12_request_body_limit_is_enforced_before_forward(self):
        with GateFixture(max_request_bytes=8) as fixture:
            status, _ = fixture.request(body=b'{"123456789":1}')
            self.assertEqual(status, 413)
            self.assertEqual(CaptureUpstream.captured, [])

    def test_b13_request_count_budget_is_enforced(self):
        with GateFixture(max_requests=1) as fixture:
            first, _ = fixture.request()
            second, _ = fixture.request()
            self.assertEqual(first, 200)
            self.assertEqual(second, 429)
            self.assertEqual(len(CaptureUpstream.captured), 1)

    def test_b14_expired_broker_rejects_without_forward(self):
        with GateFixture() as fixture:
            fixture.state.expires_at = time.monotonic() - 1
            status, _ = fixture.request()
            self.assertEqual(status, 429)
            self.assertEqual(CaptureUpstream.captured, [])

    def test_b15_response_byte_budget_is_enforced(self):
        with GateFixture(max_response_bytes=16, max_total_bytes=4096) as fixture:
            status, body = fixture.request(body=b'{"response_bytes":64}')
            self.assertEqual(status, 502)
            self.assertIn(b"response_size", body)


if __name__ == "__main__":
    unittest.main()
