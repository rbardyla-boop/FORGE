# F2 Repair 002 — Preflight / Acceptance Check Separation

**Triggered by:** `docs/f5/F5_FAILURE_001.md`  
**Status:** `PASS`

## Defect

F2 v0.1 stores one undifferentiated `required` check class. F3 therefore runs every final acceptance check on the pre-change baseline. A genuine new feature whose acceptance test correctly fails before implementation is misclassified as a broken baseline and cannot reach F4.

## Narrow repair

Extend each check authority record with a digest-bound boolean:

```json
{
  "id": "CHK_ACCEPT",
  "required": true,
  "preflight": false,
  "argv": ["python3", "acceptance.py"]
}
```

Semantics:

- `required=true, preflight=true`: must pass F3 Doctor before implementation and must run again in F4 after the patch;
- `required=true, preflight=false`: is deliberately deferred by F3 and must run in F4 after the patch;
- `required=false, preflight=false`: advisory; no completion authority in the current foundation;
- `required=false, preflight=true`: invalid authority.

## Compatibility

Legacy check records containing exactly `id`, `required`, and `argv` remain valid. Legacy required checks are interpreted as `preflight=true`; legacy advisory checks are interpreted as `preflight=false`.

Existing frozen legacy contract digests are verified against their original raw record and are not rewritten merely by the new validator.

Newly created/amended contracts normalize and persist the explicit `preflight` field so the phase distinction is digest-bound.

## F3 adaptation

Doctor executes only checks where both:

```text
required == true
preflight == true
```

Required `preflight=false` checks are reported as deferred acceptance checks, not as advisory and not as failed/not-run preflight checks.

Doctor may return `ENVIRONMENT_READY` when all preflight-required checks pass even if deferred acceptance behavior is absent on the baseline.

A contract with no preflight-required check is not environment-verifiable and must fail closed rather than claim readiness.

## F4 invariant

F4 continues to execute **all** `required=true` checks after applying the patch, regardless of `preflight` value, in frozen contract order.

Thus preflight checks become regression/environment gates and acceptance checks become post-change behavior gates.

## Required regressions

The repair cannot pass unless it proves:

1. explicit `preflight=false` is accepted and persisted in new contract authority;
2. changing `preflight` after freeze invalidates the digest;
3. advisory + preflight is rejected;
4. legacy checks remain valid and behave as preflight checks;
5. Doctor defers required acceptance-only checks;
6. Doctor still fails a red preflight check;
7. Doctor fails closed when no preflight check exists;
8. F4 executes both preflight and acceptance required checks after a patch;
9. the F5-A00 known-good feature patch is admitted and reaches PASS;
10. all prior F1-F4 substantive regressions remain green.

## Non-goals

This repair does not add:

- AI;
- hidden tests;
- an independent semantic evaluator;
- retries;
- F5 bad-control execution;
- merge/deployment authority.


## Compatibility clarification F2-R2-C1

F3 predecessor replay exposed that a blanket legacy default of `preflight=true` would silently promote old advisory checks into preflight authority and invalidate previously valid contracts. The compatibility rule is therefore frozen as:

- legacy `required: true` -> `preflight: true`;
- legacy `required: false` -> `preflight: false`;
- explicit `required: false, preflight: true` -> invalid.

This preserves the pre-repair meaning of legacy checks while requiring new contracts to persist the phase explicitly.


## Final verification

The repaired artifact passed:

- Repair-specific contract regressions: **4/4 PASS**;
- Repair-specific Doctor regressions: **3/3 PASS**;
- F4 known-good new-feature integration: **1/1 PASS**;
- original repaired F2 suite: **14/14 PASS**;
- original F3 suite: **20/20 PASS**;
- original F4 lifecycle/falsification suite: **22/22 PASS**;
- F1 canonical-state suite: **11/11 PASS**.

A predecessor replay exposed the legacy-advisory compatibility defect documented in F2-R2-C1. The repair remained open until that defect was corrected and all affected suites were replayed from the corrected artifact.


## Permanent regressions

- `tests/test_f2_repair_002.py` — phase persistence/digest binding, advisory/preflight authority, legacy required/advisory compatibility;
- `tests/test_f3_repair_002.py` — Doctor preflight execution, acceptance deferral, red-preflight blocking, no-preflight fail-closed;
- `tests/test_f4_repair_002.py` — genuine new-feature positive control admitted by Doctor and accepted only after both preflight and final acceptance pass.

## Verdict

F2 remains `PASS` with Repair 002 applied. F3 and F4 preserve their prior terminal guarantees under the new phase distinction. FORGE-F5 may resume only from the repaired canonical tree and must restart at preregistered positive control `F5-A00`; bad controls remain unauthorized until A00 passes there.
