# FORGE-W4 Bridge Verdict — Credential/Network Broker

**Unit:** FORGE-W4
**Sub-gate:** credentialless credential/network bridge
**Bridge verdict:** `BRIDGE_PASS`
**Overall W4 verdict:** **NOT PASS**
**Live sub-gate:** `LIVE_GATE_PENDING`
**Validated branch head:** `63d4f4bc906d19d442f412459b72cf9d83135fe6`
**Terminal clean-room run:** `31635722406`
**Base:** canonical FORGE-W3 `PASS`
**Real OpenAI API request in this bridge gate:** **NONE**
**Real OpenAI/ChatGPT credential in this bridge gate:** **NONE**

## Claim under test

Whether Forge can construct and falsify a brokered network topology in which untrusted coding-provider execution receives only a short-lived Forge capability, cannot receive or directly reach the upstream account credential/service, while a separate trusted broker can mediate bounded Responses-style traffic and exact workspace bytes still terminate only at W1 proposal authority.

## Result

`BRIDGE_PASS` within the frozen W4 credentialless/fake-upstream boundary.

This result is deliberately **not** W4 `PASS`. The real Codex/OpenAI API pilot required by the W4 contract has not occurred. No successor beyond W4 is authorized by this document.

## Terminal evidence on exact candidate

GitHub Actions run `31635722406` completed with overall `success` on exact head `63d4f4bc906d19d442f412459b72cf9d83135fe6`.

### W4 bridge gates

- front-gate request authentication and budget policy: **10/10**
- generated Codex broker configuration authority: **6/6**
- official Responses-proxy live policy: **4/4**
- credentialless dual-network broker system attacks: **12/12**
- literal egress-IP no-routing negative control: **1/1**
- Codex-shaped streaming broker/failure composition: **8/8**
- compile: **PASS**
- PR-base whitespace: **PASS**

### Exact predecessor replay on the same W4 candidate

- W3 Repair 001: **5/5**
- W3 executable/config/credential authority: **12/12**
- W3 JSONL/process behavior: **12/12**
- W3 W2/W1 composition: **10/10**
- W3 actual W2-contained seam: **3/3**
- W2 Repair 001: **7/7**
- W2 active isolation: **12/12**
- W2 workspace/egress: **13/13**
- W2 execution authority/handoff: **13/13**
- W2 amended request/output: **2/2**
- W1 request authority: **7/7**
- W1 proposal submission: **10/10**
- W1 stale-integrity/handoff: **10/10**
- Foundation Repair 001: **5/5**
- Foundation Repair 002: **10/10**
- integrated Foundation FG-A00–A16: **PASS**, including the required **10/10 fresh-run reliability control**
- F6: **7/7 + 9/9 + 4/4**
- F5: **12/12 + 10/10**
- F4: **22/22 + 1/1**
- F3: **20/20 + 3/3**
- F2: **14/14 + 4/4**
- F1: **11/11**

## Proven bridge properties

Within the credentialless fixture boundary:

- the provider receives no upstream account secret;
- the broker Docker inspect state does not contain the upstream secret;
- the fixture upstream secret enters the broker-side credential component through stdin rather than provider-visible environment/argv;
- the provider receives only a fresh per-run Forge client capability;
- missing/wrong capability is rejected;
- provider Authorization is consumed by the Forge front gate and is not forwarded as upstream account authority;
- only the frozen Responses request path/content shape is forwarded;
- request count, request bytes, response bytes, total bytes and expiry are bounded;
- the provider is attached only to a fresh Docker internal network;
- the upstream fixture is attached only to the egress network;
- the broker is dual-homed but runs without privilege/capabilities required for packet routing;
- a provider-side literal-IP connection attempt to the upstream's egress-network IP fails;
- provider direct public-Internet access fails while broker-mediated access succeeds;
- broker/provider logs and W1 trace do not contain the upstream secret sentinel;
- generated disposable CODEX_HOME contains no `auth.json`;
- generated Codex model-provider config contains only the frozen Forge broker provider and points its `env_key` to `FORGE_W4_CLIENT_TOKEN`, never an OpenAI account key;
- repository/project config cannot redirect the broker endpoint through the generated-config API;
- live-proxy policy pins an absolute non-symlink executable and exposes no `--upstream-url`, dump, HTTP shutdown or TLS-disable override;
- the documented official proxy default upstream is frozen as `https://api.openai.com/v1/responses` for the eventual live sub-gate;
- a Codex-shaped fixture consumes a fake streaming Responses sequence through the authenticated broker and edits only the disposable workspace;
- malformed upstream response, upstream non-2xx, upstream timeout and provider timeout fail closed;
- exact workspace bytes remain patch authority through the W2 external validator/trusted collector;
- successful bridge execution terminates only at W1 `PROPOSAL_ACCEPTED`;
- no F4/F5 artifact is created by W4 bridge success;
- operator tracked state/worktree registry remains unchanged;
- each run receives a fresh client capability and topology;
- containers/networks/temp state are removed by fixture cleanup;
- no real OpenAI network request occurred in the terminal bridge gate.

## Explicit live-gate boundary

The following remain unproven and therefore block overall W4 `PASS`:

1. pin and verify the exact official Codex Linux executable artifact for the frozen live pilot;
2. pin and verify the exact official `codex-responses-api-proxy` Linux artifact;
3. run a no-secret preflight using those exact binaries and the W4 topology;
4. determine whether a separately supplied API key is available through the trusted live-secret mechanism without printing or persisting it;
5. if no key exists, terminate the live sub-gate `BLOCKED_EXTERNAL: LIVE_API_KEY_UNAVAILABLE`;
6. if a key exists and billable execution is explicitly authorized, run exactly one tiny bounded real Codex task through the broker;
7. independently inspect the resulting no-secret workspace/patch and require the result to stop at W1 `PROPOSAL_ACCEPTED`;
8. replay the complete W4/W3/W2/W1/Foundation/F6-F1 stack on the final live candidate before publication.

## Billing/authentication firewall

This bridge result authorizes **no silent API spending and no ChatGPT subscription credential conversion**.

Forge shall not extract/copy the operator's ChatGPT/Codex `auth.json`, OAuth tokens or subscription credentials into the W4 broker. The live pilot initially supports only a separately supplied API key handled by the trusted broker path.

A real billable OpenAI request must not be made merely to finish this unit. If the required separate API credential or explicit spending authority is absent, the correct result is `BLOCKED_EXTERNAL`, not a weakened security design and not a false W4 PASS.
