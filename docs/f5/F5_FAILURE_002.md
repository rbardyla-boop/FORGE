# F5 Failure 002 — Visible-Test Overfit Reaches PASS

**F5 state at discovery:** `REPAIR_REQUIRED`
**Attack:** `F5-A08`
**First false completion:** yes

A08 deliberately hard-codes the visible acceptance examples while violating general `safe_divide(a,b)` behavior. The pre-repair F4 lifecycle reported mechanical `PASS`, while a held-out evaluator proved the implementation defective.

## Root cause

Mechanical evidence sufficiency and final behavioral completion were conflated. Adding more visible examples would not repair that authority flaw.

## Required repair

- F4 mechanical success becomes non-final `CANDIDATE_VERIFIED`.
- A separate independent final gate consumes exact F4 evidence and the exact applied diff.
- Evaluator identity/bytes and result are bound into immutable final evidence.
- Evaluator failure -> `REPAIR_REQUIRED`; explicit external block -> `BLOCKED_EXTERNAL`; only evaluator success may yield final `PASS`.
- A00 must final-PASS and A08 must not final-PASS after repair.

The repaired F5 matrix satisfies those requirements. See `F5_REPAIR_001.md`.
