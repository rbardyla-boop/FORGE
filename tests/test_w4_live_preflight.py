from __future__ import annotations

import json
import unittest

from tests.w4_fixture.upstream.fake_upstream import stream_body


def parse_sse(body: bytes) -> list[dict]:
    events: list[dict] = []
    for line in body.decode("utf-8").splitlines():
        if line.startswith("data: "):
            value = json.loads(line[6:])
            if not isinstance(value, dict):
                raise AssertionError("fixture SSE data must be an object")
            events.append(value)
    return events


class ForgeW4LivePreflightTests(unittest.TestCase):
    def test_fixture_stream_opens_output_item_before_text_delta(self):
        events = parse_sse(
            stream_body(
                {
                    "id": "response-under-test",
                    "object": "response",
                    "status": "completed",
                    "output_text": "fixture-upstream-ok",
                    "model": "gpt-5",
                }
            )
        )
        types = [event["type"] for event in events]
        self.assertLess(types.index("response.output_item.added"), types.index("response.output_text.delta"))
        delta = next(event for event in events if event["type"] == "response.output_text.delta")
        self.assertEqual(delta["item_id"], "msg_w4_fixture")
        self.assertEqual(delta["output_index"], 0)
        self.assertEqual(delta["content_index"], 0)
        self.assertEqual(types[-1], "response.completed")


if __name__ == "__main__":
    unittest.main()
