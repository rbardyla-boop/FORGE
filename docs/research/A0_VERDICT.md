# FORGE Research A0 Verdict — Dynamic Context, Static Action Authority

**Track:** research-only / non-authorizing  
**Verdict:** `RESEARCH_PASS`  
**Authority effect:** none  
**W4 status changed:** no  
**W5 authorized:** no  
**Tested candidate:** `3c0b97ce1831a48763ebdefa258d5a2ae77574c3`  
**Successful push run:** `33251629656`

## Frozen claim

Within the A0 local filesystem experiment, an untrusted worker may acquire additional content-addressed `READ_SNAPSHOT` grants from a discovery universe frozen before execution while every grant remains bound to the exact original action-authority digest.

The implementation exposes no context-grant API that can amend action authority.

This verdict does **not** claim that information access is harmless or non-authoritative. Read access is itself a capability. A0 separates a pre-authorized maximum discovery universe from the action/effect authority surface and tests that lazy grants cannot cross that boundary through the registered mechanisms.

## Result

The successful candidate completed:

- Python compile gate: `PASS`;
- A0 registered attack matrix: `PASS`;
- 18 unittest methods covering frozen attacks A00–A24: `PASS`;
- whitespace gate: `PASS`.

The matrix includes:

- in-scope content-addressed snapshots;
- exact action-authority digest invariance across multiple grants;
- parent-linked grant ordering;
- traversal and absolute-path rejection;
- symlink target and symlink-component rejection;
- outside-universe and explicit-forbidden-path rejection;
- `.forge` denial fixture;
- non-regular-file rejection;
- per-resource, cumulative-byte and grant-count budgets;
- envelope tamper rejection;
- action-authority, envelope, parent, content-metadata and access-class tamper rejection;
- resource drift rejection after grant;
- malicious instructions inside granted content treated as inert bytes by the grant mechanism;
- reordered chain rejection;
- worker reason text unable to alter authority semantics;
- empty/oversized reason rejection.

## Failure history preserved

A0 did not pass on its first execution.

### Run `33251560753` — fixture design defect

Classification: **test-fixture / parameter defect**, not mechanism failure.

The A20 hostile-content fixture was larger than the already-frozen 64-byte per-resource budget. The grant mechanism correctly rejected it before the injection-inertness assertion could execute.

Repair:

- preserve the 64-byte safety bound unchanged;
- shrink the hostile fixture so the attack itself is inside the authorized read budget;
- add an explicit assertion that the fixture remains inside that bound.

The repaired A20 test then passed.

### Run `33251604065` — CI implementation defect

Classification: **CI implementation defect**, not mechanism failure.

The full A0 attack matrix passed, but the whitespace step used `git diff --check HEAD^ HEAD` after a depth-1 checkout, so `HEAD^` was unavailable.

Repair:

- remove the unnecessary history dependency;
- use history-independent `git diff --check` for this branch-scoped gate.

The subsequent candidate passed the attack matrix and whitespace gate.

## Evidence boundary

`RESEARCH_PASS` establishes only that the current A0 implementation survived the frozen local attack matrix on the tested candidate.

It does not establish:

- arbitrary information-flow security;
- safe reading of arbitrary secrets;
- safe Internet discovery;
- automatic trust of newly discovered evidence;
- safe persistent-memory promotion;
- exact-action human approval;
- crash-safe exactly-once external effects;
- coordinator truthfulness at the final return path;
- superiority over existing agent-security systems;
- W4 completion;
- W5 authorization;
- merge/deploy or production readiness.

## Signal that survives

The useful mechanism-level signal is narrower than a generic "sealed context pack":

> **Seal action authority and the maximum discovery envelope; allow the active read set to grow only through content-addressed, parent-linked grants whose action-authority digest cannot change.**

This avoids requiring the planner to know every needed file before execution while still making discovery expansion mechanically distinct from effect-authority expansion.

## Next research question

A0 deliberately does not solve the harder problem created by successful discovery:

> What happens when information obtained from a lower-trust grant is then used to justify a higher-effect action request?

That is the proposed research-only A1 target: **taint/provenance-aware composition**. A1 should attempt to prevent information gained through legitimate discovery from laundering itself into new authority merely by being restated by the worker.

A1 must be frozen independently and receives no FORGE milestone authority from this verdict.
