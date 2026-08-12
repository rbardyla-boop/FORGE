# FORGE-F4 Verdict

**Unit:** FORGE-F4  
**Verdict:** `PASS`

## Claim tested

Whether Forge can bind one frozen contract and one Doctor-ready committed baseline to one manually supplied patch, execute that attempt only in a disposable worktree, derive the actual diff/scope/check evidence itself, and compute the terminal state without allowing the patch author to declare completion.

## Result

`PASS`

The final F4 runtime survived **22/22 targeted lifecycle tests** after all review amendments were applied. Earlier passing runs were superseded whenever runtime code changed; only the final replay counts.

## Positive control

A valid in-scope manual patch on a Doctor-ready baseline:

- applied only in the disposable worktree;
- produced a non-empty Git-derived staged diff;
- passed all frozen required checks;
- preserved the exact staged diff through verification;
- left no unstaged tracked mutation;
- preserved the original frozen contract revision/digest;
- removed the disposable worktree;
- left operator product state unchanged;
- persisted exact evidence under `.forge/runs/`;
- received harness-owned terminal state `PASS`.

## Negative / falsification controls

The final suite proves rejection or fail-closed classification for:

- DRAFT contract;
- tampered frozen contract;
- non-ready Doctor baseline;
- symlinked patch input;
- malformed/non-applicable patch;
- out-of-scope change;
- forbidden-path change;
- ordinary required-check failure;
- explicit external blocker;
- timeout / verification inability;
- checker mutation beyond the frozen patch;
- checker re-staging different bytes on the same patched path;
- patch introducing an escaping tracked symlink;
- scope-glob attempt to make `*` cross a directory boundary;
- contract revision/digest change during the attempt;
- empty/no-diff patch;
- second attempt attempting to overwrite existing evidence;
- patch prose claiming `PASS`;
- advisory check attempting to influence completion;
- symlinked Forge runs directory;
- unauthorized `forge build`;
- patch-input path replacement/symlink boundary through descriptor-based regular-file reading.

## Lower-layer replay

The exact final F4 runtime also preserves the already-cleared foundation below it:

- FORGE-F3: **20/20 PASS** in bounded replay groups;
- repaired FORGE-F2: **14/14 PASS** in bounded replay groups;
- FORGE-F1: **11/11 PASS**.

A timed-out batch is never counted as partial success; timed-out predecessor batches were discarded and rerun in smaller terminal groups.

## Evidence / authority properties demonstrated

F4 now establishes that:

1. the worker/patch cannot choose the terminal state;
2. the applied artifact is the Git-produced diff actually verified;
3. scope is evaluated from actual changed paths rather than patch claims;
4. verification occurs on a disposable committed baseline, not the operator tree;
5. required checks cannot silently rewrite/re-stage the approved patch without detection;
6. the contract must remain unchanged through final evidence construction;
7. an already-existing attempt cannot be silently overwritten;
8. explicit external blocking is preserved as `BLOCKED_EXTERNAL`, never PASS;
9. advisory checks have no completion authority;
10. the operator product tree remains outside the implementation attempt.

## Disclosed limits

F4 does **not** prove that the frozen tests are sufficient to detect every semantic bug. It does not:

- create a patch;
- use an AI coding model;
- retry or replan failed work;
- merge or deploy;
- independently synthesize adversarial implementations;
- prove general program correctness;
- yet preserve discovered failures in a permanent cross-run regression ledger.

Those boundaries are intentional. F5 exists to attack the complete contract -> Doctor -> one-unit -> verify -> gate chain with preregistered known-good and deliberately defective implementations.

## Authorization

FORGE-F4 `PASS` authorizes exactly:

> **FORGE-F5 — False-Completion Attack Harness: preregister known-good and deliberately defective implementations, then prove the contract -> Doctor -> one-unit -> verify -> gate path accepts the good control and rejects the bad controls, including test deletion/weakening, normal-behavior regression, scope escape, stale-artifact verification, and worker false-completion claims.**

No AI builder is authorized.

## Publication packaging note F4-P1

The original 22-test F4 suite was stored in one 26,951-byte `tests/test_f4.py` file. The GitHub connector could not reliably transport that file as one exact blob while preserving the exact-tree publication gate. No runtime code or test logic was changed. The suite was mechanically split into `tests/f4_support.py` plus four `tests/test_f4_*.py` modules (6 + 6 + 6 + 4 tests) and replayed from scratch. All 22 tests passed again in independent terminal groups. This packaging-only change does not reopen lower-layer runtime gates because the F1–F4 runtime files are byte-identical to the already-cleared candidate.
