# FORGE-F3 Contract

**Unit:** FORGE-F3
**Authorized by:** FORGE-F2 PASS + F2 Repair 001 PASS
**Scope:** environment readiness only

## Objective

Before any implementation is allowed, prove that the frozen contract's required verification commands are runnable against the untouched committed repository baseline, without modifying the operator's working tree, and classify non-ready conditions without pretending they are implementation failures.

## Authorized command

F3 adds exactly one top-level command:

- `forge doctor UNIT`

`forge build` remains unauthorized.

## Prerequisite authority

Doctor may run only when `UNIT` resolves to a complete, `FROZEN`, digest-valid F2 contract whose amendment chain verifies.

A DRAFT, missing, tampered, or history-invalid contract blocks Doctor before any project check executes.

## Baseline rule

F3 defines the pre-implementation baseline as the current committed Git `HEAD` of the repository.

Required contract checks are therefore required to be **green on the untouched baseline before implementation begins**. Feature-specific tests added later must enter through the same already-green runner rather than changing the frozen runner command after implementation starts.

Support for deliberately red pre-implementation acceptance commands is outside F3 v0.1.

## Disposable execution boundary

Doctor must not execute required checks in the operator's working tree.

It must:

1. require the invocation directory to be the Git repository root;
2. require no tracked working-tree/index changes before Doctor starts;
3. identify the exact baseline `HEAD` commit;
4. create a detached disposable Git worktree at that exact commit;
5. execute required checks there with `shell=False`;
6. detect any tracked-file mutation caused by a check inside the disposable baseline;
7. remove the disposable worktree before returning;
8. leave the operator working tree/status unchanged.

Untracked files in the operator working tree do not enter the disposable baseline and do not affect the baseline claim.

## Check scope

Doctor executes only checks with `required: true`.

Advisory checks are reported as skipped and have no F3 authority.

Each required command is executed exactly as the frozen argv array declares it, from the disposable repository root.

F3 does not use a shell, does not rewrite argv, and does not install missing dependencies.

## Classification vocabulary

Doctor returns exactly one overall classification.

### `ENVIRONMENT_READY`

Every required check:

- launched successfully;
- completed within the fixed Doctor timeout;
- exited `0`;
- left the disposable tracked baseline unchanged.

Exit code: `0`.

### `PROJECT_BASELINE_FAILURE`

Forge could launch the required check, but the untouched committed project baseline returned a non-zero result that was not the explicit external-blocker protocol.

This means the repository is not green under its own frozen required gate. Implementation is not authorized.

Exit code: `3`.

### `FORGE_CANNOT_VERIFY`

Forge cannot establish a trustworthy baseline verdict, including:

- Git unavailable;
- invocation is not the repository root;
- no committed `HEAD` exists;
- tracked operator worktree/index is dirty;
- disposable worktree creation fails;
- required executable cannot be launched;
- required check times out;
- required check mutates tracked baseline files;
- disposable worktree cleanup fails.

This is not represented as a project failure.

Exit code: `4`.

### `BLOCKED_EXTERNAL`

A required check explicitly reports a genuine temporary external dependency using both:

- process exit code `75` (`EX_TEMPFAIL` convention); and
- a stderr line beginning exactly `FORGE_BLOCKED_EXTERNAL:`.

Doctor does not guess that arbitrary failures are external.

Exit code: `5`.

## Classification precedence

When multiple required checks produce different non-ready conditions, overall precedence is:

1. `FORGE_CANNOT_VERIFY`;
2. `BLOCKED_EXTERNAL`;
3. `PROJECT_BASELINE_FAILURE`;
4. `ENVIRONMENT_READY`.

Doctor may run all required checks while the disposable baseline remains trustworthy. A tracked-baseline mutation ends check execution immediately because later results would no longer describe the same baseline.

## Report

Doctor emits one JSON report to stdout. It is diagnostic evidence, not a persisted authority record in F3.

The report contains at minimum:

- `unit_id`;
- `contract_digest`;
- `baseline_commit` when known;
- `workspace_mode: detached_git_worktree` when created;
- overall `classification`;
- `implementation_environment_ready` boolean;
- required-check results in contract order;
- advisory check IDs skipped;
- stable reason codes for preflight/cleanup failures.

Per-check results include:

- check ID;
- argv;
- classification;
- exit code when available;
- bounded stdout/stderr;
- stable reason code;
- whether tracked baseline mutation was detected.

No timestamp, random run ID, conversation text, or model reasoning is required for the F3 report.

## Timeout

