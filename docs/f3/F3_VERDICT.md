# FORGE-F3 Verdict

**Verdict:** `PASS`

## Claim under test

Before implementation begins, Forge can prove that a frozen contract's required verification commands are runnable against the untouched committed repository baseline in a disposable Git worktree, without modifying the operator working tree, and can distinguish project baseline failure, explicit external blocking, and Forge verification incapability.

## Implemented surface

- `forge_core/doctor.py`;
- `forge doctor UNIT` in `forge_core/cli.py`;
- F2 public `verify_contract` reuse with verify/read/re-verify binding;
- `tests/test_f3.py`;
- predecessor F1/F2 test files remain byte-identical; bare `forge doctor` still fails closed while `forge doctor UNIT` is authorized.

No product-code modification path, AI model, dependency installer, patch builder, merge authority, or deployment authority is introduced.

## Doctor execution boundary

Doctor:

1. requires a complete frozen F2 contract and verified amendment chain;
2. requires invocation at the Git repository root;
3. rejects a dirty tracked operator baseline;
4. binds the exact committed `HEAD`;
5. creates a detached disposable Git worktree at that commit;
6. rejects tracked symlinks that escape that disposable worktree;
7. executes only frozen `required: true` checks with `shell=False`;
8. strips inherited Git path overrides and sets check `PWD` to the disposable worktree;
9. bounds captured stdout/stderr;
10. rejects tracked baseline mutation;
11. removes the disposable worktree;
12. proves operator Git status and worktree registry are unchanged before returning.

## Classification proven

Doctor emits exactly one of:

- `ENVIRONMENT_READY` — exit `0`;
- `PROJECT_BASELINE_FAILURE` — exit `3`;
- `FORGE_CANNOT_VERIFY` — exit `4`;
- `BLOCKED_EXTERNAL` — exit `5`.

An external blocker is accepted only through the frozen explicit protocol: exit `75` plus a stderr line beginning `FORGE_BLOCKED_EXTERNAL:`. Ordinary exit `75` remains a project baseline failure.

Precedence is:

`FORGE_CANNOT_VERIFY` > `BLOCKED_EXTERNAL` > `PROJECT_BASELINE_FAILURE` > `ENVIRONMENT_READY`.

## Test result

The amended F3 suite was replayed in bounded groups after a monolithic subprocess-heavy run hit the execution window. No timeout was counted as a pass.

Final terminal results:

- F3: **20/20 PASS**;
- repaired F2: **14/14 PASS**;
- F1: **11/11 PASS**.

The F3 cases include:

- green frozen baseline;
- draft and tampered contract rejection;
- non-Git and wrong-root rejection;
- dirty tracked baseline rejection before checks execute;
- missing executable;
- check timeout;
- tracked-file mutation;
- ordinary non-zero;
- explicit vs false external-blocker classification;
- advisory-check non-authority;
- escaping tracked symlink rejection;
- valid internal symlink use;
- bounded stdout/stderr and disposable `PWD`;
- classification precedence;
- bare `forge doctor` predecessor compatibility;
- `forge build` remaining unauthorized.

## Defect-prevention work completed before PASS

### F2 Repair 001

F3 design discovered that F2's documented portability rule was stronger than its argv enforcement. Absolute POSIX/Windows paths and flag-embedded absolute paths are now rejected and permanently covered by F2 regression tests before F3 proceeds.

### F3 Amendment A1

F3 implementation review identified disposable-workspace escape risk through committed external symlinks and inherited Git working-directory variables. F3-A1 added fail-closed symlink inspection, sanitized Git path environment, explicit disposable `PWD`, and bounded output before F3 was terminalized.

## Non-claims

F3 does not prove:

- that a future implementation patch is correct;
- that a check suite fully captures desired behavior;
- that check commands are safe when the operator deliberately authorizes hostile commands;
- that dependencies can be installed automatically;
- that Forge can repair a red project;
- that an AI builder is reliable;
- that a green baseline implies a future patch should pass.

F3 proves environment/baseline readiness only.

## Authorization

F3 PASS authorizes exactly:

> **FORGE-F4 — One-Unit Lifecycle: bind one frozen contract and one Doctor-ready baseline into a single implementation attempt, record the exact base/diff/check evidence and terminal state, and ensure the worker cannot declare completion.**

F4 may use only a manually supplied patch/fixture as implementation input. It does not authorize an AI builder, autonomous coding, merge, or deployment.
