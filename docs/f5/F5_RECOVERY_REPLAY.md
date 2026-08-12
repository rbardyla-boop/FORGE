# FORGE-F5 Recovery Replay

**Purpose:** preserve the publication-recovery boundary after the original local scratch workspace was lost during interrupted GitHub transport.

## Canonical starting point

Recovery started from GitHub `main` at F2 Repair 002, tree `1d80f2165cc23be0c564886a20145cd6256ec64d`.

The canonical F1, F2/Repair-002, and F3/Repair-002 implementation blobs are not changed by this F5 publication.

## Reconstructed F5 authority repair

The recovered runtime implements the already-falsified authority boundary:

- F4 mechanical success -> `CANDIDATE_VERIFIED`;
- only the independent final gate may issue final `PASS`;
- the final evaluator is bound to the exact F4 evidence, baseline, applied diff, and current frozen contract;
- evaluator mutation, evidence tamper, symlinked evaluator, in-repository evaluator, repeated final evaluation, or candidate replay mismatch fail closed.

## Recovery replay

The publication candidate was rerun after reconstruction:

- frozen F5 A00-A11 attack matrix: **12/12 expected outcomes**;
- direct final-gate attacks: **10/10 PASS**;
- original F4 lifecycle behaviors: **22/22 PASS** with successful mechanical outcomes adapted to `CANDIDATE_VERIFIED`;
- F4 Repair 002 genuine-new-feature integration: **1/1 PASS**.

The decisive A08 visible-test overfit reaches `CANDIDATE_VERIFIED` but receives final `REPAIR_REQUIRED` from the held-out evaluator.

The lower F1-F3 implementation files are inherited byte-for-byte from the already-canonical Repair-002 tree; they are not reconstructed or modified by this publication.

## Evidence rule

Unattached blobs created during the interrupted publication are not evidence and are not referenced by the final tree. Only blobs explicitly included in the final Git tree are canonical.