F3 uses a fixed required-check timeout of 30 seconds per check.

The internal Doctor function may accept a shorter timeout only for deterministic unit testing of the timeout path; the CLI always uses the frozen 30-second value.

## Acceptance criteria

F3 passes only if tests prove all of the following:

1. valid frozen contract + green required baseline -> `ENVIRONMENT_READY` / exit `0`;
2. DRAFT contract -> Doctor blocks before executing checks;
3. tampered frozen contract -> Doctor blocks before executing checks;
4. non-Git directory -> `FORGE_CANNOT_VERIFY`;
5. invocation below repository root -> `FORGE_CANNOT_VERIFY`;
6. dirty tracked operator baseline -> `FORGE_CANNOT_VERIFY` without executing checks;
7. missing required executable -> `FORGE_CANNOT_VERIFY`;
8. required-check timeout -> `FORGE_CANNOT_VERIFY`;
9. required check that mutates a tracked file -> `FORGE_CANNOT_VERIFY` and original working tree remains unchanged;
10. ordinary required non-zero -> `PROJECT_BASELINE_FAILURE`;
11. exit `75` without the exact external prefix -> `PROJECT_BASELINE_FAILURE`;
12. exit `75` + exact external prefix -> `BLOCKED_EXTERNAL`;
13. failing advisory check is not executed and cannot block readiness;
14. multiple-check classification obeys frozen precedence;
15. Doctor output binds the exact F2 contract digest and Git baseline commit;
16. disposable worktree is removed and original Git status is byte-identical before/after Doctor;
17. no source/product file is modified by Forge Doctor;
18. all permanent F1 state regressions remain green;
19. all permanent repaired-F2 contract regressions remain green;
20. predecessor F1/F2 regression files remain byte-identical while bare `forge doctor` continues to fail closed with an `invalid choice` diagnostic;
21. `forge build` remains unauthorized.
22. a tracked symlink that resolves outside the disposable worktree is rejected before checks execute, while an internal tracked symlink remains usable;
23. check stdout/stderr is bounded and the check process receives `PWD` for the disposable worktree rather than the operator working tree.

## Non-goals

F3 does not:

- install dependencies;
- repair a broken repository;
- create feature-specific tests;
- run an AI model;
- build or modify product code;
- verify that a future patch is correct;
- persist a release verdict;
- treat advisory checks as completion evidence;
- sandbox a malicious operator-authored check command;
- infer external blockers from error prose alone.

The check argv is frozen operator authority in F3; hostile/untrusted check commands are outside this unit.

## Terminal states

- `PASS`
- `REPAIR_REQUIRED`
- `BLOCKED_EXTERNAL`
- `ABANDONED_BY_OWNER`

## Next-unit boundary

F3 PASS may authorize exactly:

> **FORGE-F4 — One-Unit Lifecycle: bind one frozen contract and one Doctor-ready baseline into an implementation attempt, then record the exact base/diff/check evidence and terminal state without allowing the worker to declare completion.**

F3 does not authorize an AI builder. F4 may use a manually supplied patch/fixture as the implementation input.

## Clarification F3-C1 — successor compatibility without predecessor-test edits

F1 and F2 were intentionally built before Doctor and included assertions that a bare `forge doctor` invocation was invalid. F3 preserves those regression files byte-for-byte rather than retiring them.

The F3 command therefore has one valid form only:

- `forge doctor UNIT` — authorized F3 invocation;
- bare `forge doctor` — fail closed with an `invalid choice` diagnostic;
- `forge build` — remains unauthorized.

All F1 state-integrity and repaired-F2 contract-integrity tests remain unchanged. This is stronger than the initially planned phase-bound test retirement and reduces the F3 change surface.

## Amendment F3-A1 — symlink escape and inherited working-directory boundary

**Reason:** implementation review identified two ways a check could accidentally escape the intended disposable baseline without directly editing ordinary tracked files: a committed symlink resolving outside the detached worktree, and an inherited `PWD`/Git environment pointing back at the operator context.

**Added requirements:**

- inspect Git-indexed symlinks before any required check executes;
- reject a tracked symlink that materializes incorrectly or resolves outside the disposable worktree;
- allow tracked symlinks whose resolved target remains inside the disposable worktree;
- set `PWD` to the disposable worktree for check processes;
- remove inherited `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, and `GIT_COMMON_DIR` from the check environment;
- keep stdout/stderr bounded to the declared report limit.

This amendment expands the safety checks. It does not weaken any F3 criterion or authorize new product behavior.
