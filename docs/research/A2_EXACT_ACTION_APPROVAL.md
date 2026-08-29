# FORGE Research A2 — Exact-Action Approval Binding

**Track:** research-only / non-authorizing  
**Predecessor evidence:** A0 and A1 research verdicts  
**External effects:** none  
**W4/W5 authority:** unchanged

## Question

Can a trusted approval authority authorize one exact canonical action while making later substitution, mutation, expiry, signer substitution and token replay mechanically detectable?

A2 tests:

> **Approve bytes, not prose.**
>
> Human-facing presentation is deterministically derived from the same canonical action manifest whose digest is signed. The worker cannot supply the approval summary, cannot alter action arguments after approval, and cannot transform a valid approval for one action into approval for another.

A2 does not perform the approved action.

## Trusted boundary

The research signer is represented by a trusted HMAC key held outside worker-controlled proposal data. HMAC is used here only to test exact binding and replay semantics; A2 does not prescribe production human-identity or key-management technology.

The worker is assumed able to see the action manifest and approval token but not the signing key.

## Canonical action manifest

A manifest may be compiled only from an A1 evaluation whose state is `ACTION_AUTHORIZED`.

It binds:

- action ID;
- effect class;
- exact normalized argument names and UTF-8 values;
- context-envelope digest;
- source-policy digest;
- action-template digest;
- action-proposal digest;
- manifest digest.

The compiler independently hashes each supplied argument and requires it to equal the corresponding A1 `value_sha256`. Therefore worker-supplied execution arguments cannot silently diverge from the values whose provenance A1 evaluated.

## Approval token

The trusted signer binds:

- exact manifest digest;
- signer identity;
- nonce;
- issued-at epoch second;
- expires-at epoch second;
- HMAC-SHA256 signature.

Validation requires:

- exact token schema;
- exact recomputed manifest digest;
- allowed signer;
- non-empty bounded nonce;
- issue/expiry sanity;
- current time inside the validity interval;
- constant-time valid signature;
- nonce not already consumed by the supplied replay guard.

Consumption marks the nonce spent in the research replay guard.

A3 will test why an in-memory/local replay guard is not sufficient to prove exactly-once external effects across crashes.

## Approval presentation

A2 exposes only deterministic presentation generated from the manifest:

```text
action
 effect class
 exact parameters
 manifest digest
```

No worker/LLM-written explanation is an authorization input.

## Frozen attack set

```text
A2-00 exact manifest can be approved and validated
A2-01 recipient/target substitution after approval rejected
A2-02 payload substitution after approval rejected
A2-03 effect-class mutation rejected
A2-04 context/policy/template/proposal digest mutation rejected
A2-05 denied A1 evaluation cannot become an approvable manifest
A2-06 execution arguments must hash to A1-evaluated values
A2-07 extra/missing action arguments rejected
A2-08 wrong signing key rejected
A2-09 signature bit mutation rejected
A2-10 signer substitution rejected
A2-11 unapproved signer rejected
A2-12 expired token rejected
A2-13 not-yet-valid/future token rejected
A2-14 malformed/empty nonce rejected
A2-15 token manifest-digest substitution rejected
A2-16 first consumption succeeds
A2-17 second consumption of same nonce rejected
A2-18 approval for action A cannot approve action B
A2-19 deterministic presentation comes only from manifest fields
A2-20 canonical key ordering does not change manifest identity
A2-21 visually similar but byte-distinct Unicode argument changes digest
A2-22 approval token has no execution/completion authority field
```

## Evidence boundary

A2 can establish exact local approval binding. It cannot establish:

- that a human understood the action;
- that an approval UI is free from visual deception outside the deterministic fields;
- secure production identity/key custody;
- exactly-once remote effects;
- safe retry after a crash;
- W4 completion, W5 authorization, merge or deployment.

## Expected successor pressure test

A3 will deliberately create this sequence:

```text
approval valid
→ local journal says attempt started
→ remote effect occurs
→ process crashes before local commit
```

The test asks whether a purely local system can know on restart whether retrying is safe.
