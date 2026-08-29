# FORGE Product Brief

## One sentence

**FORGE is a deterministic authority layer for AI agents: models may propose and gather context, while non-model machinery decides what information may influence sensitive action parameters, what exact action a human approved, and whether retry is safe after failure.**

## The problem

Modern agent products increasingly give models browsers, terminals, persistent files, credentials, schedules, and application access. That makes the model useful, but it also creates a control problem:

**content and authority become easy to confuse.**

A webpage, email, retrieved document, model-generated summary, or another agent can influence the model. If the model is also the component deciding what it is allowed to do, then untrusted information can become operational authority through reasoning alone.

FORGE is built around a stricter rule:

> Information may influence reasoning without granting itself new authority.

## The product position

FORGE should not be presented as another autonomous worker, chatbot, or multi-agent framework.

Those products provide the visible worker.

FORGE is the layer underneath the worker that answers:

- What may this worker read?
- Which source classes may influence which action parameters?
- What exact action is being authorized?
- What did the human actually approve?
- What state must be durable before an external action begins?
- Is a retry safe after a crash?
- When remote completion cannot be known, can the system stop at honest uncertainty?

The useful mental model is:

```text
Agent runtime = capability
FORGE         = authority control
```

## The first public demonstration

The shortest credible demo is not a benchmark. It is one understandable failure case.

Scenario:

1. An agent is allowed to prepare a status notice.
2. A trusted source contains the legitimate recipient.
3. An untrusted source contains useful text plus an attacker-controlled recipient.
4. The agent attempts to use the untrusted recipient.
5. FORGE denies that parameter because `recipient` requires `VERIFIED` provenance.
6. The agent uses the same untrusted source in `body`, where `UNTRUSTED` provenance is permitted.
7. A canonical action manifest is produced.
8. A human approval is bound to that exact manifest.
9. A post-approval recipient mutation is rejected.
10. A simulated crash occurs after a non-retryable remote effect but before the local committed record.
11. FORGE returns `EFFECT_UNCERTAIN` and refuses an automatic duplicate retry.

Run it with:

```bash
python3 demo.py
```

This demo is intentionally local-only and uses no provider credential or real external service.

## What is differentiated

### 1. Tool permission is not enough

A tool allowlist can answer whether `send_notice` is callable.

FORGE asks whether each effect-sensitive argument was derived from provenance allowed for that parameter.

Example:

```text
recipient -> VERIFIED minimum
subject   -> VERIFIED minimum
body      -> UNTRUSTED permitted
```

An attacker-controlled document can therefore be quoted without being allowed to redirect the action.

### 2. Approval is for the action, not the explanation

A model-written approval summary can differ from the bytes eventually sent to a tool.

FORGE's research prototype derives the approval presentation from a canonical action manifest and binds the token to that manifest digest. Target or payload substitution after approval invalidates the binding.

### 3. Authorization and replay safety are different questions

A human approval answers:

> May this action happen?

A durable local journal can answer:

> Was an attempt recorded locally?

Neither necessarily answers:

> Did the external system perform the logical effect immediately before this process crashed?

That distinction produced the strongest negative result in V1. For non-retryable effects, an in-flight crash can require `EFFECT_UNCERTAIN` rather than automatic retry.

## What we can claim today

The repository has executable research mechanisms and adversarial tests for:

- bounded dynamic context grants;
- provenance-aware parameter composition;
- canonical exact-action approval binding;
- durable effect-intent journaling;
- fail-closed non-retryable crash recovery;
- idempotency-keyed recovery in the tested fixture.

The public demo composes the key V1 mechanisms into one local scenario.

## What we should not claim

Do not market FORGE as:

- AGI;
- a complete autonomous-agent product;
- a universal prompt-injection solution;
- a production-certified security boundary;
- a proof of exactly-once arbitrary remote execution;
- a novel distributed-systems impossibility theorem;
- a system in which hashes make untrusted data trustworthy.

The strongest credible claim is narrower and more useful:

**FORGE is a working research prototype for moving agent authorization out of the model and into explicit, deterministic control mechanisms.**

## Who would care

The likely users are teams building agents that can cause effects rather than teams building chat-only applications:

- coding agents with repository or deployment access;
- browser agents operating authenticated applications;
- internal enterprise agents using email, tickets, documents, or workflows;
- local/private agents with persistent personal data;
- agent orchestrators delegating work to lower-trust workers;
- systems where duplicate actions can be costly or dangerous.

## How to explain it publicly

Avoid starting with milestone names such as F0, F6, W2, or A3.

Start with the failure people already understand:

> Your AI worker reads an untrusted webpage. Why should that webpage be allowed to choose who receives an email, what repository gets changed, or where money gets sent?

Then show the demo.

Only afterward explain the machinery.

## Product path from here

The next valuable step is not another abstract FORGE research pass. It is one real consumer application with a small set of effectful tools and visible approval boundaries.

A good integration should make FORGE nearly invisible to the end user. The user should experience a useful agent; FORGE should provide the receipts, authority boundaries, provenance checks, and safe failure semantics underneath it.

That is the difference between a research control plane and a product people can immediately understand.
