# FORGE-F2 Contract

**Unit:** FORGE-F2  
**Authorized by:** FORGE-F1 PASS  
**Scope:** contract authority only

## Objective

Define one machine-readable work-unit contract, freeze the parts that define success and scope to a stable SHA-256 digest, and prove that a unit cannot become implementation-eligible when the contract is absent, draft, corrupt, silently edited, or replaced without an explicit amendment chain.

## Allowed implementation surface

- `forge_core/contract.py`
- `forge_core/cli.py`
- `tests/test_f2.py`
- `docs/f2/F2_CONTRACT.md`
- `docs/f2/F2_VERDICT.md` after verification
- `README.md` construction-state update after PASS

F1 files may be changed only where required to expose F2 contract commands. F1 state semantics and its 11 regression tests must continue to pass unchanged.

## Authorized command surface

F2 adds one command group:

- `forge contract create UNIT --file AUTHORITY.json`
- `forge contract freeze UNIT`
- `forge contract verify UNIT`
- `forge contract ready UNIT`
- `forge contract amend UNIT --file AUTHORITY.json --reason REASON`

No implementation/build command is authorized.

## Authority fields

The authority JSON supplied to `create` / `amend` must contain exactly:

- `objective`
- `deliverables`
- `success_criteria`
- `scope.allowed_paths`
- `scope.forbidden_paths`
- `checks`
- `terminal_states`
- `non_goals`
- `forbidden_actions`

The frozen contract digest must bind all of those fields plus:

- unit ID;
- revision;
- frozen state;
- parent digest;
- amendment reason.

## Canonical contract storage

- current contract: `.forge/contracts/<UNIT>.json`
- archived revision: `.forge/contracts/history/<UNIT>/revision-NNNN.json`

No timestamp, random identifier, conversation text, or model reasoning is Forge-generated into the contract record. Structured path-bearing authority must remain machine-portable: scope paths are relative POSIX paths/patterns, and check argv may not contain direct or flag-embedded absolute filesystem paths. Operator-authored prose fields remain opaque text.

## Readiness rule

`forge contract ready UNIT` may exit 0 only when:

1. the current record exists;
2. the record is `FROZEN`;
3. its schema is valid;
4. its contract digest recomputes exactly;
5. the authority schema and cross-references remain valid.

A worker statement, README claim, or unchanged-looking diff has no authority to bypass this rule.

## Amendment rule

A frozen contract may change only through `forge contract amend`.

Amendment must:

1. verify the current frozen contract before mutation;
2. require a non-empty reason;
3. archive the exact prior frozen revision;
4. create the next revision as `DRAFT`;
5. bind the prior frozen digest as `parent_digest`;
6. block readiness until the new revision is explicitly frozen.

Silent editing of a frozen record must make `verify` and `ready` fail.

## Validation rules

- unit/check/criterion IDs are bounded safe identifiers;
- no absolute or `..` scope paths;
- `.forge` may never appear in `allowed_paths`;
- check commands are argv arrays, never shell command strings;
- check argv tokens may not contain POSIX/Windows absolute filesystem paths, including `--flag=/absolute/path` forms;
- check IDs are unique;
- criterion IDs are unique;
- each success criterion references existing **required** checks;
- terminal states come only from the frozen F0 vocabulary;
- `PASS` and at least one failure terminal must be declared.

## Acceptance criteria

F2 passes only if all of the following survive tests:

1. valid authority -> DRAFT contract;
2. DRAFT -> not ready;
3. freeze -> stable digest;
4. second freeze -> byte-stable/idempotent;
5. verify -> PASS only for unchanged frozen record;
6. ready -> PASS only for unchanged frozen record;
7. silent edit to objective -> FAIL;
8. silent edit to success criteria -> FAIL;
9. silent edit to allowed paths -> FAIL;
10. silent edit to checks -> FAIL;
11. silent edit to terminal states -> FAIL;
12. invalid/traversal unit IDs -> FAIL;
13. unsafe scope paths -> FAIL;
14. criterion reference to missing/advisory check -> FAIL;
15. amendment of valid frozen revision preserves prior revision and blocks readiness until re-freeze;
16. amendment of a tampered current record -> FAIL without mutation;
17. same authority/revision metadata -> same digest across separate projects;
18. all F1 regression tests remain green;
19. `forge doctor` and `forge build` remain absent.
20. POSIX, Windows, and flag-embedded absolute argv paths are rejected while relative argv paths remain valid.

## Non-goals

F2 does not:

- inspect whether commands are runnable;
- execute contract checks;
- inspect dependencies;
- modify product files;
- invoke an AI model;
- judge a patch;
- authorize merge/deploy;
- implement Doctor.

## Terminal states

- `PASS`
- `REPAIR_REQUIRED`
- `BLOCKED_EXTERNAL`
- `ABANDONED_BY_OWNER`

## Next-unit boundary

F2 PASS may authorize exactly **FORGE-F3 — Environment Doctor**.

## Clarification F2-C1 — amendment history is part of readiness evidence

For revision 2+, `verify` / `ready` must also replay the complete archived parent chain. Missing, symlinked, reordered, digest-invalid, or parent-mismatched history invalidates readiness. The current record's digest alone is insufficient proof of an explicit amendment chain.
