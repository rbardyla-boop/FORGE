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

1. capture the actual repository `HEAD` before the bounded lifecycle begins;
2. require successful F4 evidence to name that same captured baseline;
3. reconstruct the exact verified candidate from that captured baseline plus the exact F4 `APPLIED.diff` bytes;
4. require the reconstructed staged diff to be byte-identical to F4's verified diff, making the reconstructed tree equivalent to the staged candidate F4 verified;
5. create a deterministic Git commit with the actual captured F4 baseline as its single parent;
6. anchor that commit at:
   `refs/forge/candidates/<UNIT>/attempt-0001`;
7. persist `candidate_commit` and `candidate_ref` in F4 evidence before the CLI can return `CANDIDATE_VERIFIED`;
8. if reconstruction/ref creation fails, F4 may not externally return `CANDIDATE_VERIFIED`;
9. failed/non-candidate attempts may not leave an authoritative candidate ref.

The implementation may wrap the existing tested F4 lifecycle at the CLI authority boundary rather than rewriting its kernel. The wrapper's captured baseline is independent of mutable post-run JSON, and the reconstructed tree must be byte-equivalent to the verified staged diff before sealing.

The internal commit is not a product commit and does not move the product branch.

### Final gate authority

Before replay/evaluation, F5 must independently resolve the internal candidate ref and:

1. require the resolved commit to equal F4 `candidate_commit`;
2. derive the candidate commit's parent and require it to equal F4 `baseline_commit`;
3. compute the exact parent→candidate binary diff and require byte equality with F4 `APPLIED.diff`;
4. refuse missing/moved/non-commit/multi-parent candidate authority;
5. only then permit the existing independent evaluator gate to run.

The implementation may wrap the existing tested F5 final gate; mutable F4 JSON is no longer sufficient authority by itself.

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
