# FOUNDATION FAILURE 001 — Mutable F4 Baseline Can Redirect Final PASS

**Attack:** `FG-A05`
**Foundation state:** `REPAIR_REQUIRED`
**First false completion in Foundation matrix:** yes

## Frozen expectation

After F4 emits `CANDIDATE_VERIFIED`, changing only its recorded `baseline_commit` must not allow the final gate to evaluate a different candidate lineage and issue final `PASS`.

## Observed result

FG-A00 through FG-A04 passed, including the required 10/10 repeated happy-path control.

FG-A05 then:

1. created a valid F4 `CANDIDATE_VERIFIED` attempt on baseline A;
2. created a distinct committed baseline B containing an unrelated tracked change;
3. edited only `.forge/runs/U-0001/attempt-0001/EVIDENCE.json` so `baseline_commit` named B;
4. left the F4 applied diff unchanged;
5. ran the independent final gate.

Forge returned final `PASS`.

The final gate therefore evaluated `B + APPLIED.diff`, although F4 mechanically verified `A + APPLIED.diff`.

## Root cause

F4 binds `baseline_commit` only inside mutable JSON evidence. F5 validates the diff hash and current contract but has no independent immutable/reconstructable authority for which baseline produced the mechanically verified candidate.

The final gate trusts the mutable baseline field when recreating the candidate.

This violates the Foundation requirement that final evaluation run against the exact candidate mechanically verified by F4.

## Why adding another JSON hash is insufficient

A sidecar hash stored beside the evidence would detect accidental single-file edits but would still leave the candidate identity as self-reported mutable filesystem state. The repair should give the candidate an independent content-addressed Git identity.

## Required repair

F4 must seal a mechanically successful candidate into Git's object database before reporting `CANDIDATE_VERIFIED`:

- candidate tree comes from the exact staged index that survived F4 checks and locked regressions;
- create a deterministic candidate commit whose parent is the actual Doctor/F4 baseline;
- anchor it under an internal Forge Git ref for the attempt;
- bind candidate commit/ref into F4 evidence.

The final gate must:

- resolve the internal candidate ref independently of mutable F4 JSON;
- require it to match the candidate commit recorded by F4;
- derive the authoritative baseline from the sealed candidate commit's parent;
- require that parent to match F4 evidence;
- require the sealed commit diff to match the exact `APPLIED.diff` bytes;
- only then perform independent final evaluation.

FG-A05 becomes a permanent regression. Missing/moved/tampered candidate refs must also fail closed.

## Stop rule

FG-A06 through FG-A16 remain uncredited/unexecuted for Foundation terminal purposes until Repair 001 is complete and the Foundation matrix restarts from FG-A00.
