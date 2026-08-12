# FORGE F0 Salvage Ledger

## Classification vocabulary

- **SALVAGE** — mechanism belongs in Forge substantially as-is at the conceptual/interface level, after replay.
- **ADAPT** — useful mechanism, but Forge needs a materially different implementation or scope.
- **REFERENCE_ONLY** — keep as design evidence; do not place on current critical path.
- **DEFER** — explicitly outside Foundation.
- **REJECT** — unsuitable or contradicts current Forge boundaries.

## Evidence warning

No row below is `E4 REPRODUCED_FOR_FORGE` yet. F0 is an audit and freeze unit, not a replay/build unit.

| ID | Mechanism | Source | Evidence | Disposition | Forge destination | Basis | Required reproduction |
|---|---|---|---|---|---|---|---|

| MECH-001 | Task contract before implementation | Agent Reliability Harness | A/E1 | SALVAGE | F2 Contract Authority | Direct recovered design artifact specifies machine-readable task_id, objective, deliverables, constraints, tools, forbidden actions, completion checks, budgets, escalation, terminal states. | Create valid/invalid contracts; implementation command must refuse missing/unfrozen contract. |
| MECH-002 | Immutable objective/success criteria | Agent Reliability Harness | A/E1 | SALVAGE | F2 Contract Authority | Worker may propose amendment but cannot silently change objective, success criteria, baseline, gates, or terminal states. | Attempt post-freeze objective/gate edit; require recorded approved amendment. |
| MECH-003 | Canonical state outside conversation | Agent Reliability Harness | A/E1 | SALVAGE | F1 Persistent Skeleton | Recovered harness declares conversation disposable and project state canonical. | Kill process/context; new process reconstructs objective, phase, checkpoint, blocker and next action from repo state only. |
| MECH-004 | Conversation-loss recovery | Agent Reliability Harness | A/E1 | SALVAGE | F1/F4 | Explicit fresh-worker recovery test exists in harness design. | Fresh context receives only repo/state; must correctly resume. |
| MECH-005 | Bounded one-action cycle | Agent Reliability Harness | A/E1 | ADAPT | F4 Unit Lifecycle | LOAD->one action->VERIFY->SAVE EVIDENCE->UPDATE STATE. | Trace must show one independently verifiable transition per cycle; unlogged transition invalidates run. |
| MECH-006 | Mechanical completion authority | Agent Reliability Harness | A/E1 | SALVAGE | F4/F5 Gate | Harness defines DONE from evidence; worker statement has no authority. | Worker claims done with one missing required check; verdict must not PASS. |
| MECH-007 | Worker/evaluator separation | Agent Reliability Harness | A/E1 | SALVAGE | F5/W3 | Recovered artifact separates deterministic checks, independent evaluator, and human/policy approval. | Builder output alone cannot create PASS; evaluator cannot waive deterministic failure. |
| MECH-008 | Repeated-failure/no-progress brakes | Agent Reliability Harness | A/E1 | SALVAGE | F4 | Budgets, retries, no-progress window and repeated-error stop rules are specified. | Three equivalent failures trigger stop/escalation; repeated no-state-change loop is detected. |
| MECH-009 | Reconstructable traces | Agent Reliability Harness | A/E1 | ADAPT | F4 Evidence | Trace fields include state, action, tool I/O, evidence, files, tests, cost, duration, permission, checkpoint hash. | Rebuild run chronology from stored trace without chat transcript. |
| MECH-010 | Failure -> permanent evaluation | Agent Reliability Harness | A/E1 | SALVAGE | F6 Failure Memory | Serious failure closure explicitly requires minimal reproduction, broader test, unrelated tests, permanent eval and preserved prior fixes. | Reintroduce fixed defect; permanent eval catches it. |
| MECH-011 | Least privilege/environment-enforced permissions | Agent Reliability Harness | A/E1 | ADAPT | F2/F4 | Harness states prompt warnings are not security controls; environment enforces permission. | Unauthorized network/secret/shared-branch action fails mechanically. |
| MECH-012 | Allowed-write ceiling | Claude Powerplant | B/E2 | SALVAGE | F2 Contract Authority | Pinned source contains enumerated read/write/check sets and sanitized-copy-only project contract. | Patch attempts forbidden path write; run fails closed before PASS. |
| MECH-013 | Sanitized/disposable workspace | Claude Powerplant | B/E2 + E3 historical | ADAPT | F3/F4 | Source contract excludes secrets/dependencies/deployment and asserts sanitized_copy_only / realProjectMounted=false; dogfood records boundary defects. | Seed denied file; sanitized bundle must abort if it survives copy. |
| MECH-014 | Explicit required vs advisory verification | Claude Powerplant | B/E3 historical | ADAPT | F3/F5 | Powerplant documented dependency-bound checks as advisory under isolation and structural checks as required. | A broken behavioral dependency-bound check cannot be misrepresented as proven behavior. |
| MECH-015 | Evidence bundle / run classification | Claude Powerplant | B/E3 historical | SALVAGE | F4 Evidence | README/docs describe PATCH, manifests, verification report, classification, session summary, evidence hash. | Given a run ID, all verdict inputs must be reconstructable and hashes stable. |
| MECH-016 | Exact artifact verification invariant | Claude Powerplant dogfood | B/E3 historical | SALVAGE | F5 Gate | Dogfood caught corrupt generated file that passed checks against different bytes; ledger states verification must run against exact approved artifact. | Deliberately substitute artifact bytes between verify and approve; gate must fail. |
| MECH-017 | Manual approval/branch boundary | Claude Powerplant | B/E2/E3 historical | REFERENCE_ONLY | W4 GitHub Wall | Historical design applies approved patch only to dedicated branch and keeps mainline merge separate. | Deferred until Walls; verify Forge gate cannot write main directly. |
| MECH-018 | Scout advisory discovery | Claude Powerplant | B/E2/E3 historical | DEFER | Walls/Roof | Charter explicitly prevents Scout from mutating or self-promoting into product management. | No foundation implementation. |
| MECH-019 | Failure ledger with named regression | Cognitive OS | B/E3 historical | SALVAGE | F6 Failure Memory | Committed ledger maps scenario -> expected -> actual -> root cause -> fix -> regression -> locked status. | Import representative failures; reintroduce defect; named regression blocks. |
| MECH-020 | Adversarial/unit/integration/regression test strata | Cognitive OS | B/E3 historical | ADAPT | F5 Attack Harness | QA plan separates unit, integration, adversarial and release regression gates. | Fixture suite must demonstrate distinct failure classes and release gate aggregation. |
| MECH-021 | Behavioral probe beats declared intent | Cognitive OS S25-S32 | B/E3 historical | ADAPT | F5/F6 | Governance chain evolved from declared-effect weakness to behavior-derived trace probes and fail-closed unprobed invariants. | Proposal says 'preserve' but behavioral probe regresses; must block. |
| MECH-022 | Content/provenance binding of governed change | Cognitive OS S28-S32 | B/E3 historical | REFERENCE_ONLY | Later Foundation/Walls | Governance milestone binds pre/post artifact content and enforcement source hashes; useful against gate self-weakening but too complex for first bricks. | Defer implementation; reproduction required before adoption. |
| MECH-023 | Frozen evaluation contract | StackVerdict | B/E3 historical | SALVAGE | F2/F5 | v1.1 contract freezes scientific result, acceptance criteria, non-claims and stop conditions. | Attempt criteria change after result; contract hash mismatch invalidates verdict. |
| MECH-024 | Evidence receipt identity | StackVerdict | B/E3 historical | SALVAGE | F4 Evidence | v1.1 contract pins authoritative artifact and SHA-256 receipt; release stops on receipt change. | Mutate receipt/artifact; gate must detect hash mismatch. |
| MECH-025 | Evidence-vs-claim separation | StackVerdict | B/E3 historical | SALVAGE | F5 Gate | StackVerdict keeps real reproduced evidence, unverified imported receipts and fictional demos distinct; v1.1 non-claims are explicit. | Unverified/demo artifact may not satisfy reproduced-evidence gate. |
| MECH-026 | Cross-scope non-comparison | StackVerdict | B/E3 historical | REFERENCE_ONLY | Evaluation semantics | v1.1 acceptance forbids cross-scope winner calculation. | Useful principle, not load-bearing for FORGE-0.1. |
| MECH-027 | Gauntlet independent adversarial challenge | Gauntlet / recovered Harness | A/E1 | ADAPT | F5 Attack Harness | Recovered design requires decisive tests, invalidating failures, and independent verification before completion. | Known bad patches and shortcut attacks must be included before PASS. |
| MECH-028 | Terminal negative result discipline | Gauntlet / Forge method | A/E1 | SALVAGE | F4 State | Recovered terminal states preserve sealed negative outcomes instead of forcing success. | Failed claim can close reproducibly without scope pivot. |
| MECH-029 | Adaptive model allocation | AIS | A/D | DEFER | Roof | Separate scientific programme; no evidence needed for foundation. | No foundation implementation. |
| MECH-030 | Multi-agent swarm | Prior swarm goal / current synthesis | C/D | DEFER | Roof | Historical motivation, not a foundation mechanism. | No foundation implementation. |
