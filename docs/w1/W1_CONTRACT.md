# FORGE-W1 Contract — Provider-Agnostic BuilderAdapter Proposal Boundary

**Unit:** FORGE-W1
**Layer:** Walls / first unit
**State:** FROZEN BEFORE IMPLEMENTATION
**Base:** canonical FORGE Foundation `PASS`
**Codex / AI execution:** forbidden

## Objective

Define and prove a provider-agnostic boundary through which an untrusted future builder can receive frozen task authority and return only:

1. a proposed patch; and
2. a bounded reconstructable trace.

The proposal has **zero completion authority**. W1 does not execute Codex or any other coding model.

## External CLI

W1 adds exactly one top-level namespace:

```text
forge proposal request UNIT
forge proposal submit UNIT --patch PATCH --trace TRACE
forge proposal verify UNIT
```

The namespace is deliberately `proposal`, not `builder`: W1 handles data crossing the trust boundary, not execution of an agent.

No `build`, `builder`, `merge`, `deploy`, `swarm`, `autonomous`, provider-specific, or model-specific command is authorized.

## Request authority

`forge proposal request UNIT` may create exactly one deterministic request for the unit.

Before creating it, Forge must independently require:

- a valid frozen contract;
- `contract ready` authority;
- an `ENVIRONMENT_READY` Doctor result;
- current repository `HEAD` equal to the Doctor baseline;
- complete F6 registered/locked failure-anchor integrity.

Persist under:

```text
.forge/proposals/<UNIT>/request-0001/REQUEST.json
```

The request must bind at minimum:

- schema/version;
- unit ID;
- contract revision and digest;
- exact baseline commit;
- the complete frozen contract authority required by a builder:
  - objective;
  - deliverables;
  - success criteria;
  - scope allowed/forbidden paths;
  - declared checks;
  - terminal-state vocabulary;
  - non-goals;
  - forbidden actions;
- output protocol version;
- `completion_authority: none`;
- a deterministic `request_digest` over the canonical request payload.

The request contains no timestamp or conversational state. The repository remains canonical.

## Proposal trace schema

The external trace is JSON with exactly:

```json
{
  "schema": "forge.builder-trace.v0.1",
  "adapter": "provider-neutral-name",
  "provider_run_id": "opaque-provider-run-id",
  "events": [
    {
      "seq": 1,
      "kind": "PLAN|EDIT|CHECK_ATTEMPT|NOTE",
      "summary": "bounded text"
    }
  ]
}
```

Rules:

- `seq` starts at 1 and is contiguous;
- events are bounded in count and text length;
- the trace may report what the provider attempted, including its own check attempts, but none of that becomes Forge verification evidence;
- prose such as `PASS`, `DONE`, `MERGE`, or `DEPLOY` inside a trace has zero authority.

## Proposal submission

`forge proposal submit UNIT --patch PATCH --trace TRACE` may create exactly one proposal for `request-0001`.

Before accepting it, Forge must re-establish:

- request file integrity/digest;
- live frozen contract revision/digest equals request authority;
- live `HEAD` equals request baseline;
- Doctor is still `ENVIRONMENT_READY` on that same baseline;
- F6 failure-anchor integrity remains complete.

Input files must be regular non-symlink files and bounded:

- patch: at most 1 MiB;
- trace: at most 256 KiB.

Forge must validate the proposal in a disposable detached worktree at the exact request baseline:

1. patch parses/applies with whitespace errors treated as errors;
2. actual changed paths are derived from Git, never trusted from provider prose;
3. `.forge/**` is always forbidden;
4. actual changed paths fit the frozen contract allowed-path ceiling;
5. frozen forbidden paths remain forbidden;
6. patched tracked symlinks may not escape the disposable worktree;
7. proposal validation may not mutate the operator product worktree;
8. **no frozen required check, final evaluator, or locked regression is executed by W1 submission.** Those remain Foundation authority.

On successful submission, persist:

```text
.forge/proposals/<UNIT>/request-0001/
├── REQUEST.json
└── proposal-0001/
    ├── PATCH.diff
    ├── TRACE.json
    └── PROPOSAL.json
```

