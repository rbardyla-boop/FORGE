# FORGE Research V1 — Final Project State

**Status:** COMPLETE as a research prototype  
**Production status:** NOT PRODUCTION READY  
**Automatic merge/deploy authority:** NONE  
**Live/billable provider work required for closure:** NO

## Simple answer

FORGE produced something useful.

It is not a finished autonomous AI platform. It is a tested control-system prototype showing how an AI worker can be given useful freedom without automatically inheriting unrestricted authority.

The research produced three positive mechanisms and one important negative result.

## What works

### A0 — Learn more without gaining more power

An agent may receive additional read-only context during a run while its original action authority stays frozen.

Rule:

> Seal authority, not all knowledge.

### A1 — Track where sensitive action inputs came from

Untrusted information cannot become trusted merely because the worker repeats, combines, or relabels it.

A tool policy can require stronger provenance for sensitive parameters such as a recipient, destination, account, target, or command argument.

Rule:

> A tool allowlist is not enough. Sensitive parameters also need provenance rules.

### A2 — Human approval binds the exact action

Approval is bound to the canonical bytes of the actual action, not to an LLM-written summary.

Changing the target, payload, effect class, action identity, or bound authority after approval invalidates the approval.

Rule:

> Approve exact action bytes, not model prose.

## What failed — and why that is useful

### A3 — Generic exactly-once external effects

The hypothesis that exact approval plus a durable local log is enough to make arbitrary external effects exactly-once was falsified.

A process can:

```text
record intent
-> call remote system
-> remote effect happens
-> crash before local completion record
```

After restart, local state may not reveal whether the remote system actually performed the effect.

Blind retry can therefore duplicate a non-idempotent action.

The safe state for an ambiguous non-retryable action is:

```text
EFFECT_UNCERTAIN
```

A remote system that genuinely supports stable idempotency keys can instead be retried with the same action-derived key.

Rule:

> Do not infer remote completion from local intent, and do not infer safe retry merely from uncertainty.

## Final V1 architecture

```text
FROZEN ACTION AUTHORITY
        |
        v
PRE-AUTHORIZED DISCOVERY ENVELOPE
        |
        v
CONTENT-ADDRESSED READ GRANTS
        |
        v
PROVENANCE-AWARE PARAMETER COMPOSITION
        |
        v
CANONICAL ACTION MANIFEST
        |
        v
EXACT HUMAN APPROVAL
        |
        v
DURABLE EFFECT INTENT
        |
        v
REPLAY / RECOVERY POLICY
        |
        +--> IDEMPOTENCY_KEYED -> retry same stable key
        |
        +--> NON_RETRYABLE -> EFFECT_UNCERTAIN after ambiguous crash
        |
        v
EXTERNAL EFFECT
```

## Important architectural correction

Authorization and recovery are separate questions.

A future effect contract should contain both an effect classification and replay semantics, for example:

```yaml
effect_class: EXTERNAL_MUTATION
replay_semantics: IDEMPOTENCY_KEYED
```

or:

```yaml
effect_class: EXTERNAL_MUTATION
replay_semantics: NON_RETRYABLE
```

Potential future classes such as `IDEMPOTENT` and `RECONCILABLE` were not proven by V1 and must not be claimed as tested results.

## What FORGE V1 is

FORGE V1 is evidence that these control mechanisms can be implemented and mechanically attacked in a small deterministic harness.

It is useful as:

- an agent-governance research prototype;
- a reference architecture for bounded AI workers;
- a testbed for authority, provenance, approval, and recovery semantics;
- source material for a future production runtime.

## What FORGE V1 is not

V1 does not claim:

- universal prompt-injection resistance;
- safe arbitrary Internet access;
- production identity/key custody;
- production exactly-once semantics;
- persistent trusted memory across runs;
- safe autonomous merge or deployment;
- autonomous completion authority;
- proof that every external tool can be safely reconciled.

## Project closure

The authority-lifecycle research project ends at A0–A3.

A0 = `RESEARCH_PASS`  
A1 = `RESEARCH_PASS`  
A2 = `RESEARCH_PASS`  
A3 = `RESEARCH_NEGATIVE_RESULT`

The negative A3 result is part of the success of the research because it removed a false architectural assumption.

```text
FORGE AUTHORITY-LIFECYCLE RESEARCH V1 = COMPLETE
NET RESULT = USEFUL PROTOTYPE + ARCHITECTURAL CORRECTION
PRODUCTION READY = NO
NOTHING FOUND = FALSE
```

Persistent-memory promotion or further agent work is a separate future project, not unfinished V1 work.

## Repository handling after closure

To keep GitHub activity low-noise:

- do not create more V1 research branches, issues, PRs, tags, or automated comments;
- do not perform live/billable Codex work merely to make V1 appear more complete;
- do not automatically continue to A4;
- preserve the merged A0–A3 code, tests, verdicts, and this final record as the V1 evidence package;
- any new work begins only as an explicitly chosen new project.
