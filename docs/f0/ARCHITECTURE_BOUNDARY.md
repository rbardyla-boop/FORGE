# FORGE Architecture Boundary

## Foundation

The Foundation owns truth, state, verification authority, and failure memory.

```text
IDEA
  |
  v
CONTRACT
  |
  v
DOCTOR
  |
  v
ONE UNIT
  |
  v
VERIFY
  |
  v
GATE
  |
  +--> FAIL / REPAIR / BLOCK / NEGATIVE RESULT
  |
  +--> PASS
```

Foundation components, in order:

- F0 — survey + freeze
- F1 — persistent skeleton (`init`, `status`)
- F2 — contract authority
- F3 — environment Doctor
- F4 — one-unit lifecycle
- F5 — false-completion attack harness
- F6 — failure -> permanent regression
- FOUNDATION GATE

## Walls

Only after Foundation PASS:

- builder interface;
- Codex adapter;
- independent verifier;
- GitHub branch/CI enforcement;
- bounded next-unit planner.

## Roof

Only after Walls PASS:

- competing builders;
- specialist agents;
- swarm;
- AIS/adaptive compute;
- cross-project learning;
- self-improvement;
- UI.

## Load-bearing invariants

1. No contract -> no implementation.
2. No environment evidence -> no implementation.
3. No behavioral evidence -> no behavior PASS.
4. Worker does not own completion authority.
5. Verification must execute against the exact artifact eligible for approval.
6. Required checks cannot be silently weakened after implementation begins.
7. Serious failures become permanent tests.
8. No new layer may weaken a lower-layer invariant without explicit governed change and replay.
9. The repository/external state is canonical; conversation context is disposable.
10. Unknown/unverifiable is not PASS.
