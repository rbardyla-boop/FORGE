from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import threading
import time
import unittest

from forge_core.w4_gate import GateHandler, GateState


REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX_FIXTURE = REPO_ROOT / "tests" / "w4_fixture" / "codex_provider" / "fake_codex_brokered.py"


class ControlledUpstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    entered = 0
    lock = threading.Lock()
    release = threading.Event()
    delay = False

    def log_message(self, *_args):
        return

    @classmethod
    def reset(cls, *, delay: bool = False) -> None:
        with cls.lock:
            cls.entered = 0
        cls.release = threading.Event()
        cls.delay = delay

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        with type(self).lock:
            type(self).entered += 1
        if type(self).delay:
            type(self).release.wait(2)
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass
        self.close_connection = True


class ObservingHTTPServer(ThreadingHTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler_errors = []

    def handle_error(self, request, client_address):
        self.handler_errors.append((type(request).__name__, client_address))


class OfflineGateFixture:
    def __init__(self, *, max_requests: int = 8, delay: bool = False):
        ControlledUpstream.reset(delay=delay)
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), ControlledUpstream)
        self.upstream_thread = threading.Thread(target=self.upstream.serve_forever, daemon=True)
        self.upstream_thread.start()
        self.token = "t" * 43
        state = GateState(
            client_token=self.token,
            upstream_host="127.0.0.1",
            upstream_port=self.upstream.server_port,
            max_requests=max_requests,
            max_request_bytes=1024,
            max_response_bytes=1024,
            max_total_bytes=4096,
            ttl_seconds=60,
        )
        self.gate = ObservingHTTPServer(("127.0.0.1", 0), GateHandler)
        self.gate.gate_state = state  # type: ignore[attr-defined]
        self.gate_thread = threading.Thread(target=self.gate.serve_forever, daemon=True)
        self.gate_thread.start()
        self.state = state

    def request(self, *, timeout: float = 5.0) -> tuple[int, bytes]:
        connection = HTTPConnection("127.0.0.1", self.gate.server_port, timeout=timeout)
        try:
            connection.request(
                "POST",
                "/v1/responses",
                body=b"{}",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def close(self) -> None:
        self.gate.shutdown()
        self.gate.server_close()
        self.upstream.shutdown()
        self.upstream.server_close()
        self.gate_thread.join(timeout=2)
        self.upstream_thread.join(timeout=2)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False


def _fixture_parser():
    """Load the exact fixture parser without starting its network server."""
    spec = importlib.util.spec_from_file_location("forge_w4_fixture_codex", CODEX_FIXTURE)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load the frozen Codex fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_sse


class ForgeW4OfflineResilienceTests(unittest.TestCase):
    def test_r01_concurrent_request_budget_is_a_hard_cap(self):
        with OfflineGateFixture(max_requests=4, delay=True) as fixture:
            with ThreadPoolExecutor(max_workers=24) as pool:
                futures = [pool.submit(fixture.request) for _ in range(24)]
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and ControlledUpstream.entered < 4:
                    time.sleep(0.01)
                self.assertEqual(ControlledUpstream.entered, 4)
                self.assertEqual(fixture.state.request_count, 4)
                ControlledUpstream.release.set()
                results = [future.result() for future in futures]

            self.assertEqual(sum(status == 200 for status, _ in results), 4)
            self.assertEqual(sum(status == 429 for status, _ in results), 20)
            self.assertEqual(ControlledUpstream.entered, 4)
            self.assertEqual(fixture.state.request_count, 4)

    def test_r02_downstream_timeout_does_not_take_down_local_gate(self):
        with OfflineGateFixture(max_requests=2, delay=True) as fixture:
            with self.assertRaises(TimeoutError):
                fixture.request(timeout=0.05)
            self.assertEqual(ControlledUpstream.entered, 1)
            ControlledUpstream.release.set()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and fixture.state.total_bytes == 2:
                time.sleep(0.01)

            status, body = fixture.request()
            self.assertEqual(status, 200)
            self.assertEqual(body, b"ok")
            self.assertEqual(fixture.state.request_count, 2)
            self.assertTrue(fixture.gate.handler_errors)

    def test_r03_responses_parser_rejects_malformed_and_mismatched_events(self):
        parse_sse = _fixture_parser()
        valid = b'event: response.created\ndata: {"type":"response.created"}\n\n'
        self.assertEqual(parse_sse(valid)[0]["type"], "response.created")
        with self.assertRaises(json.JSONDecodeError):
            parse_sse(b"event: response.created\ndata: {not-json}\n\n")
        with self.assertRaises(ValueError):
            parse_sse(b'event: response.created\ndata: {"type":"response.completed"}\n\n')
        with self.assertRaises(ValueError):
            parse_sse(b"event: response.created\ndata: \xff\n\n")

    def test_r04_partial_responses_stream_has_no_completion_event(self):
        parse_sse = _fixture_parser()
        body = (
            b'event: response.created\ndata: {"type":"response.created"}\n\n'
            b'event: response.output_text.delta\n'
            b'data: {"type":"response.output_text.delta","delta":"partial"}\n\n'
        )
        events = parse_sse(body)
        self.assertEqual([event["type"] for event in events], [
            "response.created",
            "response.output_text.delta",
        ])
        self.assertEqual([event for event in events if event.get("type") == "response.completed"], [])


if __name__ == "__main__":
    unittest.main()
