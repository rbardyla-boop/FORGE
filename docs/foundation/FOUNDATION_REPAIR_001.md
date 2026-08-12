# FOUNDATION REPAIR 001 — Seal the Exact F4 Candidate in Git

**Triggered by:** `FOUNDATION_FAILURE_001.md`
**State:** FROZEN BEFORE IMPLEMENTATION

## Objective

Close the authority gap that allowed mutable F4 JSON to redirect final evaluation to a different baseline.

## Repair boundary

### F4 candidate seal

When, and only when, a lifecycle attempt has survived:

- exact patch application;
- scope checks;
- required checks;
- locked permanent regressions;
- operator/worktree postconditions;
- frozen-contract postcondition;

F4 must create a content-addressed Git candidate identity:

1. derive the exact candidate tree from the staged index that was verified;
2. create a deterministic Git commit with the actual F4 baseline as its single parent;
3. anchor that commit at:
   `refs/forge/candidates/<UNIT>/attempt-0001`;
4. persist `candidate_commit` and `candidate_ref` in F4 evidence;
5. if the ref cannot be created, F4 may not emit `CANDIDATE_VERIFIED`;
6. failed/non-candidate attempts may not leave an authoritative candidate ref.

The internal commit is not a product commit and does not move the product branch.

### Final gate authority

Before replay/evaluation, F5 must independently resolve the internal candidate ref and:

1. require the resolved commit to equal F4 `candidate_commit`;
2. derive the candidate commit's parent and require it to equal F4 `baseline_commit`;
3. compute the exact parent→candidate binary diff and require byte equality with F4 `APPLIED.diff`;
4. refuse missing/moved/non-commit/multi-parent candidate authority;
5. recreate/evaluate only from that authoritative sealed lineage.

The F4 JSON field is no longer sufficient authority by itself.

## Deterministic candidate commit

Candidate commit creation must set Forge-controlled deterministic author/committer metadata and message so the same:

- baseline commit;
- verified candidate tree;
- unit ID;
- frozen contract digest

produces the same candidate commit identity.

## Required repair tests

- FG-A05 baseline-only evidence substitution -> final gate refuses;
- deleting the internal candidate ref -> final gate refuses;
- moving the candidate ref to another commit -> final gate refuses;
- tampering `candidate_commit` evidence -> final gate refuses;
- tampering `APPLIED.diff` remains refused;
- existing good candidate still reaches final `PASS`;
- F4 failures/blocked states do not gain a candidate ref;
- F1–F6 predecessor suites remain green.

## Non-goals

This repair does not claim protection from a repository owner who intentionally rewrites Git objects/refs and all corresponding evidence coherently. The Foundation threat boundary requires worker/patch/evidence tamper resistance and exact candidate lineage, not hostile-owner cryptographic attestation. Remote transparency/signing belongs outside this repair.
