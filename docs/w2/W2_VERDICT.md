# FORGE-W2 Verdict — Provider Execution Containment

**Unit:** FORGE-W2
**Layer:** Walls / second unit
**Verdict:** `PASS`
**Validated branch head:** `8e867c585ad7614dc474cb211c41b9de9cff197c`
**Terminal clean-room run:** `31630630972`
**Base:** canonical W1 `PASS`

## Claim under test

Whether Forge can execute deterministic untrusted provider code inside a real operating-system containment boundary, expose only sealed W1-authorized inputs plus disposable workspace/output surfaces, derive the resulting patch independently from workspace bytes, and preserve zero completion/merge/deploy authority.

## Result

`PASS` within the frozen `linux-docker-v0.1` threat and environment boundary.

The terminal clean-room replay passed:

- W2 Repair 001 reclaimability: **7/7**
- W2 active isolation: **12/12**
- W2 workspace/egress: **13/13**
- W2 execution authority/handoff: **13/13**
- W2 amended request/output attacks: **2/2**
- W1 request authority: **7/7**
- W1 proposal submission: **10/10**
- W1 stale-integrity/handoff: **10/10**
- Foundation Repair 001: **5/5**
- Foundation Repair 002: **10/10**
- integrated Foundation FG-A00–A16: **PASS**, including its required **10/10 fresh-run reliability control**
- F6: **7/7 + 9/9 + 4/4**
- F5: **12/12 + 10/10**
- F4: **22/22 + 1/1**
- F3: **20/20 + 3/3**
- F2: **14/14 + 4/4**
- F1: **11/11**
- compile: **PASS**
- PR-base whitespace: **PASS**

No skipped predecessor gate receives terminal credit from earlier failed/invalid runs.

## Failure discovered and preserved

### W2-F001 — rejected provider-owned tree escaped cleanup

The initial terminal run correctly rejected a malicious provider-created `.forge/state.json`, but the container used UID/GID `65534:65534`. The resulting nested provider-owned directory could not be removed by the different non-root Forge host user, causing `TemporaryDirectory` cleanup to raise `PermissionError`.

The repair:

- runs provider containers as the exact numeric effective UID/GID of the non-root Forge host process;
- fails closed if Forge is host root;
- rejects rootless/user-namespace-remapped Docker modes for this v0.1 direct-bind backend;
- normalizes disposable workspace/output permissions after provider exit;
- adds no privileged cleanup helper, `sudo`, `--privileged`, or added capabilities.

The exact original attack is now a permanent regression and returns normal `PROVIDER_REJECTED` with no new `forge-w2-exec-*` residue.

## Invalid validation run preserved as zero credit

A later run stopped in the two amended edge tests because their requested fixture modes (`request_readonly`, `dir_output`) had not actually been added after an earlier GitHub write conflict. That was a validation-fixture defect, not W2 runtime behavior. Runtime bytes were not changed to repair it; the fixture was corrected and the complete terminal replay restarted from zero.

## Proven containment properties

Within `linux-docker-v0.1`, the malicious fixture demonstrates:

- operator repository is never mounted;
- operator `.forge` authority is absent from provider workspace;
- exact W1 request is mounted read-only;
- provider code runs as a numeric non-root host-owned UID/GID;
- container root filesystem is read-only;
- outbound provider network is disabled;
- Docker socket is absent;
- host accelerator/device nodes are absent;
- effective Linux capabilities are zero;
- `no-new-privileges` is active;
- PID namespace is private;
- PID, memory, CPU and wall-clock execution are bounded;
- host secret environment is not inherited;
- known host absolute paths are not readable through containment;
- provider may freely edit only the disposable workspace;
- provider-local Git state has zero patch authority;
- unsafe symlinks, FIFOs, `.forge` creation and malformed/extra egress are rejected;
- provider-authored `PATCH.diff` is rejected;
- Forge derives the authoritative patch in a separate trusted collector;
- accepted output reaches at most W1 `PROPOSAL_ACCEPTED`;
- `completion_authority: none` and `candidate_authority: none` remain invariant;
- Foundation handoff remains explicit and separate.

## Explicit boundary / non-claims

W2 does not prove arbitrary container escape resistance against kernel/runtime zero-days.

W2 supports only the frozen Linux Docker profile and intentionally fails closed for host-root Forge execution and incompatible Docker ownership modes.

W2 does not connect Codex, Claude, an API key, a networked provider, automatic F4/F5 handoff, merge, deployment, project-management autonomy, routing, swarms, or self-improvement.

## Authorization

W2 `PASS` authorizes exactly the next Wall unit:

> **FORGE-W3 — Codex Adapter Boundary:** freeze and test how a real Codex execution adapter acquires its executable/auth/network authority, consumes a W1 request through the W2 containment model where technically possible, returns only bounded trace/workspace effects, and still has zero completion authority.

W3 must freeze its credential/network/provider-acquisition policy before any real Codex execution. No automatic merge/deploy or autonomous project-management capability is authorized.
