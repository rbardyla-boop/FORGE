# FORGE-W4 Live Preflight Evidence

**Unit:** FORGE-W4 live preflight
**Status:** `BLOCKED_EXTERNAL`
**Reason:** `LIVE_API_KEY_UNAVAILABLE`
**Real OpenAI request:** none
**Billable requests:** `0`

This document records the no-secret binary preflight only. It does not promote
W4 to `PASS` and does not authorize W5, production use, merge, or deployment.

## Frozen official artifacts

The release metadata was resolved from the official
`openai/codex` GitHub release API on 2026-08-13.

| Component | Release | Asset | Immutable asset ID | Bytes | Release SHA-256 | Observed SHA-256 |
|---|---|---|---:|---:|---|---|
| Codex CLI | `rust-v0.147.0` | `codex-x86_64-unknown-linux-musl.tar.gz` | `504450426` | `98,970,270` | `sha256:0246e2e773834e07f0fb5249ed6ebad12e4591e608f8c7bb97dd6a9690544c36` | `sha256:0246e2e773834e07f0fb5249ed6ebad12e4591e608f8c7bb97dd6a9690544c36` |
| Responses proxy | `rust-v0.147.0` | `codex-responses-api-proxy-x86_64-unknown-linux-musl.tar.gz` | `504450442` | `4,550,399` | `sha256:1596d30264ec74837d5b805e06bf80abf7de01f17bf0bc79a63c9be45019c99c` | `sha256:1596d30264ec74837d5b805e06bf80abf7de01f17bf0bc79a63c9be45019c99c` |

Trusted source identity for both artifacts:

```text
https://api.github.com/repos/openai/codex/releases/tags/rust-v0.147.0
https://github.com/openai/codex/releases/download/rust-v0.147.0/<asset>
release_id = 366471016
published_at = 2026-08-07T01:41:49Z
```

The resolver workflow now freezes the tag, release ID, asset IDs, sizes,
release digests, and download URLs; downloads both assets; verifies the
independent hashes before extraction; and refuses to continue on a mismatch.

## No-secret binary preflight

Passed checks:

- official Codex executable identity: `codex-cli 0.147.0`;
- official Responses proxy executable identity and help surface;
- documented default upstream remains `https://api.openai.com/v1/responses`;
- live proxy argv builder contains no `--upstream-url`, dump, shutdown, or
  endpoint/TLS override;
- official proxy with empty stdin fails closed with `API key must be provided
  via stdin`;
- a disposable `CODEX_HOME` was used and contained no `auth.json`;
- the real official Codex binary reached the Forge gate in the non-billable
  fixture path;
- the gate forwarded exactly one request;
- the official proxy received its fixture-only sentinel through stdin and the
  fake upstream verified the injected bearer value;
- the Codex container environment contained the Forge capability only and no
  `OPENAI_API_KEY`, Codex API credential, GitHub token, or ChatGPT auth file;
- Codex exited `0` with a completed JSONL turn;
- no public OpenAI endpoint was used by the fixture path.

The official binary driver used Docker host networking only as a disposable
local adapter because this validation host's Docker bridge could not reach the
host gateway. This is not the W4 production topology and does not replace the
existing W4 dual-network isolation gates, which remain required predecessor
evidence.

The fixture SSE stream was repaired after the official CLI reported
`OutputTextDelta without active item`; the stream now opens an output item and
content part before emitting its text delta. The repair is recorded as a
permanent regression in `tests/test_w4_live_preflight.py`.

## Terminal replay evidence

On the repaired working tree:

- artifact resolution and no-secret binary checks: `PASS`;
- W4 policy/config/live-fixture checks: `22/22`;
- W4 Docker broker and Codex composition packet: `20/20`;
- complete W3 → W1 → Foundation → F6 → F1 predecessor replay: `265` tests,
  `OK`;
- compileall and `git diff --check`: `PASS`.

The replay used immutable local Docker image IDs for every fixture image. All
containers and validation processes were removed after the run.

## External boundary

No separately supplied OpenAI API key was available through the explicitly
supported trusted live input. Forge did not inspect, extract, transform, or
forward ChatGPT/Codex subscription credentials or `auth.json`.

Therefore the correct terminal state is:

```text
W4 = BLOCKED_EXTERNAL
reason = LIVE_API_KEY_UNAVAILABLE
LIVE CREDENTIAL PRESENT = NO
LIVE REQUEST MADE = NO
BILLABLE REQUESTS = 0
```

The next live action, if separately authorized and supplied with an API key,
is one maximally bounded pilot task followed by the complete predecessor
replay. No billable request was attempted during this preflight.
