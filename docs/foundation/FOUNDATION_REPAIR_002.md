# FOUNDATION REPAIR 002 — Anchor Failure Obligations in Git

**Triggered by:** `FOUNDATION_FAILURE_002.md`
**State:** FROZEN BEFORE IMPLEMENTATION

## Objective

Make the existence and locked status of serious failure obligations independently reconstructable so deleting/downgrading `.forge/failures/*` cannot silently reduce the regression set.

## Registration anchor

After legacy F6 registration succeeds, Forge must create a deterministic content-addressed Git object and anchor it at:

`refs/forge/failures/registered/<FAILURE_ID>`

The anchor payload binds:

- failure ID;
- immutable registration digest;
- all four frozen evaluator SHA-256 identities.

A failure directory without its registration anchor, or an anchor without its matching verified directory/record, is an integrity failure.

## Locked-obligation anchor

After an all-four-green closure succeeds, Forge must create a second deterministic anchor at:

`refs/forge/failures/locked/<FAILURE_ID>`

The locked payload binds:

- failure ID;
- registration digest;
- closure attempt identity;
- frozen permanent-evaluator SHA-256 identity.

A `LOCKED` record without this anchor is invalid. A locked anchor whose record is missing, no longer `LOCKED`, or no longer matches the bound digest/evaluator is also invalid.

## Lifecycle boundary

The external F4 CLI authority wrapper must verify complete failure-anchor consistency:

1. before invoking the legacy lifecycle;
2. again after the legacy lifecycle succeeds but before sealing/returning `CANDIDATE_VERIFIED`.

Any mismatch is a hard fail-closed lifecycle refusal or `REPAIR_REQUIRED`; it may not become a candidate.

The existing F6 kernel remains responsible for executing frozen permanent regressions. Repair 002 adds existence/status authority rather than replacing evaluator execution.

## CLI boundary

Failure register/close/replay/verify commands may wrap the existing F6 kernel:

- registration wrapper creates/validates the registered anchor;
- closure wrapper creates the locked anchor only on successful closure;
- replay/verify first require anchor consistency;
- failed closure does not create a locked anchor.

## Required repair regressions

1. registration creates a valid registered anchor;
2. successful closure creates a valid locked anchor;
3. failed closure creates no locked anchor;
4. delete failure directory while registered/locked ref remains -> fail closed;
5. delete registered ref while directory remains -> fail closed;
6. delete locked ref while record remains `LOCKED` -> fail closed;
7. move/tamper registered or locked ref -> fail closed;
8. downgrade a `LOCKED` record to `OPEN` while locked ref remains -> fail closed;
9. normal F6 register/close/replay behavior remains green;
10. FG-A11 deleted locked obligation no longer reaches `CANDIDATE_VERIFIED`;
11. F1–F6 predecessor regressions remain green.

## Threat boundary

Custom Git refs are content-addressed local authority against worker/filesystem evidence loss. A hostile repository owner who deliberately deletes both every anchor and all corresponding filesystem records remains outside the Foundation threat boundary. Remote signed transparency may be added later but is not required for FORGE-0.1.
