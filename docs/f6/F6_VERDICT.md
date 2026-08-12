# FORGE-F6 Verdict

**Unit:** FORGE-F6 — Failure -> Permanent Regression
**Technical verdict:** `PASS`
**Canonical merge:** pending at time of this record

## Claim tested

Whether Forge can preserve a serious defect as immutable failure memory, refuse repair closure until four frozen evaluator layers pass, and automatically replay locked permanent regressions against later implementation candidates before they may become `CANDIDATE_VERIFIED`.

## Result

`PASS` within the frozen F6 boundary.

F6 now provides:

- immutable per-repository failure registration under `.forge/failures/`;
- exact evaluator-byte SHA-256 binding at registration;
- four mandatory closure layers:
  - `MINIMAL_REPRODUCTION`;
  - `ORIGINAL_BROADER_CHECK`;
  - `UNRELATED_REGRESSIONS`;
  - `PERMANENT_EVALUATION`;
- append-only failed closure evidence;
- `LOCKED` status only after all four layers pass;
- permanent replay of the frozen evaluator;
- automatic replay of every locked failure against the still-live F4 disposable candidate before `CANDIDATE_VERIFIED`;
- fail-closed handling of ledger/evaluator tamper and evaluator mutation.

## Clean-room validation

GitHub Actions workflow run `31622466914` on branch head `2f681b719babb16cac1de69efc98afaa9d2af2ce` completed with overall conclusion `success`.

Required groups:

- F6 registration/integrity: **7/7 PASS**;
- F6 closure/replay: **9/9 PASS**;
- F6 lifecycle inheritance: **4/4 PASS**;
- F5 matrix: **12/12 PASS**;
- F5 final gate: **10/10 PASS**;
- F4 lifecycle: **22/22 PASS**;
- F4 Repair 002: **1/1 PASS**;
- F3 Doctor: **20/20 PASS**;
- F3 Repair 002: **3/3 PASS**;
- F2 Contract Authority: **14/14 PASS**;
- F2 Repair 002: **4/4 PASS**;
- F1 canonical state: **11/11 PASS**;
- Python compilation: `PASS`;
- corrected PR-base whitespace guard: `PASS`.

The first validation run is not terminal evidence because its whitespace command referenced an unavailable shallow-history `HEAD^`. All behavioral tests in that run were green, but the run was discarded. The validator was repaired to fetch history and compare against the exact PR base; the entire suite then replayed from zero in run `31622466914`.

## Decisive behaviors

1. Duplicate registration cannot overwrite a failure.
2. Failure record or stored evaluator tamper is detected.
3. Any one of the four closure layers can independently prevent closure.
4. Failed closure evidence persists without changing registered criteria.
5. Only an all-four-green closure produces `LOCKED`.
6. A locked failure replays successfully after repair.
7. Reintroduction of the defect is detected later.
8. An evaluator that mutates candidate state fails closed.
9. F4 with no locked failures remains backward-compatible.
10. F4 automatically records and passes a locked regression that remains fixed.
11. F4 downgrades a mechanically clean candidate to `REPAIR_REQUIRED` when a locked regression fails.
12. Locked evaluator mutation also blocks `CANDIDATE_VERIFIED`.

## Authority boundary

A worker, patch, evaluator, or conversation cannot delete or waive a locked failure by prose. The failure ledger owns failure-memory integrity; F4 consumes its locked regression result as a mandatory candidate gate.

## Disclosed limits

F6 is repository-local. It does not yet:

- share learned failures across projects;
- decide which failure belongs to which unrelated repository;
- provide autonomous root-cause analysis;
- perform retry/replan policy;
- introduce an AI builder;
- authorize merge or deployment;
- provide model routing, swarm behavior, or self-improvement.

## Authorization

F6 `PASS`, once canonicalized to `main` with unchanged runtime/test bytes, authorizes exactly:

> **FORGE FOUNDATION GATE — attack the complete F1-F6 chain as a single system, including repeated runs, context-loss recovery, corrupt state, wrong baseline, dependency blocking, deceptive patches, evaluator tamper, and locked-regression recurrence.**

The Walls and all AI builders remain unauthorized until the Foundation Gate passes.
