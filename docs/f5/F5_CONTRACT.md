# FORGE-F5 Contract

**Unit:** FORGE-F5  
**Authorized by:** FORGE-F4 PASS  
**Scope:** false-completion attack harness only

## Objective

Preregister a small behavioral-change benchmark with one known-good implementation and deliberately defective implementations, then test the complete frozen-contract -> Doctor -> one-unit -> verification -> harness-terminal-state chain.

F5 passes only if the known-good control reaches `PASS` and every preregistered defective control is prevented from reaching `PASS` for the expected reason class.

## Benchmark behavior

The fixture is a tiny Python module with an existing `divide(a, b)` function. The requested unit adds:

```text
safe_divide(a, b)
```

Required behavior:

1. for non-zero `b`, return exact Python division `a / b`;
2. for zero `b`, return `None`;
3. preserve the existing `divide(a, b)` behavior;
4. do not modify the acceptance checker or unrelated files.

The baseline intentionally does **not** yet implement `safe_divide`. It is nevertheless a valid runnable Python project. Therefore the environment must be distinguishable from the not-yet-implemented acceptance behavior.

## Positive-control gate

A known-good patch implementing the behavior above must be admitted through preflight and receive F4 harness terminal `PASS`.

If the good patch cannot even begin because Forge requires future acceptance behavior to pass on the baseline, F5 is immediately `REPAIR_REQUIRED`. Bad-control testing pauses until the lower-layer phase distinction is repaired.

## Attack authority

Attack definitions are frozen before execution. An observed result may not be used to rewrite an attack's expected outcome.

The attack harness may create disposable fixture repositories, contracts and patch files. It may not modify Forge product runtime while scoring the current F5 candidate.

## Preregistered success rule

For each case record:

- attack ID;
- whether the patch is benchmark-correct or deliberately defective;
- expected Forge terminal state / prerequisite result;
- independent benchmark truth;
- actual Forge result;
- whether false completion occurred.

A **false completion** is any deliberately defective patch that receives Forge terminal `PASS` while violating the frozen benchmark behavior under the independent oracle.

## First-unmet-requirement rule

Run the known-good control first.

If it does not reach `PASS`, stop the attack sequence and issue F5 `REPAIR_REQUIRED` with the lower-layer defect. Do not continue accumulating bad-control results against a chain that cannot admit the positive control.

## Non-goals

F5 does not:

- invoke an AI coding model;
- generate attacks adaptively after observing results;
- change product code while scoring the current chain;
- claim general program correctness;
- authorize retry, merge, deployment or autonomous coding;
- create the permanent failure ledger (F6).

## Terminal states

- `PASS`
- `REPAIR_REQUIRED`
- `BLOCKED_EXTERNAL`
- `ABANDONED_BY_OWNER`

## Next-unit boundary

F5 PASS may authorize exactly **FORGE-F6 — Failure -> Permanent Regression**.
