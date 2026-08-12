# FORGE-F2 Verdict

**Verdict:** `PASS`

## Claim under test

Forge can define one machine-readable unit contract, freeze its authority to a stable digest, deny implementation eligibility when the authority is draft/tampered/incomplete, and preserve explicit amendments as a verifiable parent chain.

## Implemented surface

- `forge_core/contract.py`;
- F2 `forge contract ...` command group in `forge_core/cli.py`;
- `tests/test_f2.py`;
- F2 contract and verdict documentation.

F1 `forge init` / `forge status` behavior is preserved.

## Frozen authority

A contract digest binds:

- unit ID;
- revision;
- frozen state;
- parent digest;
- amendment reason;
- objective;
- deliverables;
- success criteria;
- allowed/forbidden paths;
- check definitions and required/advisory status;
- terminal states;
- non-goals;
- forbidden actions.

Canonical encoding is deterministic JSON followed by SHA-256.

## Readiness rule proven

`forge contract ready UNIT` returns implementation eligibility only for a schema-valid, `FROZEN`, digest-valid contract whose complete amendment history also verifies.

The following fail closed:

- absent contract;
- DRAFT contract;
- objective edit after freeze;
- success-criterion edit after freeze;
- scope edit after freeze;
- check edit after freeze;
- terminal-state edit after freeze;
- unsafe unit/path values;
- success criterion referencing a missing or advisory check;
- tampered current contract;
- tampered archived parent;
- missing archived parent;
- amendment attempt on a tampered parent.

## Explicit amendment behavior

A valid amendment:

1. verifies the current frozen chain;
2. archives the exact current revision;
3. requires a non-empty reason;
4. creates revision N+1 as `DRAFT`;
5. binds the prior digest as `parent_digest`;
6. denies readiness until explicit re-freeze;
7. verifies the full parent chain on later `verify` / `ready` calls.

## Test result

- F2 deterministic tests: **12/12 PASS** across split replay groups;
- F1 regression tests: **11/11 PASS** after F2 changes;
- Python byte-compilation: **PASS**;
- `forge build`: **NOT AUTHORIZED / REJECTED**;
- `forge doctor`: **NOT AUTHORIZED / REJECTED**.

The F2 suite was split into bounded groups because a combined subprocess-heavy replay exceeded the execution window. No timeout was counted as a pass; every test was subsequently executed to terminal PASS in a bounded group.

## Non-claims

F2 does not prove:

- that declared check commands are installed or runnable;
- that a repository builds;
- that tests exercise real behavior;
- that a patch is correct;
- that an AI builder is reliable.

These remain outside F2.

## Authorization

F2 PASS authorizes exactly:

> **FORGE-F3 — Environment Doctor: before any implementation is allowed, prove that the target repository/runtime/check environment needed by a frozen contract is actually available and classify failures as project failure, Forge verification incapability, or external blocker.**

F3 does not authorize an AI builder or autonomous coding.
