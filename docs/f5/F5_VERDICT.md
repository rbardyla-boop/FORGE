# FORGE-F5 Verdict

**Unit:** FORGE-F5
**Verdict:** `PASS`

## Claim tested

Whether the frozen contract -> Doctor -> one-unit mechanical verification -> independent final-gate chain accepts a known-good implementation while preventing preregistered defective/deceptive implementations from reaching final `PASS`.

## Result

`PASS` within the frozen F5 benchmark boundary.

F5 exposed two real lower-layer defects before earning this verdict:

1. `F5_FAILURE_001`: Doctor conflated baseline readiness with future acceptance behavior. F2 Repair 002 separated preflight and final-acceptance checks.
2. `F5_FAILURE_002`: A08 hard-coded visible examples and fooled F4's former mechanical `PASS`. F4 Repair 001 changes mechanical success to `CANDIDATE_VERIFIED`; F5 Repair 001 gives final completion authority to an exact-artifact-bound independent gate.

## Final authority chain

```text
frozen contract
  -> Doctor preflight
  -> bounded patch lifecycle
  -> exact diff/scope/required checks
  -> CANDIDATE_VERIFIED
  -> independent exact-artifact evaluator
  -> PASS / REPAIR_REQUIRED / BLOCKED_EXTERNAL
```

## Publication recovery replay

After the interrupted scratch workspace was lost, F5 was reconstructed from canonical Repair-002 `main` and replayed before publication:

- A00-A11 attack matrix: **12/12 expected outcomes**;
- direct final-gate attack suite: **10/10 PASS**;
- original F4 lifecycle behaviors: **22/22 PASS** after the authorized success-state transition;
- F4 Repair 002 genuine-new-feature integration: **1/1 PASS**.

The decisive A08 overfit now reaches `CANDIDATE_VERIFIED` but final `REPAIR_REQUIRED`.

F1-F3 implementation blobs are inherited unchanged from canonical Repair-002 and are not modified by this F5 publication. See `F5_RECOVERY_REPLAY.md`.

## Disclosed limits

F5 does not prove arbitrary program correctness or evaluator sufficiency. The evaluator is orchestrator-supplied and Python-only in this Foundation version. No AI builder, retry/replan engine, merge authority, or deployment authority is introduced.

## Authorization

FORGE-F5 `PASS` authorizes exactly:

> **FORGE-F6 — Failure -> Permanent Regression: create the canonical failure/evaluation ledger and prove that a serious failure cannot be marked repaired until its minimal reproduction, broader checks, unrelated regressions, and permanent evaluation all pass; locked failures must then replay automatically on later verification.**

No AI builder is authorized.
