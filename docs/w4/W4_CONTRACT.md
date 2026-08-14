# FORGE-W4 Contract — Real Codex Pilot / Credential-Network Bridge

**Unit:** FORGE-W4
**Layer:** Walls / fourth unit
**State:** FROZEN BEFORE IMPLEMENTATION
**Base:** canonical FORGE-W3 `PASS`
**Real OpenAI request:** forbidden until W4 bridge fixture gates pass
**Automatic Foundation handoff:** forbidden
**Merge/deploy authority:** forbidden

## Objective

Design, falsify, and then use the smallest credential/network bridge that allows **one real Codex CLI task** to reach OpenAI while preserving the Forge authority chain:

```text
real Codex provider
    ↓
W4 credential/network broker
    ↓
OpenAI Responses API

workspace/result side:
W1 frozen request
    ↓
W2-style disposable workspace containment
    ↓
real Codex mutations
    ↓
external workspace validation
    ↓
trusted patch derivation
    ↓
W1 PROPOSAL_ACCEPTED only
```

The first live task is successful only if it ends at W1 `PROPOSAL_ACCEPTED`. It may not invoke F4/F5 automatically and may not declare final completion.

## Official grounding frozen on 2026-08-12

Primary OpenAI sources consulted before freezing this contract:

- `openai/codex-action` README: https://github.com/openai/codex-action
- `openai/codex-action` security guidance: https://github.com/openai/codex-action/blob/main/docs/security.md
- official Codex Responses API proxy: https://github.com/openai/codex/blob/main/codex-rs/responses-api-proxy/README.md
- Codex CLI / non-interactive documentation under https://developers.openai.com/codex/

The current official material establishes these relevant facts:

1. OpenAI's Codex GitHub Action protects a provider API key by starting a Responses API proxy rather than handing the key directly to repository-controlled Codex execution.
2. OpenAI explicitly warns that API keys must be protected from repository-controlled code and recommends privilege reduction/isolation.
3. The official Responses API proxy accepts only Responses API traffic and injects the upstream bearer credential itself.
4. The official proxy documentation reads the real API key from stdin and hardens its in-memory handling.
5. The documented proxy/custom-provider route is an **API-key** route. W4 does not claim that a ChatGPT subscription login can safely or officially be forwarded through an arbitrary custom base URL.
6. A previously reported unauthenticated localhost proxy surface demonstrates why Forge must not rely on an unprotected local TCP endpoint as its only client-authority control.

Forge credits this broker/proxy architecture to OpenAI's Codex Action and Responses API proxy. W4 adds Forge-specific capability authentication, request budgets, topology isolation, evidence, and W1/W2 composition gates.

## Authentication modes

W4 supports exactly one live authentication mode initially:

```text
OPENAI_API_KEY_BROKER
```

The real OpenAI API key must be supplied separately at run time by the trusted orchestrator. It must never be committed to Git, stored in `.forge`, copied into a provider workspace, placed in provider JSONL/trace/evidence, or mounted into the Codex container.

### ChatGPT subscription authentication

W4 does **not** extract, copy, proxy, transform, or re-use the operator's ChatGPT/Codex subscription credentials or `auth.json`.

If the operator has only ChatGPT subscription authentication and no separately supplied API key for this pilot, the live sub-gate terminates:

```text
BLOCKED_EXTERNAL: LIVE_API_KEY_UNAVAILABLE
```

That is a legitimate non-PASS terminal state. Forge must not silently switch billing/auth modes or expose the subscription login to make the test run.

## W4 topology

W4 introduces two distinct execution principals on an ephemeral single-tenant Linux runner:

### 1. Trusted broker

The broker:

- has **no repository/workspace mount**;
- receives the real OpenAI API key only through a one-shot trusted secret input channel;
- holds the upstream credential only in broker process memory for the bounded run;
- receives a fresh 256-bit Forge client capability token generated for that run;
- connects upstream only to the exact configured OpenAI Responses API endpoint;
- accepts only the exact allowed Responses request path/method/content type;
- strips any provider-supplied upstream `Authorization` header;
- injects the real upstream bearer credential itself;
- enforces request-count, request-body, response-byte, wall-clock and total-byte budgets;
- records redacted metadata only;
- never records authorization values, cookies, secret input, full environment, or raw upstream credentials;
- has no Docker socket and no ability to mutate the operator repository;
- terminates at the end of one W4 run.

### 2. Untrusted Codex provider

The Codex execution side:

