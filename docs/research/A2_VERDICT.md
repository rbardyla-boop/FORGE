# FORGE Research A2 Verdict — Exact-Action Approval Binding

**Verdict:** `RESEARCH_PASS`  
**Track:** research-only / non-authorizing  
**Tested candidate:** `2d6ec09768fdbec2fac0d29b2c121a6bf7448ef9`  
**Successful lifecycle run:** `33252018097`  
**A2 unittest methods:** 20  
**W4 status changed:** no  
**W5 authorized:** no

## Result

The tested lifecycle candidate passed the A2 exact-action approval matrix together with complete A0 and A1 regression replay.

A2 establishes within the frozen local fixture that:

- only an A1 `ACTION_AUTHORIZED` evaluation can compile an approval manifest;
- execution arguments must hash to the exact bytes evaluated by A1;
- action ID, effect class, arguments, context-envelope digest, source-policy digest, template digest and proposal digest are all bound by the canonical manifest digest;
- approval presentation is deterministically derived from the same manifest rather than worker-written prose;
- the approval token binds the exact manifest digest, signer, nonce and validity interval;
- target/payload/effect/digest mutation after approval is rejected;
- wrong keys, signature mutation, signer substitution, expiry and future/not-yet-valid use are rejected;
- a consumed nonce cannot be consumed again by the research replay guard;
- an approval for action A cannot approve action B;
- visually similar but byte-distinct Unicode arguments produce different manifest identities;
- the approval token carries no execution or completion authority.

## Evidence boundary

A2 proves exact local binding only. It does not prove that a human correctly understood the action, that production identity/key custody is secure, or that a remote side effect is exactly-once across process/network failure.

The HMAC signer is a research fixture for binding semantics, not a production identity recommendation.

## Surviving rule

> Human approval must authorize the canonical effect manifest, not an LLM summary of that manifest.

The approval UI may explain the action, but authorization must be checked against the exact action bytes that will be executed.

## Next corridor

A3 tests the gap A2 intentionally leaves open: a valid exact approval can still be followed by a crash after the remote system performs the effect but before local state records completion.
