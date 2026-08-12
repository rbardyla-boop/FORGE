# FORGE-F4 Contract

**Unit:** FORGE-F4
**Authorized by:** FORGE-F3 PASS
**Scope:** one manual implementation attempt only

## Objective

Bind one frozen F2 contract and one F3 Doctor-ready committed baseline to one manually supplied patch, execute that attempt only in a disposable Git worktree, and persist exact base/diff/check evidence plus a harness-owned terminal state without allowing the patch author/worker to declare completion.

## Authorized command

F4 adds exactly:

- `forge unit run UNIT --patch PATCH_FILE`

No retry, AI builder, merge, deploy, or autonomous planning command is authorized.

`forge build` remains unauthorized.

## Prerequisites

Before an implementation attempt may begin:

1. `UNIT` must resolve to a complete `FROZEN`, digest-valid F2 contract with valid amendment history;
2. `forge doctor UNIT` against the current committed `HEAD` must return `ENVIRONMENT_READY`;
3. the operator tracked worktree/index must therefore be clean under the F3 boundary;
4. `PATCH_FILE` must be a real regular file, not a symlink, and must not exceed 1 MiB;
5. no F4 attempt may already exist for `UNIT`.

If a prerequisite fails, no implementation attempt is created and no F4 terminal PASS may exist.

## One-attempt rule

F4 v0.1 authorizes exactly one persisted attempt per unit:

- `.forge/runs/<UNIT>/attempt-0001/`

The attempt directory may never be overwritten or silently reused. Retry/replan semantics belong to later units.

## Disposable implementation boundary

F4 must never apply the patch in the operator working tree.

It must:

1. bind the exact Doctor-ready baseline commit;
2. create a detached disposable Git worktree at that commit;
3. verify the patch with `git apply --check --whitespace=error-all`;
4. apply the patch to the disposable index/worktree with `git apply --index --whitespace=error-all`;
5. derive actual changed paths from Git after application rather than trusting patch prose;
6. reject any changed path outside `scope.allowed_paths`, matching `scope.forbidden_paths`, or under `.forge`;
7. reject an attempt that produces no actual tracked/index diff;
8. freeze the exact applied staged diff before checks execute;
9. execute only frozen required checks with `shell=False` in contract order;
10. reject a patched tree containing a tracked symlink that resolves outside the disposable worktree before checks execute;
11. after every required check, require the exact staged diff to remain byte-identical to the frozen applied diff and require zero unstaged tracked diff;
12. remove the disposable worktree before persisting the final attempt evidence;
13. re-verify that the frozen contract digest/revision still match the attempt authority;
14. prove the operator Git status/worktree registry is unchanged except for Forge-owned evidence under `.forge`.

F4 does not install dependencies or rewrite the patch.

## Scope matching

Changed paths are canonical relative POSIX paths derived from Git.

A path is authorized only when:

- it matches at least one `scope.allowed_paths` pattern;
- it matches no `scope.forbidden_paths` pattern;
- it is not `.forge` and does not live under `.forge/`.

F4 scope evaluation is against actual post-apply changed paths, including both sides of a rename when Git reports one.

Scope patterns are anchored against the entire canonical relative POSIX path: `*` and `?` never cross `/`, while `**` may cross directory boundaries. Thus `root/*.txt` does not authorize `root/sub/x.txt`; `root/**` does.

## Check semantics

Only `required: true` checks have completion authority.

Required checks execute against the patched disposable worktree using the same explicit external-blocker protocol as F3:

- exit `0` -> check PASS;
- exit `75` plus stderr line beginning `FORGE_BLOCKED_EXTERNAL:` -> external blocker;
- other non-zero -> implementation/check failure;
- executable missing, timeout, tracked/index mutation, or execution infrastructure failure -> verification failure.

Advisory checks are not executed in F4 v0.1.

## Harness-owned terminal states

The worker/patch has no field, flag, output string, comment, commit message, or prose channel that can select the terminal state.

F4 computes exactly one terminal state after an implementation attempt begins:

### `PASS`

Only when:

- patch applies cleanly;
- actual changed paths satisfy frozen scope;
- a non-empty applied diff is frozen;
- every required check exits `0`;
- the patched tree contains no tracked symlink escaping the disposable worktree;
- checks leave the exact staged diff byte-identical to the frozen patch and leave no unstaged tracked diff;
- the frozen contract remains digest/revision-valid through final evidence construction;
- disposable cleanup and operator postconditions pass;
- evidence is persisted successfully.

### `REPAIR_REQUIRED`

For a bounded implementation failure including patch-apply failure, scope violation, empty diff, ordinary required-check failure, timeout/missing executable/verification inability, or tracked/index mutation.

### `BLOCKED_EXTERNAL`

Only when a required check uses the exact F3 external-blocker protocol.

`PASS_WITH_DISCLOSED_LIMITS`, `SEALED_NEGATIVE_RESULT`, and `ABANDONED_BY_OWNER` are not selectable by the F4 command path.

