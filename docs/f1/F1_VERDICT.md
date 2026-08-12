# FORGE-F1 Verdict

**Verdict:** `PASS`

## Claim under test

The smallest executable Forge skeleton can initialize canonical project state and reconstruct that state from a completely new process without conversation context.

## Implemented surface

- repository-root executable `forge` launcher;
- `forge_core/cli.py`;
- `forge_core/state.py`;
- F1 contract and explicit amendment F1-A1;
- F1 deterministic test suite.

No pip installation is required. Forge F1 uses only the Python standard library.

## Decisive checks

1. `forge init` creates exactly `.forge/project.json` and `.forge/state.json`.
2. A second `forge init` leaves both files byte-identical.
3. Two separately located projects with the same project name produce byte-identical canonical state.
4. A fresh process reconstructs project name, current unit, unit state, terminal state and largest remaining gap from disk only.
5. 25/25 additional fresh-process `forge status` runs returned `canonical_state=VALID` with no state-byte changes.
6. Missing state fails closed.
7. Corrupt state fails closed.
8. Partial state is not overwritten.
9. Tampered canonical state is not overwritten.
10. A symlinked `.forge` directory is rejected and no out-of-repository state is written.
11. `forge doctor` is absent and returns a command error.
12. Python byte-compilation succeeds.

## Defect found during F1

The initial packaging approach used PEP 517/setuptools metadata. In a fresh offline virtual environment, pip attempted to provision the build backend before Forge could run.

This was treated as a foundation defect, not an operator instruction problem.

### Repair F1-A1

The packaging dependency was removed. F1 now uses a repository-root executable launcher and standard-library package only. The full acceptance suite was rerun after the repair.

## Test result

- deterministic unit/integration tests: **11/11 PASS**;
- repeated fresh-process recovery: **25/25 PASS**;
- state-byte stability across repeated status reads: **PASS**;
- unauthorized Doctor command: **REJECTED**;
- production capability beyond F1: **NOT INTRODUCED**.

## Non-claims

F1 does not prove:

- environment readiness;
- contract immutability for arbitrary work units;
- behavioral correctness of generated patches;
- independent verification;
- false-completion resistance;
- autonomous coding reliability.

Those belong to later units.

## Authorization

F1 PASS authorizes exactly:

> **FORGE-F2 — Contract Authority: define and freeze one machine-readable unit contract, bind its objective/success criteria/scope/checks/terminal states to a stable digest, and prove implementation cannot begin or silently change those authorities without an explicit amendment.**

F2 does not authorize Doctor, AI builders, autonomous planning, or deployment.
