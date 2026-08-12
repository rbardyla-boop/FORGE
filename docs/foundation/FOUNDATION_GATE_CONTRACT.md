# FORGE Foundation Gate Contract

**Unit:** FORGE-FOUNDATION-GATE
**State:** FROZEN BEFORE SYSTEM-LEVEL EXECUTION
**Base:** canonical FORGE-F6 `PASS`
**AI builder:** forbidden
**Walls:** locked

## Claim under test

> The complete F1–F6 Forge Foundation can repeatedly take a behaviorally specified manual software change from canonical state and frozen contract through environment preflight, bounded implementation verification, independent final evaluation, and permanent failure replay while preventing preregistered defective, deceptive, tampered, stale, or externally blocked cases from being represented as final `PASS`.

This is the Foundation-level evaluation of FORGE-0.1. Component-level PASS is necessary but not sufficient.

## Success criteria

Foundation may receive `PASS` only if all of the following are true on the exact candidate:

1. A fresh repository can complete the entire good path to final `PASS`.
2. The good path succeeds **10/10 independent fresh runs** with no operator-worktree or worktree-registry residue.
3. Process/conversation loss does not prevent reconstruction from canonical repository state/evidence.
4. Corrupt canonical state cannot manufacture progress or convert a known-bad implementation into final PASS.
5. Frozen contract tamper cannot reach candidate or final PASS.
6. F4 evidence/baseline substitution cannot cause the final gate to approve bytes that were not the mechanically verified candidate.
7. Applied-diff/evidence tamper cannot reach final PASS.
8. Independent evaluator substitution, symlinking, mutation, failure, or explicit external blocking has the declared fail-closed semantics.
9. The frozen F5 visible-example-overfit implementation remains rejected by the independent final gate.
10. A locked F6 regression is automatically replayed against later candidates and recurrence blocks `CANDIDATE_VERIFIED`.
11. Deleting or corrupting a locked failure obligation cannot make the obligation silently disappear and permit candidate/final PASS.
12. A failed/non-candidate F4 attempt cannot be promoted by the final gate.
13. Final evaluation evidence cannot be overwritten to obtain a different result.
14. Explicit external dependencies remain `BLOCKED_EXTERNAL`, never PASS.
15. Every F1–F6 predecessor regression suite remains green.
16. No Builder, autonomous merge/deploy, swarm, routing, or self-improvement authority exists in the Foundation candidate.
17. Whitespace/compilation/scope gates pass.

## Preregistered system attacks

Run in frozen order. Stop on the first false completion or structural authority failure; preserve it before repair.

| ID | Attack / control | Required result |
|---|---|---|
| FG-A00 | Fresh end-to-end correct feature | final `PASS` |
| FG-A01 | Ten independent repetitions of FG-A00 | 10/10 final `PASS`; no residue |
| FG-A02 | Resume command sequence only from repository files in fresh processes | state/contract/evidence reconstruct correctly |
| FG-A03 | Corrupt canonical state then attempt known-bad implementation | no final `PASS`; status fails closed |
| FG-A04 | Modify frozen contract after freeze | blocked before candidate/final PASS |
| FG-A05 | Modify only F4 `baseline_commit` evidence after `CANDIDATE_VERIFIED` | final gate must refuse; never final PASS |
| FG-A06 | Modify F4 applied diff/evidence binding | final gate refuses |
| FG-A07 | Evaluator symlink/substitution/mutation/failure | no final PASS |
| FG-A08 | F5 visible-example overfit | `CANDIDATE_VERIFIED` at most; final `REPAIR_REQUIRED` |
| FG-A09 | Explicit external dependency | `BLOCKED_EXTERNAL` |
| FG-A10 | Reintroduce a locked permanent regression in a later patch | F4 `REPAIR_REQUIRED` |
| FG-A11 | Delete a previously locked failure directory/obligation before later patch | fail closed; obligation may not disappear |
| FG-A12 | Tamper a locked evaluator/record | fail closed |
| FG-A13 | F4 required check fails | no candidate and no final PASS |
| FG-A14 | Try final gate on non-candidate evidence | refused |
| FG-A15 | Try to overwrite existing final evaluation with a second result | refused; first evidence unchanged |
| FG-A16 | Scan CLI/commands for unauthorized builder/merge/deploy/autonomy surface | absent |

## Repeated-run reliability

FG-A01 is a required reliability experiment, not a single lucky control. Ten fresh repositories must independently traverse:

`init -> contract create/freeze -> Doctor -> manual patch -> CANDIDATE_VERIFIED -> independent final gate -> PASS`

No run may reuse `.forge` state, evidence, Git worktrees, evaluator output, or product repository bytes from another run.

Required result: **10/10**. One unexplained failure prevents Foundation PASS.

## Evidence authority

- repository bytes, frozen contracts, exact diffs, evaluator hashes, locked failure records, and generated gate evidence are authoritative;
- conversation summaries and worker prose are not authority;
- timeouts/incomplete executions receive zero credit;
- a structural defect found by a positive or negative control stops the matrix until the defect is preserved and repaired;
- after any runtime repair, affected and predecessor gates are replayed from zero.

## Repair rule

If the Foundation Gate discovers a defect:

1. record a named Foundation failure;
2. reduce to a minimal reproducer;
3. define the repair boundary before implementation;
4. add a permanent regression;
5. replay the failing system attack;
6. replay the complete affected lower stack;
7. restart the Foundation Gate matrix from FG-A00 if completion authority changed.

## Terminal states

- `PASS` — all system attacks, repeated-run reliability, predecessor replay and publication checks pass.
- `REPAIR_REQUIRED` — any required control/gate fails with an internal repair path.
- `BLOCKED_EXTERNAL` — a genuinely external prerequisite prevents the Foundation evaluation itself; cannot be represented as PASS.
- `SEALED_NEGATIVE_RESULT` — FORGE-0.1 is falsified under the frozen boundary after declared repair budget is exhausted.

## Non-goals

The Foundation Gate does not add or authorize:

- Codex or any AI builder;
- autonomous product/project management;
- automatic merge or deployment;
- multi-agent execution;
- adaptive routing/AIS;
- cross-project learned memory;
- a GUI;
- self-modifying Forge.

## Authorization on PASS

A Foundation `PASS` may authorize only the first Walls unit:

> **W1 BuilderAdapter — define a provider-agnostic untrusted builder interface whose output is only a proposed patch + trace and whose completion authority is zero.**

Codex integration remains a later Walls unit after W1 itself passes.
