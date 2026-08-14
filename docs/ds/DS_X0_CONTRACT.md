# DS-X0 — Autonomous Operator Gauntlet

Status: **FROZEN**

DS-X0 is an engineering gate, not a human study. It runs a deterministic
browser operator against a read-only `git archive` snapshot of the DS-E1
candidate. The operator may observe, click, reload, inject hostile storage
conditions, and record machine-checkable outcomes. It may not edit the
candidate or infer human comprehension.

## Frozen input

```text
candidate commit:     bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc
candidate parent:     d8727e7d5946f48ada39199e77df9564a62e4203
DS-E1 packet SHA-256: 2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817
browser:              Firefox, headless
executions:           exactly 50
context:              fresh browser context for every execution
network:              local fixture server only
```

The snapshot is assembled by FORGE from the exact commit. The source checkout
is fingerprinted before and after the run. A changed checkout, changed commit,
or changed DS-00–DS-06 source manifest invalidates the gate.

## Execution families

- 20 core task executions: known and bounded-unknown paths reach the correct
  terminal state.
- 6 safe-stop executions: stopping at every post-entry stage reaches the
  explicit safe terminal without a failure score or destructive instruction.
- 8 failure/recovery executions: malformed and forged state, storage failures,
  reload, clearing, and rapid activation recover safely.
- 6 false-success executions: recovery wording and terminal labels cannot
  promote inspection or location discovery into an operational recovery claim.
- 6 privacy/accessibility executions: local coarse state only, no outbound
  request, keyboard/mobile/reduced-motion boundaries, and no free-text fields.
- 4 replay/isolation executions: identical scripted traces replay identically
  and one context cannot leak state into another.

## Machine-checkable terminal criteria

```text
critical safety/privacy failures       = 0
false-success outcomes                 = 0
irrecoverable state corruption         = 0
candidate mutations                    = 0
cross-run leakage                      = 0
core task completion                    >= 95%
recovery-task completion               >= 95%
exact deterministic replay              = 100%
DS-I0 regression suite                  = PASS
DS-E1 source/public-surface properties = PASS
```

All failures are retained as evidence. DS-X0 has no repair authority.

## Terminal labels

```text
ENGINEERING_RELEASE_SUPPORTED / HUMAN_USABILITY_NOT_CLAIMED
ENGINEERING_REPAIR_REQUIRED / HUMAN_USABILITY_NOT_CLAIMED
ENGINEERING_RELEASE_FAILED / HUMAN_USABILITY_NOT_CLAIMED
```

Even a supported result says only that the bounded engineering properties
survived this synthetic gauntlet. It does not establish human usability,
comprehension, recovery behavior, retention, or effectiveness.
