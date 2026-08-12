# FOUNDATION FAILURE 002 — Deleting a Locked Failure Erases the Obligation

**Attack:** `FG-A11`
**Foundation state:** `REPAIR_REQUIRED`
**False completion:** yes (`CANDIDATE_VERIFIED` issued after locked obligation disappeared)

## Frozen expectation

A previously locked serious failure must remain a permanent regression obligation. Deleting its filesystem directory must fail closed; deletion may not silently turn the set of locked regressions into an empty set.

## Observed result

After Repair 001, Foundation attacks FG-A00 through FG-A10 passed.

FG-A11 then:

1. registered and successfully closed `FAIL-F6L`, producing a locked permanent regression;
2. deleted `.forge/failures/FAIL-F6L`;
3. applied a later patch that should have been challenged by that locked regression;
4. F4 returned `CANDIDATE_VERIFIED` with `locked_regressions: []`.

## Root cause

F6 verifies the integrity of failure records and evaluators that are present, but the filesystem directory itself is the only enumeration authority. If the entire directory disappears, `run_locked_regressions()` has no independent record that the obligation ever existed.

This violates the F6/ Foundation invariant that a locked failure cannot be deleted or waived by changing local evidence state.

## Required repair

Failure registration and locking need independent content-addressed Git anchors outside `.forge/failures/`:

- registration creates a deterministic anchor under `refs/forge/failures/registered/<FAILURE_ID>`;
- successful closure creates a locked-obligation anchor under `refs/forge/failures/locked/<FAILURE_ID>`;
- anchors bind the immutable registration digest and evaluator identities; the locked anchor also binds closure identity/permanent evaluator identity;
- failure verification requires filesystem records and Git anchors to agree;
- a filesystem failure directory without its registration anchor fails closed;
- a registration anchor without its filesystem record fails closed;
- a LOCKED record without its locked anchor fails closed;
- a locked anchor whose record is missing/downgraded/tampered fails closed;
- F4 must verify failure-anchor completeness before and after its lifecycle before it can externally return `CANDIDATE_VERIFIED`.

FG-A11 becomes a permanent system regression. Explicit locked-ref deletion/movement and LOCKED→OPEN downgrade must also be repair regressions.

## Threat boundary

This prevents worker/evidence/filesystem deletion from silently erasing obligations. It does not claim protection from a hostile repository owner who coherently deletes both Git anchors and all matching filesystem evidence; cryptographic remote transparency is outside the Foundation threat boundary.

## Stop rule

FG-A12 through FG-A16 remain uncredited until Repair 002 is complete and the entire Foundation matrix restarts from FG-A00.
