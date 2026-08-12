# FORGE Failure Model v0.1

Forge exists to defeat these failure classes.

| ID | Failure | Foundation response |
|---|---|---|
| FM-01 | Worker falsely reports completion | worker statement has zero completion authority |
| FM-02 | Test does not exercise requested behavior | behavioral acceptance test required |
| FM-03 | New change breaks existing behavior | regression replay required |
| FM-04 | Worker deletes or weakens an inconvenient test | contract/check provenance + protected tests |
| FM-05 | Worker silently changes project scope | frozen contract; amendment ledger |
| FM-06 | Worker writes outside authorized files | allowed-write ceiling; fail closed |
| FM-07 | Environment cannot reproduce the application | Doctor before implementation |
| FM-08 | External prerequisite is discovered late | preflight/Doctor and BLOCKED_EXTERNAL |
| FM-09 | Build passes while application behavior is broken | structural and behavioral checks separated |
| FM-10 | AI verifier agrees with AI builder incorrectly | deterministic gates remain authoritative; independent evaluation is additional evidence |
| FM-11 | Conversation state diverges from repository state | repository/external state is canonical |
| FM-12 | Objective or success criteria change during implementation | explicit approved amendment only |
| FM-13 | Bug is fixed but not preserved | serious failure -> permanent eval/regression |
| FM-14 | Unsupported claim is promoted to PASS | evidence/claim separation |
| FM-15 | Operator is required late to perform an expert test they cannot perform | predeclare verifiability and automation path before build |
| FM-16 | New attractive project interrupts an unterminated unit | idea capture separate from unit state; unit must be explicitly terminalized |
| FM-17 | Verification runs against artifact different from approval artifact | exact-byte/artifact binding invariant |
| FM-18 | Agent repeats same failed action indefinitely | mechanical no-progress/repeated-error brakes |
| FM-19 | Agent loses task after context reset | conversation-loss recovery test |
| FM-20 | Enforcement mechanism itself is silently weakened | mechanism provenance and behavioral probe where feasible |
| FM-21 | A valid signature/approval is treated as proof of correctness | authorization is necessary where required, never sufficient evidence of behavior |
| FM-22 | A failure is hidden by relabeling it advisory | required/advisory semantics frozen before result |
| FM-23 | Test is modified to match the implementation rather than the contract | acceptance source and implementation authority separated |
| FM-24 | Green result is based on stale inputs or wrong baseline | base revision and evidence hashes bound to run |
| FM-25 | One lucky successful run is reported as reliability | repeated-run reliability metrics required before autonomy claims |

## Repeated-failure brake inherited from the Reliability Harness

- first equivalent failure -> repair;
- second equivalent failure -> materially replan;
- third equivalent failure -> stop and escalate;
- additional retries require recorded justification.

## Serious-failure closure

A serious failure is not repaired until:
1. minimal reproduction passes;
2. original broader test passes;
3. unrelated tests still pass;
4. permanent evaluation/regression is added;
5. previous failures remain fixed.
