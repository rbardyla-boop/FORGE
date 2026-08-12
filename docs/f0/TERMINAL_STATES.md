# FORGE Terminal States

Every independently judgeable unit must end in an explicit terminal state. Vague completion states are forbidden.

## PASS

All locked success criteria are satisfied and the required evidence/gates pass.

## PASS_WITH_DISCLOSED_LIMITS

The core bounded result is complete and useful, but explicitly identified non-core limits remain. A failed required gate cannot be converted into this state.

## REPAIR_REQUIRED

The unit is not terminal-successful. One or more required criteria failed, but a bounded repair path exists within the current objective.

## SEALED_NEGATIVE_RESULT

The tested claim or approach failed after the declared falsification programme. The failure, surviving signals, and untested design space are preserved reproducibly.

## BLOCKED_EXTERNAL

A genuine external dependency prevents completion. Record:
- exact blocker;
- evidence it is external;
- completed work;
- shortest resumption procedure.

`BLOCKED_EXTERNAL` must never be represented as PASS.

## ABANDONED_BY_OWNER

The operator explicitly ends the unit/project. Preserve the exact state, evidence, unresolved gates, and resumption information.

## Forbidden vague statuses

Do not use:
- almost complete;
- basically done;
- promising;
- production ready without verification;
- should work;
- probably fixed;
- largest remaining gap: none while required gates remain open.

## Unit rule

Finishing a unit means reaching a terminal state, not necessarily obtaining a positive result.
