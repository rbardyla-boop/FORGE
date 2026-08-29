# FORGE Research A1 Verdict — Provenance-Aware Action Composition

**Verdict:** `RESEARCH_PASS`  
**Track:** research-only / non-authorizing  
**Tested candidate:** `790c5eb94b34bb998e5f052d23ec3c8e04669ca5`  
**Successful push run:** `33251798287`  
**W4 status changed:** no  
**W5 authorized:** no

## Result

The tested candidate passed:

- research-kernel compile gate;
- complete A0 regression: 18 unittest methods covering A00–A24;
- A1 provenance-composition gate: 23 unittest methods covering A1-00–A1-24;
- whitespace gate.

A1 demonstrates within the frozen local fixture that:

- lower-trust discovered material can be admitted into a parameter whose policy explicitly permits it;
- the same source cannot select a parameter requiring higher trust;
- worker text cannot create `CONTROL` trust;
- bytes identical to a frozen control constant remain `UNTRUSTED` when obtained from an untrusted grant;
- concatenating trusted and untrusted values produces the least-trusted source classification;
- ambiguous source classification fails closed;
- path rule selection, trust labels, effect class and parameter minimum trust are not worker-controlled proposal fields;
- content drift, policy/template tampering, raw values and unsupported provenance expressions fail closed;
- the evaluation report preserves source lineage and derived trust;
- `ACTION_AUTHORIZED` still carries `execution_authority: none`.

## Evidence boundary

This is parameter-provenance enforcement, not universal prompt-injection resistance and not a claim of novelty over existing information-flow/capability systems.

The fixture does not establish that an arbitrary low-sensitivity payload is semantically harmless. Real sinks still require sink-specific effect and parameter policies.

## Surviving control-system rule

> Authority policy must constrain not only which tool is callable, but which provenance classes may influence each effect-sensitive parameter of that call.

A tool allowlist alone cannot express this property.

## Next failure corridor

A1 says whether an action proposal is provenance-compatible. It does not solve what happens after a human approves a concrete effect.

The next research corridor is approval + execution recovery:

1. bind approval to exact canonical action bytes;
2. reject substitution, mutation, expiry and replay;
3. crash immediately after a simulated remote effect but before the local commit;
4. determine whether the system can distinguish "effect happened" from "effect did not happen" without relying on model judgment.

The expected pressure point is that a local append-only journal may preserve uncertainty without being able to eliminate it. This must be tested rather than assumed away.