`PROPOSAL.json` binds:

- request digest;
- contract revision/digest;
- baseline commit;
- exact patch SHA-256/byte length;
- exact trace SHA-256/byte length;
- actual changed paths;
- `proposal_state: PROPOSAL_ACCEPTED`;
- `completion_authority: none`;
- `checks_executed_by_forge: false`;
- `candidate_authority: none`.

`PROPOSAL_ACCEPTED` means only that the data is well-formed, scoped, and safe to hand to the existing Foundation lifecycle. It is never a candidate verdict or completion verdict.

## Proposal verification

`forge proposal verify UNIT` must verify stored request/proposal integrity and current authority without changing product state.

It must fail on:

- request/proposal JSON tamper;
- patch or trace byte tamper;
- contract drift/amendment;
- baseline movement;
- missing/corrupt failure anchors;
- missing/symlinked stored artifacts.

On success it may return the repository-relative stored patch path for explicit handoff to `forge unit run`.

## Foundation handoff

The only path from a W1 proposal toward completion remains:

```text
PROPOSAL_ACCEPTED
      ↓
forge unit run --patch <stored PATCH.diff>
      ↓
Foundation F4/F6 gates
      ↓
CANDIDATE_VERIFIED
      ↓
Foundation sealed final gate
      ↓
PASS / REPAIR_REQUIRED / BLOCKED_EXTERNAL
```

W1 itself cannot call, waive, weaken, or replace those gates.

## Preregistered W1 attacks

1. valid request is deterministic/digest-bound and leaves product bytes untouched;
2. draft/tampered contract cannot create request;
3. non-ready Doctor cannot create request;
4. missing/corrupt F6 anchor authority cannot create request;
5. valid scoped patch + valid trace -> `PROPOSAL_ACCEPTED` only;
6. provider trace containing `PASS`/`DONE` still has `completion_authority: none` and creates no F4/final evidence;
7. malformed patch is rejected;
8. out-of-scope patch is rejected;
9. frozen-forbidden path patch is rejected;
10. `.forge/**` patch is rejected regardless of contract prose;
11. escaping tracked symlink proposal is rejected;
12. patch/trace source symlink is rejected;
13. oversize patch/trace is rejected;
14. malformed/non-contiguous/oversize trace schema is rejected;
15. baseline movement after request makes submission/verification stale and refused;
16. contract amendment/tamper after request makes submission/verification stale and refused;
17. request byte tamper is detected;
18. stored patch/trace/proposal byte tamper is detected by `proposal verify`;
19. second request/submission cannot overwrite evidence;
20. accepted stored patch can be handed explicitly to Foundation F4 and reaches `CANDIDATE_VERIFIED` for the known-good fixture, proving compatibility without granting W1 completion authority;
21. CLI still contains no autonomous builder execution, merge, deploy, swarm or provider-specific command;
22. complete Foundation Gate and F1–F6 predecessor regressions remain green.

## Terminal gate

W1 receives `PASS` only if:

- its complete attack suite passes;
- Foundation Gate integrated attacks remain green under the new proposal namespace;
- F1–F6 predecessor replay remains green;
- product/operator state does not change during request/submission/verification;
- temporary validation infrastructure is removed before merge;
- post-test runtime/test identity is proven;
- final GitHub merge tree equals the reviewed candidate tree.

## Non-goals

W1 does not:

- execute Codex, Claude, local models, or any provider;
- choose a provider/model;
- grant shell/network/credential access to an agent;
- autonomously implement code;
- run trusted acceptance/final-evaluator gates on behalf of a builder;
- decide PASS;
- amend contracts;
- merge or deploy;
- retry/replan;
- manage a task queue;
- provide project-management autonomy.

## Authorization on PASS

W1 `PASS` may authorize exactly the next bounded Walls unit chosen after W1 evidence is complete. A Codex-specific adapter is not automatically authorized merely because W1 exists; its provider/execution containment contract must be frozen separately.
