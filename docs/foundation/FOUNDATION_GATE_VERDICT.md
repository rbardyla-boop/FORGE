# FORGE Foundation Gate Verdict

**Unit:** FORGE-FOUNDATION-GATE
**Technical verdict:** `PASS`
**Canonical merge:** pending at time of this record

## Claim tested

Whether the complete F1–F6 Foundation can repeatedly take a behaviorally specified manual software change from canonical state and frozen contract through environment preflight, bounded implementation verification, independent final evaluation, and permanent failure replay while preventing preregistered defective, deceptive, tampered, stale, or externally blocked cases from being represented as final `PASS`.

## Result

`PASS` within the frozen Foundation boundary.

The terminal clean-room GitHub Actions run was:

- run ID: `31624551170`;
- tested branch head: `9f392dffe21508d011cb01a31a72764295647bfe`;
- overall conclusion: `success`.

## Terminal evidence burden

The exact tested candidate passed:

- Python compilation: `PASS`;
- Foundation Repair 001 exact-candidate seal regressions: **5/5 PASS**;
- Foundation Repair 002 Git-anchored failure-obligation regressions: **10/10 PASS**;
- Foundation system matrix FG-A00–FG-A16: **all PASS**;
- FG-A01 repeated-run reliability: **10/10 independent fresh end-to-end final PASS** with no leaked worktree residue;
- F6 registration/integrity: **7/7 PASS**;
- F6 closure/replay: **9/9 PASS**;
- F6 lifecycle inheritance: **4/4 PASS**;
- F5 false-completion matrix: **12/12 PASS**;
- F5 final-gate attacks: **10/10 PASS**;
- F4 lifecycle: **22/22 PASS**;
- F4 Repair 002 genuine-feature integration: **1/1 PASS**;
- F3 Doctor: **20/20 PASS**;
- F3 Repair 002: **3/3 PASS**;
- F2 Contract Authority: **14/14 PASS**;
- F2 Repair 002: **4/4 PASS**;
- F1 canonical state: **11/11 PASS**;
- PR-base whitespace guard: `PASS`.

Timeouts and failed/incomplete earlier runs were not credited.

## Failures discovered by the Foundation Gate

The Foundation did not pass on its first design.

### FOUNDATION FAILURE 001 — mutable baseline redirects final evaluation

FG-A05 changed only F4's recorded `baseline_commit`. The old final gate reconstructed a different committed baseline plus the same patch and still issued final `PASS`, meaning mechanical verification and final evaluation were not bound to the same candidate lineage.

Repair 001 added deterministic content-addressed candidate sealing:

- the actual F4 baseline is captured independently before execution;
- the exact verified diff is reconstructed against that baseline;
- a deterministic candidate commit is created;
- the commit is anchored under `refs/forge/candidates/<UNIT>/attempt-0001`;
- the final gate independently verifies ref → commit → single parent → exact parent/candidate diff before evaluation.

After repair, FG-A05 and the dedicated candidate-ref tamper/deletion/movement tests pass.

### FOUNDATION FAILURE 002 — deleting a locked failure erases obligation

FG-A11 deleted `.forge/failures/FAIL-F6L`. The old F6 enumeration interpreted the missing directory as no locked regression and a later defective patch received `CANDIDATE_VERIFIED`.

Repair 002 added independent Git anchors for failure existence/status:

- registered failures: `refs/forge/failures/registered/<FAILURE_ID>`;
- locked obligations: `refs/forge/failures/locked/<FAILURE_ID>`;
- anchors bind registration digest, evaluator identities and locked closure identity;
- F4 verifies complete filesystem/ref agreement before and after its legacy lifecycle;
- missing/moved/downgraded/tampered obligations now fail closed.

After repair, FG-A11 and the dedicated registration/locked-anchor deletion, movement and downgrade tests pass.

## Final Foundation authority chain

```text
canonical repository state
        ↓
frozen contract authority
        ↓
Environment Doctor / preflight
        ↓
bounded manual patch in disposable candidate
        ↓
required checks + locked permanent regressions
        ↓
exact candidate Git seal
        ↓
CANDIDATE_VERIFIED
        ↓
sealed lineage verification
        ↓
independent exact-artifact evaluator
        ↓
final PASS / REPAIR_REQUIRED / BLOCKED_EXTERNAL
```

Serious failures that become `LOCKED` remain separately anchored permanent obligations and are automatically replayed before future candidate verification.

## FORGE-0.1 ruling

Within the frozen Foundation benchmark and threat boundary, **FORGE-0.1 survives the declared falsification programme**.

This is not a claim that Forge proves arbitrary software correct or that unknown bugs cannot exist. It is evidence that the Foundation now prevents the preregistered false-completion classes from silently counting as completion and preserves serious discovered failures as future regression obligations.

## Disclosed threat boundary

The Foundation is designed to resist worker/patch/evidence tamper and accidental/local loss within the governed repository workflow. It does not claim cryptographic resistance to a hostile repository owner who coherently rewrites/deletes all Git anchors, Git objects, filesystem evidence and corresponding history. Remote signed transparency/attestation is outside FORGE-0.1.

## Remaining non-goals

Foundation PASS does **not** authorize:

- Codex or another AI coding agent directly;
- autonomous product/project management;
- automatic merge or deployment;
- model routing/AIS;
- multi-agent swarms;
- cross-project learned policies;
- self-modifying Forge;
- a GUI.

## Authorization

Once this exact tested runtime/test candidate is canonicalized to `main`, Foundation `PASS` authorizes exactly:

> **W1 BuilderAdapter — define and prove a provider-agnostic untrusted builder interface whose input is frozen task/repository authority and whose only output is a proposed patch plus trace. The builder has zero completion, merge, deployment, contract-amendment or evaluator authority.**

Codex integration remains a later Walls unit after W1 itself passes.
