# FORGE-W1 Verdict — Provider-Agnostic Proposal Boundary

**Unit:** FORGE-W1
**Technical verdict:** `PASS`
**Canonical merge:** pending at time of this record

## Claim tested

Whether Forge can expose frozen repository/task authority to a provider-neutral proposal boundary and accept only a proposed patch plus bounded trace while preserving zero completion authority and all Foundation guarantees.

## Result

`PASS` within the frozen W1 boundary.

The terminal clean-room GitHub Actions run was:

- run ID: `31625722255`;
- tested branch head: `38b497d9007e1da8be2cf3b4904ff741bd26d7e1`;
- overall conclusion: `success`.

## W1 evidence

The exact tested candidate passed:

- Python compilation: `PASS`;
- W1 request authority: **7/7 PASS**;
- W1 proposal submission/scope attacks: **10/10 PASS**;
- W1 stale-integrity/Foundation-handoff attacks: **10/10 PASS**;
- Foundation Repair 001: **5/5 PASS**;
- Foundation Repair 002: **10/10 PASS**;
- integrated Foundation FG-A00–FG-A16 matrix: **PASS**;
- Foundation repeated fresh-run reliability: **10/10 final PASS**;
- F6: **7/7 + 9/9 + 4/4 PASS**;
- F5: **12/12 + 10/10 PASS**;
- F4: **22/22 + 1/1 PASS**;
- F3: **20/20 + 3/3 PASS**;
- F2: **14/14 + 4/4 PASS**;
- F1: **11/11 PASS**;
- PR-base whitespace guard: `PASS`.

## W1 authority result

W1 adds only:

```text
forge proposal request UNIT
forge proposal submit UNIT --patch PATCH --trace TRACE
forge proposal verify UNIT
```

A request is bound to:

- frozen contract revision/digest;
- exact committed baseline;
- full frozen task authority;
- Doctor readiness;
- F6 failure-anchor integrity;
- deterministic request digest.

An accepted proposal is bound to:

- exact request digest;
- exact patch bytes/hash;
- exact trace bytes/hash;
- actual Git-derived changed paths;
- frozen scope ceiling;
- baseline/contract identity;
- `proposal_state: PROPOSAL_ACCEPTED`;
- `completion_authority: none`;
- `candidate_authority: none`;
- `checks_executed_by_forge: false`.

The proposal boundary does not execute provider code or trusted acceptance checks.

## Decisive boundary tests

- a trace may literally claim `PASS`, `DONE`, `MERGE`, or `DEPLOY`; the resulting proposal still has zero authority;
- a behaviorally defective but well-formed scoped patch may be `PROPOSAL_ACCEPTED`, proving W1 does not pretend to be a trusted verifier;
- handing that same bad stored patch to Foundation F4 produces `REPAIR_REQUIRED`;
- handing a known-good stored patch explicitly to F4 produces `CANDIDATE_VERIFIED`, not final PASS;
- malformed, out-of-scope, forbidden, `.forge/**`, escaping-symlink, symlink-source, oversize and malformed-trace proposals are rejected;
- stale baseline/contract authority and request/proposal/patch/trace tamper are detected;
- proposal operations leave tracked product bytes and operator worktree registry unchanged;
- no `build`, `builder`, `merge`, `deploy`, `swarm`, autonomous, Codex-specific or Claude-specific CLI execution surface exists.

## Construction ruling

The first Wall is now load-bearing: Forge can define a coding task for an external future worker and ingest its output without giving that worker any completion authority.

W1 does **not** prove that executing an external coding-agent process is safely contained. That is the largest remaining gap before a real provider is connected.

## Next unit decision

As lead project manager, the next bounded Walls unit is:

> **FORGE-W2 — Provider Execution Containment: prove that a deterministic fixture provider can be invoked through a constrained execution boundary that receives only the W1 request/repository inputs it is authorized to see, returns only patch + trace, cannot mutate the operator repository or Forge authority, and cannot obtain completion/merge/deploy authority.**

This intentionally inserts a containment unit before a Codex-specific adapter. The earlier high-level Walls sketch placed Codex immediately after BuilderAdapter, but W1 evidence makes the missing execution boundary explicit. Connecting Codex before proving that boundary would repeat the worker-before-factory failure mode Forge was built to eliminate.

A Codex-specific adapter becomes **W3** after W2 passes. This also allows useful work to continue while Codex usage is unavailable.

## Still unauthorized

W1 PASS does not authorize:

- Codex, Claude, or another real coding provider;
- networked provider execution;
- broad shell/credential access;
- automatic proposal handoff to F4;
- PASS authority;
- merge or deployment;
- retries/replanning/project-management autonomy;
- routing, swarms, AIS, or Roof capabilities.