## Evidence package

A started F4 attempt must persist:

```text
.forge/runs/<UNIT>/attempt-0001/
├── EVIDENCE.json
└── APPLIED.diff
```

`EVIDENCE.json` must contain at minimum:

- schema;
- unit ID;
- contract digest and revision;
- baseline commit;
- input patch SHA-256 and byte length;
- applied diff SHA-256 and byte length when available;
- actual changed paths;
- required-check results in contract order;
- skipped advisory check IDs;
- terminal state;
- stable reason code;
- operator status/worktree postcondition booleans;
- contract postcondition boolean;
- `completion_authority: harness`.

`APPLIED.diff` must be the exact Git-produced staged diff that was evaluated. If patch application/scope fails before a trustworthy applied diff exists, `APPLIED.diff` may be absent and evidence must say so explicitly.

No timestamp, random run ID, conversation transcript, worker confidence, or model reasoning is required.

## Evidence integrity

The applied diff SHA-256 is computed from the exact bytes written to `APPLIED.diff`.

Evidence persistence itself occurs only under `.forge/runs/` after the disposable execution boundary is closed. F4 never writes evidence into product paths.

## Acceptance criteria

F4 passes only if tests prove all of the following:

1. green manual patch -> harness terminal `PASS`;
2. `PASS` evidence binds exact contract digest, baseline commit, input patch hash, applied diff hash, changed paths, and required-check results;
3. operator product files are byte-identical before/after F4;
4. disposable worktree is removed and worktree registry is restored;
5. DRAFT/tampered contract blocks before attempt creation;
6. non-ready Doctor baseline blocks before attempt creation;
7. malformed/non-applicable patch -> `REPAIR_REQUIRED`;
8. out-of-scope changed path -> `REPAIR_REQUIRED`;
9. forbidden-path changed path -> `REPAIR_REQUIRED`;
10. ordinary required-check failure -> `REPAIR_REQUIRED`;
11. explicit external blocker -> `BLOCKED_EXTERNAL`;
12. missing executable or timeout -> `REPAIR_REQUIRED` with verification reason;
13. required check mutating tracked/index state beyond the patch -> `REPAIR_REQUIRED`;
14. no-diff patch -> `REPAIR_REQUIRED`;
15. second attempt for the same unit is refused without overwriting evidence;
16. worker/patch text claiming `PASS` cannot affect terminal state;
17. advisory checks are skipped and cannot create PASS evidence;
18. all F3 regressions remain green;
19. all repaired F2 regressions remain green;
20. all F1 regressions remain green;
21. `forge build` remains unauthorized;
22. a checker that rewrites and re-stages an already patched path is rejected because the exact staged diff changed even if coarse Git status is unchanged;
23. a patch that introduces a tracked symlink resolving outside the disposable worktree is rejected before required checks execute;
24. anchored scope globs do not let `*` cross directory boundaries;
25. contract digest/revision changes during an attempt force `REPAIR_REQUIRED` rather than PASS.

## Non-goals

F4 does not:

- create or improve a patch;
- run an AI model;
- decide what unit should come next;
- retry failed work;
- merge or deploy;
- prove the test suite is sufficient;
- defend against deliberately malicious contract-authored commands beyond the F3/F4 disposable boundaries;
- run the full F5 planted-defect false-completion attack programme.

## Terminal states for this unit

- `PASS`
- `REPAIR_REQUIRED`
- `BLOCKED_EXTERNAL`
- `ABANDONED_BY_OWNER`

## Next-unit boundary

F4 PASS may authorize exactly:

> **FORGE-F5 — False-Completion Attack Harness: preregister known-good and deliberately defective implementations, then prove the contract -> Doctor -> one-unit -> verify -> gate path accepts the good control and rejects the bad controls, including test deletion/weakening, normal-behavior regression, scope escape, stale artifact verification, and worker false-completion claims.**

F4 does not authorize an AI builder.


## Amendment F4-A1 — exact patched-state, symlink, scope-glob, and contract postconditions

**Reason:** post-implementation review found four ways a coarse lifecycle gate could overstate confidence: a checker could re-stage different bytes on an already-changed path while coarse status still looked equivalent; a manual patch could introduce an escaping tracked symlink after F3 had validated only the baseline; ambiguous glob semantics could widen scope across directories; and `.forge` contract authority could change while the disposable attempt was running.

**Added requirements:**

- compare the exact staged Git diff after every required check to the pre-check frozen applied diff;
- require zero unstaged tracked diff after every required check;
- re-run tracked symlink containment after patch application and before checks;
- use anchored relative-POSIX glob semantics where `*`/`?` do not cross `/` and `**` may;
- re-verify the original contract revision/digest after disposable cleanup and before evidence persistence;
- record the contract postcondition in `EVIDENCE.json`.

This amendment strengthens the F4 false-completion boundary. It does not authorize a new command, retry, AI worker, merge, or deployment behavior.