- receives **no OpenAI API key, ChatGPT token, auth.json, refresh token, or GitHub token**;
- receives only the fresh W4 client capability token needed to call the broker;
- receives only the disposable task workspace and generated W1/W3 task inputs;
- is attached only to a dedicated per-run **internal** Docker network;
- has no direct Internet route;
- can reach the broker's private service endpoint on that internal network;
- preserves the W2 filesystem/capability/resource restrictions unless W4 explicitly lists a required amendment;
- uses a fresh disposable `CODEX_HOME` generated by Forge;
- uses a Forge-generated custom Codex model-provider configuration that points only at the broker;
- cannot supply arbitrary model-provider configuration or arbitrary `-c` overrides.

The broker is dual-homed: one private internal network shared only with this provider and one trusted egress network used for the upstream OpenAI request. IP forwarding/routing between those networks is not an authorized capability; only the broker application may forward allowed HTTP requests.

## Client capability token

The W4 client token is **not** the OpenAI credential. It is an ephemeral capability scoped to one broker instance.

Rules:

- generated from a cryptographically secure source;
- at least 256 bits of entropy;
- never committed or persisted in Forge canonical state;
- supplied only to the provider and broker for that bounded run;
- compared in constant time;
- rejected if missing, malformed, or incorrect;
- expires when the broker exits;
- broker request budgets prevent a leaked per-run capability from becoming unlimited quota authority.

Provider code is assumed able to read its own W4 client token. That is acceptable because the token grants only the already-authorized bounded broker capability for the current run; it is not reusable OpenAI account authority.

## Broker request policy

The initial W4 broker permits only:

```text
POST /v1/responses
Content-Type: application/json
```

No other method/path/query is permitted.

The broker SHALL reject:

- missing/incorrect Forge client capability;
- incoming OpenAI/API credentials from the provider;
- non-JSON content type;
- query strings;
- CONNECT, WebSocket upgrade, arbitrary host, arbitrary URL, redirects, or proxy-style absolute request targets;
- oversized body;
- request count above the frozen task budget;
- response stream above the frozen byte budget;
- requests after run expiry;
- any attempt to change upstream hostname/path.

The upstream target is frozen to the exact OpenAI HTTPS Responses endpoint selected by the contract. TLS verification may not be disabled.

## W2 network amendment for W4 only

Canonical W2 remains `network none` and unchanged.

W4 creates a new **brokered-network profile** rather than editing W2's proven profile in place:

```text
linux-docker-brokered-v0.1
```

Differences from W2 `linux-docker-v0.1` are limited to:

- attach provider to a fresh internal Docker network;
- permit network access only to the W4 broker service reachable on that network;
- supply the ephemeral Forge client capability token and broker base URL;
- supply a fresh Forge-generated `CODEX_HOME` model-provider configuration for the broker.

All other W2 restrictions remain inherited: no operator repo mount, no `.forge`, read-only rootfs, dropped capabilities, no-new-privileges, no Docker socket/host devices, bounded PID/memory/CPU/time, disposable writable workspace, external workspace validation, trusted patch derivation, and zero completion authority.

W4 must prove the provider cannot reach public Internet addresses directly even though the broker can.

## Codex provider configuration amendment

W3 canonical `--ignore-user-config` remains correct for the credentialless fixture boundary.

For W4 live broker use, Codex must know the custom broker model provider. W4 therefore permits exactly one Forge-generated disposable configuration in `CODEX_HOME`.

The configuration is generated from trusted constants/runtime broker coordinates and is not supplied by repository content. It may define only:

- one Forge broker model provider;
- broker `base_url`;
- `wire_api = "responses"`;
- one environment-key name for the **ephemeral Forge client capability**, never the OpenAI key;
- an explicitly frozen model for the pilot.

Ambient operator config, project config, profiles, MCP servers, plugins, skills, arbitrary provider blocks, arbitrary `-c`, and auth files remain forbidden.

## Secret handling

Before the live pilot, W4 tests must prove all of the following with sentinel secrets:

- provider environment contains no real/upstream sentinel;
- provider filesystem contains no real/upstream sentinel;
- provider stdout/stderr/JSONL contains no real/upstream sentinel;
- W1 proposal/trace contains no real/upstream sentinel;
- broker logs/evidence contain no real/upstream sentinel;
- Docker inspect data for the provider contains no real/upstream sentinel;
- operator repository and Git history contain no real/upstream sentinel;
- broker receives secret through the frozen trusted input mechanism only;
- broker process cannot mount/read the disposable workspace;
- provider cannot access broker process filesystem/PID namespace/secret input channel.

Any real secret leak is a terminal security failure and requires immediate key revocation outside Forge before further live work.

## Fixture-before-live rule

No real OpenAI request may occur until W4's full bridge is proven against a deterministic fake upstream and malicious provider fixtures.

The fixture architecture must include:

