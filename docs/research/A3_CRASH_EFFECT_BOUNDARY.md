# FORGE Research A3 — Crash-After-Effect Boundary

**Track:** research-only / non-authorizing  
**External effects:** simulated local sinks only  
**Expected conceptual outcome:** generic exactly-once claim may fail  
**W4/W5 authority:** unchanged

## Question

After exact-action approval has been durably accepted, can a purely local agent-control journal guarantee that an arbitrary external side effect occurs exactly once across a crash?

A3 tests the sequence:

```text
exact action approved
→ approval nonce + effect intent durably recorded
→ local state marks attempt IN_FLIGHT
→ simulated remote effect occurs
→ process crashes before local COMMITTED record
→ process restarts
```

The critical observation is that the durable local state is the same whether the crash occurred immediately before or immediately after the remote system performed the effect.

## Hypotheses

### H1 — generic local-journal exactly-once

> A local durable journal plus exact-action approval is sufficient to guarantee exactly-once execution against arbitrary external sinks.

A3 expects to falsify H1.

### H2 — fail-closed non-idempotent recovery

> When a non-idempotent/non-reconcilable effect is found `IN_FLIGHT` after restart, the safe local state is `EFFECT_UNCERTAIN`; automatic retry must be refused.

### H3 — idempotency-keyed recovery

> If the remote sink contract guarantees idempotency for a stable key derived from the approved action manifest, retrying the same in-flight intent can complete without duplicating the remote effect.

## Durable intent rule

Approval consumption and local effect-intent creation must occur in one SQLite transaction.

The durable record binds:

- approval nonce;
- exact action-manifest digest;
- approval-token digest;
- replay semantics;
- stable idempotency key derived from the action-manifest digest;
- state;
- attempt count;
- receipt hash after confirmed completion.

Once a valid approval has created a durable effect intent, later recovery continues that already-approved intent. It is not a new action and does not require extending the original approval expiry.

A different action may not reuse the consumed approval nonce.

## Replay-semantics classes

A3 uses:

```text
IDEMPOTENCY_KEYED
NON_RETRYABLE
```

`IDEMPOTENCY_KEYED` means the remote sink contract guarantees that repeated requests carrying the same key represent the same logical effect.

`NON_RETRYABLE` means FORGE has neither a remote idempotency guarantee nor an authoritative reconciliation operation. An in-flight crash therefore becomes uncertainty, not permission to retry.

Future work may add a separate `RECONCILABLE` contract, but A3 does not assume that a remote lookup is authoritative unless explicitly proven.

## State machine

```text
PREPARED
   ↓
IN_FLIGHT
   ├── confirmed response → COMMITTED
   └── crash/restart      →
          IDEMPOTENCY_KEYED: retry same key
          NON_RETRYABLE:  EFFECT_UNCERTAIN
```

`COMMITTED` is terminal for the research executor and must never invoke the sink again.

## Frozen attack / recovery set

```text
A3-00 approval consumption + intent creation are one durable transaction
A3-01 same approval nonce cannot authorize a different action
A3-02 exact repeated preparation is idempotent locally
A3-03 intent survives closing/reopening the journal
A3-04 crash after simulated remote effect leaves durable IN_FLIGHT state
A3-05 NON_RETRYABLE recovery refuses automatic retry
A3-06 blind retry of NON_RETRYABLE sink demonstrably duplicates effect
A3-07 IDEMPOTENCY_KEYED retry uses exact same stable key
A3-08 idempotent sink produces one logical effect across crash + retry
A3-09 recovered idempotent intent reaches COMMITTED
A3-10 COMMITTED intent never calls sink again
A3-11 receipt is stored as hash, not required as raw authority text
A3-12 approval expiry after durable preparation does not erase the prepared intent
A3-13 expired approval cannot create a new intent
A3-14 replay semantics cannot change after preparation
A3-15 action manifest cannot change after preparation
A3-16 sink claiming idempotency is insufficient when local intent was NON_RETRYABLE
A3-17 local idempotency label is insufficient if sink contract does not support it
A3-18 unknown/inconsistent journal state fails closed
```

## Decision rule

If A3-04 through A3-06 are reproduced, H1 receives `RESEARCH_NEGATIVE_RESULT` even if the implementation correctly handles H2/H3.

A passing test suite must not be mislabeled as evidence that arbitrary exactly-once effects are solved. The test suite can pass precisely because it demonstrates and contains the impossibility corridor.

## Expected architectural consequence if H1 fails

The effect policy needs a replay/recovery dimension in addition to "read-only / reversible / irreversible":

```text
replay_semantics:
  IDEMPOTENT
  IDEMPOTENCY_KEYED
  RECONCILABLE
  NON_RETRYABLE
```

Human approval answers "may this action happen?"

It does not answer the distributed-systems question "did the remote side already perform it before we crashed?"
