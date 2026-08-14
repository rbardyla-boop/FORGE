# W4 Offline Resilience Evidence

**Unit:** W4 offline resilience probe
**State:** `PASS_WITH_DISCLOSED_LIMITS`
**Authentication:** none
**Real OpenAI requests:** `0`
**Billable requests:** `0`

## Claim under test

The credentialless local path should preserve the already-frozen W4 safety
boundaries when a local caller is concurrent, times out, or receives an
adversarial Responses stream. This is an offline engineering claim only. It
does not validate OpenAI service availability, API authentication, billing, or
the official binary's live behavior.

## Falsification gates

| Gate | Required result |
| --- | --- |
| Concurrent request budget | No more than the frozen request budget reaches the upstream. |
| Downstream timeout | A timed-out caller does not make the local gate unavailable to the next bounded caller; any disconnect diagnostic is disclosed. |
| Stream grammar | Malformed, mismatched, and non-UTF-8 events are rejected by the Codex-shaped consumer. |
| Partial stream | A stream without `response.completed` cannot be treated as complete. |
| External boundary | No API key, network request, or paid service may be introduced. |

## Evidence

The replayable local suite is:

```text
python3 -m unittest tests.test_w4_offline_resilience -v
```

It exercises a real in-process `ThreadingHTTPServer` gate and upstream. The
stream parser is loaded from the exact frozen Codex-shaped fixture source
without starting its server. The suite does not use Docker, DNS, Internet,
OpenAI credentials, or repository credentials.

The concurrency check starts 24 callers against a four-request budget while the
upstream holds accepted requests. Exactly four requests are forwarded; the
remaining 20 receive `429 request_budget`. The timeout check disconnects one
caller while the upstream is delayed, releases the delayed response, then
proves a second bounded request still completes. The parser checks malformed
JSON, event/type mismatch, non-UTF-8 data, and a partial stream with no
completion event.

The timeout check also records the frozen gate's current limitation: after the
caller disconnects, the gate's attempted response write raises
`BrokenPipeError`, and its fallback error write is not graceful. The gate
process remains available and the next request succeeds, but cancellation is
not propagated upstream and the disconnect is noisy. This is disclosed evidence
for a future authorized W4 source-repair unit, not evidence of graceful
cancellation.

Existing predecessor evidence separately covers Codex process timeout and
process-group cleanup (`tests.test_w3_jsonl`, A17), plus W4 malformed upstream,
non-2xx, upstream timeout, provider timeout, and workspace-preservation cases
when the required immutable Docker fixture image IDs are available.

## Limits and authority

This unit does not repair or alter frozen W4 production code, the frozen
preflight, the W4 live runner, or the official binary. It does not establish
that a real request can cross the OpenAI service boundary; W4-LIVE-001 remains
`BLOCKED_EXTERNAL / DEFERRED` because no API key is available.

The Docker-backed W4 integration suite is environment-dependent on immutable
local image IDs. If those IDs are absent, the suite is `NOT_RUN`, not a live
failure and not evidence for the external claim.

## Verdict

The offline resilience claim is supported with the disclosed limits above.
The project may continue with local deterministic work at zero API cost. The
external-evidence debt remains isolated:

```text
W4 PREFLIGHT          PASS / FROZEN
W4 OFFLINE RESILIENCE PASS_WITH_DISCLOSED_LIMITS
W4 LIVE-001           BLOCKED_EXTERNAL / DEFERRED
REAL OPENAI REQUESTS  0
BILLABLE REQUESTS     0
```
