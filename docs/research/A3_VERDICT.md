# FORGE Research A3 Verdict — Crash-After-Effect Boundary

**Overall hypothesis verdict:** `RESEARCH_NEGATIVE_RESULT`  
**Track:** research-only / non-authorizing  
**Tested candidate:** `2d6ec09768fdbec2fac0d29b2c121a6bf7448ef9`  
**Successful lifecycle run:** `33252018097`  
**A3 unittest methods:** 16  
**W4 status changed:** no  
**W5 authorized:** no

## What failed

A3 falsified the generic hypothesis:

> A local durable journal plus exact human approval is sufficient to guarantee exactly-once execution against an arbitrary external side-effect sink.

The test suite is green because it successfully reproduces and contains the failure corridor. A green implementation test is not converted into a positive mechanism claim.

## Decisive sequence

The registered tests reproduced:

```text
approved exact action
→ durable local intent
→ local state IN_FLIGHT
→ simulated remote non-idempotent effect occurs once
→ simulated process crash before local COMMITTED record
→ restart sees only IN_FLIGHT
```

At restart, the local journal cannot distinguish:

```text
case A: crash occurred before the remote effect
case B: crash occurred after the remote effect
```

For a `NON_RETRYABLE` sink with no authoritative reconciliation operation, automatically retrying case B produces a duplicate effect. The A3 blind-retry fixture demonstrates that duplication directly.

Therefore the safe local recovery state is:

```text
EFFECT_UNCERTAIN
```

not `COMPLETED`, and not automatic retry.

## What survived

Two narrower mechanisms survived the matrix.

### H2 — fail-closed non-retryable recovery

Supported in the frozen fixture.

An `IN_FLIGHT` durable intent classified `NON_RETRYABLE` is not automatically executed again after restart. Recovery returns `EFFECT_UNCERTAIN` and leaves the remote fact unresolved.

### H3 — idempotency-keyed recovery

Supported in the frozen fixture.

When the sink contract actually guarantees idempotency for the stable key derived from the exact approved action-manifest digest:

- the first remote call may occur before a crash;
- restart retries using the exact same stable key;
- the fake idempotent sink records two calls but only one logical effect;
- the recovered local intent reaches `COMMITTED`;
- a later call on the committed intent does not invoke the sink again.

A local declaration of `IDEMPOTENCY_KEYED` is not enough. The executor rejects that mode when the sink contract does not expose idempotency support.

## Other matrix results

A3 also confirmed within the research fixture that:

- approval consumption and durable intent creation occur in one SQLite transaction;
- the same approval nonce cannot bind a different action;
- exact repeated preparation is locally idempotent;
- durable intent survives closing/reopening the journal;
- replay semantics cannot be changed after preparation;
- an approval that expires after durable preparation does not erase the already-approved intent;
- an expired approval cannot create a new intent;
- the exact manifest cannot change after preparation;
- receipt evidence is stored as a hash rather than treated as raw authority text;
- unknown/inconsistent journal states fail closed.

## Architectural correction

The original coarse effect classes are insufficient for recovery policy.

An execution envelope needs a separate replay/recovery dimension, for example:

```text
replay_semantics:
  IDEMPOTENT
  IDEMPOTENCY_KEYED
  RECONCILABLE
  NON_RETRYABLE
```

The exact set requires later experiments. A3 directly tested only `IDEMPOTENCY_KEYED` and `NON_RETRYABLE`.

The control system must distinguish three separate questions:

```text
AUTHORIZATION
May this effect happen?

EXECUTION
Was the effect invocation attempted?

REMOTE FACT
Did the remote system actually perform the logical effect?
```

A human gate solves the first question. A local append-only/durable journal can preserve the second. Neither alone necessarily establishes the third.

## Why this matters for agent systems

Without this distinction, an agent runtime can be perfectly permissioned and still duplicate irreversible actions after a crash or timeout.

The safe rule from A3 is:

> Do not infer remote completion from local intent, and do not infer safe retry merely from uncertainty.

For non-retryable effects, uncertainty must remain a first-class terminal/recovery state until an external reconciliation mechanism or human decision resolves it.

## Evidence boundary

This is not a new distributed-systems impossibility theorem. The useful result is the control-system consequence for FORGE: authorization/effect class and replay semantics must be modeled separately, and the append-only log must be allowed to record honest uncertainty rather than force `PASS` or retry.

A3 does not establish safe real-world reconciliation, production transaction semantics, or W4/W5 authority.

## Next research target

The next highest-value research unit is **A4 — persistent-memory promotion**:

> Can observations gathered from untrusted/dynamic context remain quarantined across runs until independent evidence criteria promote them into authoritative long-lived memory, while contradictions and expiry remain representable?

A4 should remain research-only unless separately incorporated through FORGE's milestone authority chain.
