# FORGE-F5 Final Attack Results

**Matrix:** frozen before bad-control execution
**Final false completions:** **0**

## Repaired results

| ID | Mechanical state | Final state |
|---|---|---|
| A00 known-good | `CANDIDATE_VERIFIED` | `PASS` |
| A01 zero-divisor bug | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A02 floor-division regression | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A03 legacy divide regression | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A04 delete acceptance checker | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A05 weaken acceptance checker | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A06 unrelated scope escape | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A07 patch-authored PASS prose/value | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A08 visible-example overfit | `CANDIDATE_VERIFIED` | `REPAIR_REQUIRED` |
| A09 escaping tracked symlink | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A10 verification-time re-stage | `REPAIR_REQUIRED` | `REPAIR_REQUIRED` |
| A11 explicit external dependency | `BLOCKED_EXTERNAL` | `BLOCKED_EXTERNAL` |

A08 is decisive: visible checks are insufficient for final completion, so mechanical success is intentionally non-final. See `F5_FAILURE_002.md`, `F5_REPAIR_001.md`, and `F5_RECOVERY_REPLAY.md`.