- fake OpenAI Responses upstream on the broker egress side;
- real W4 broker policy in the middle;
- malicious provider client on the internal-only side;
- W3 Codex-shaped fixture running through the brokered profile;
- W2 trusted workspace validation/patch derivation and W1 proposal submission.

## Required W4 bridge attacks

At minimum:

```text
B00 broker has no workspace/repository mount
B01 provider has no upstream API secret
B02 broker secret never appears in provider Docker inspect/env
B03 missing client capability rejected
B04 incorrect client capability rejected
B05 correct ephemeral capability accepted
B06 capability comparison/request auth cannot be bypassed with alternate headers
B07 only POST /v1/responses accepted
B08 query strings rejected
B09 non-JSON content type rejected
B10 arbitrary host/absolute-form proxy request rejected
B11 provider Authorization header stripped/rejected
B12 request body limit enforced
B13 request-count budget enforced
B14 broker expiry enforced
B15 response-byte budget enforced
B16 broker upstream is exact HTTPS OpenAI target in live mode
B17 TLS verification cannot be disabled
B18 provider cannot reach public Internet directly
B19 provider can reach broker on private network
B20 broker can reach fake/live upstream through egress side
B21 broker does not route provider packets between networks
B22 broker logs/evidence redact secrets
B23 provider stdout/stderr/JSONL cannot exfiltrate upstream secret because it never receives it
B24 generated CODEX_HOME contains no operator auth.json
B25 generated provider config contains only allowed Forge broker provider
B26 repository/project config cannot alter provider/base URL
B27 arbitrary -c/provider override impossible
B28 Codex-shaped fixture reaches broker and receives fake Responses stream
B29 Codex-shaped fixture edits disposable workspace only
B30 W2 external validator/trusted collector remains patch authority
B31 successful fixture ends at W1 PROPOSAL_ACCEPTED only
B32 no F4/F5 artifact after bridge success
B33 broker/provider cleanup removes networks/containers/temp secret material
B34 repeated run gets a different client capability and fresh topology
B35 malformed fake upstream response fails closed
B36 upstream non-2xx fails closed
B37 upstream timeout fails closed
B38 provider timeout fails closed
B39 operator tracked state/worktree registry unchanged
B40 no real network request occurs during fixture terminal gate
```

Every serious bridge failure becomes a named permanent regression before live execution is authorized.

## Live pilot preconditions

The real pilot may start only after the fixture bridge and all W3/W2/W1/Foundation/F6-F1 predecessor gates pass on the exact candidate.

Additionally:

- trusted orchestrator confirms a separately supplied API key is available without revealing it to the model/conversation/repository;
- selected Codex executable/image is pinned and fingerprinted;
- selected model is frozen;
- request/token/cost ceilings are frozen;
- the task is a tiny deterministic fixture task, not Forge itself or another valuable repository;
- no untrusted PR/issue/comment/commit message is included in the prompt;
- real broker logs remain redacted;
- a separate no-secret validation phase independently inspects resulting workspace/patch.

## First live task

The first live task shall be structurally equivalent to the existing `safe_divide` fixture:

- tiny local disposable Git repository;
- one behaviorally specified file change;
- no external tools/services required by the task;
- no secrets in task content;
- no dependency installation;
- no deployment;
- strict time/request/token/cost ceiling;
- expected result is a W1 `PROPOSAL_ACCEPTED` patch, **not** final PASS.

The task is then separately eligible for normal Foundation verification. W4 itself does not perform or authorize that verification automatically.

## Live terminal outcomes

```text
PASS
REPAIR_REQUIRED
BLOCKED_EXTERNAL
SEALED_NEGATIVE_RESULT
```

Examples:

- bridge fixtures fail → `REPAIR_REQUIRED`;
- no separately supplied API key → `BLOCKED_EXTERNAL: LIVE_API_KEY_UNAVAILABLE`;
- provider/API unavailable after all local gates pass → `BLOCKED_EXTERNAL` with exact evidence;
- real task produces a safe W1 proposal inside all frozen limits → live pilot may pass after complete predecessor replay and publication gate;
- real provider fails the task without an authority/security defect → `SEALED_NEGATIVE_RESULT` may be appropriate, but never PASS.

## Non-goals

W4 does not authorize:

- copying ChatGPT subscription tokens/auth.json into an agent environment;
- automatic key creation or purchase;
- silent API billing changes;
- arbitrary Internet access for Codex;
- general-purpose network proxying;
- automatic F4/F5 handoff;
- merge/deploy;
- production use on valuable repositories;
- multi-provider routing;
- autonomous project management;
- swarm or Roof capabilities.

## W4 PASS authorization

W4 `PASS` authorizes only the next bounded Wall decision after one real pilot has been independently evidenced. The successor must be frozen explicitly; W4 does not pre-authorize broad autonomous coding.
