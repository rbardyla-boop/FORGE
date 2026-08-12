# FORGE-F6 Contract — Failure -> Permanent Regression

**Unit:** FORGE-F6
**State:** FROZEN BEFORE IMPLEMENTATION
**Base:** canonical FORGE-F5 `PASS`
**AI builder:** forbidden

## Objective

Create a canonical failure/evaluation ledger and prove that a serious defect cannot be marked repaired until all required closure layers pass, after which its locked evaluator is automatically replayed against later implementation candidates.

## Core invariant

> A serious defect is not repaired because the patch looks fixed. It is repaired only after its frozen reproducer/evaluators pass, and the defect remains a permanent regression obligation afterward.

## Failure registration

`forge failure register FAILURE_ID --file SPEC.json`

Registration must be append-only and must freeze, at minimum:

- failure ID;
- unit/source reference;
- human-readable scenario, expected behavior and observed behavior;
- root-cause field (may initially be `UNKNOWN`);
- exactly four evaluator layers:
  1. `MINIMAL_REPRODUCTION`;
  2. `ORIGINAL_BROADER_CHECK`;
  3. `UNRELATED_REGRESSIONS`;
  4. `PERMANENT_EVALUATION`;
- exact evaluator bytes and SHA-256 identity for each layer.

The evaluator criteria are archived at registration time. Closure may not replace, weaken, delete or reorder them.

## Repair closure

`forge failure close FAILURE_ID --candidate PATH`

Closure must:

1. verify the registered failure record and evaluator hashes;
2. evaluate all four frozen layers against the supplied candidate/repository;
3. require all four to pass;
4. preserve failed closure evidence without changing the registered criteria;
5. mark the failure `LOCKED` only after all layers pass;
6. persist closure evidence non-destructively.

Any failed/missing/tampered layer => no repaired/locked state.

## Permanent replay

`forge failure replay FAILURE_ID --candidate PATH`

A locked failure must replay its frozen `PERMANENT_EVALUATION` against a later candidate and return a deterministic regression verdict.

## Automatic F4 inheritance

Before F4 may emit `CANDIDATE_VERIFIED`, every locked failure relevant to the repository must replay its frozen permanent evaluator against the exact patched disposable candidate.

Any locked regression failure => F4 `REPAIR_REQUIRED`.

The candidate/worker cannot waive, delete or relabel a locked regression.

## Evidence requirements

Failure records and evaluator bytes live under `.forge/failures/` and must be bound by SHA-256. Evidence must preserve:

- registered criteria identity;
- evaluator hashes;
- closure/replay result and exit code;
- bounded stdout/stderr;
- candidate identity where available;
- status transition;
- completion authority = `failure_ledger`.

## Attack requirements

F6 must prove at least:

1. duplicate registration is refused;
2. failure-record tamper is detected;
3. evaluator tamper/deletion is detected;
4. each of the four closure layers independently blocks closure when failing;
5. a failed closure does not weaken the frozen criteria;
6. only all-four-green closure reaches `LOCKED`;
7. locked replay passes after the repair;
8. later reintroduction of the defect is detected;
9. evaluator mutation of the candidate fails closed;
10. future F4 candidates automatically inherit locked regressions;
11. a locked regression failure prevents `CANDIDATE_VERIFIED`;
12. existing F1-F5 substantive regressions remain green.

## Non-goals

F6 does not add:

- an AI builder;
- retry/replan autonomy;
- cross-project learned failure sharing;
- automatic merge/deployment;
- a GUI;
- model routing or swarm behavior.

## Terminal gate

F6 can receive `PASS` only after its own attack suite and the complete required F1-F5 regression replay pass on the exact publication candidate.

F6 `PASS` authorizes only the Foundation Gate. It does not authorize the Walls or an AI builder by itself.
