# F5 Failure 001 — Baseline/Acceptance Phase Conflation

**F5 state:** `REPAIR_REQUIRED`  
**Attack/control:** `F5-A00` known-good positive control  
**Date:** 2026-08-12

## Locked expectation

A runnable baseline that does not yet implement `safe_divide` must be eligible for a known-good patch. The post-change acceptance checker is expected to fail before implementation and pass after the good patch.

## Observed result

Current Forge returned:

```text
Doctor: PROJECT_BASELINE_FAILURE
implementation_environment_ready: false
required acceptance check exit: 21

forge unit run:
FORGE_ERROR: Doctor prerequisite not ready: PROJECT_BASELINE_FAILURE
```

The known-good patch was never applied or evaluated.

## Diagnosis

F2 currently has one undifferentiated `required` check class. F3 Doctor executes every required check and requires it to pass on the pre-change baseline. F4 also executes every required check after the patch.

That means a contract cannot naturally express both:

1. checks proving the repository/environment is runnable before implementation; and
2. acceptance checks proving behavior that is intentionally absent before implementation.

This makes genuine feature addition incompatible with the current Doctor gate unless the new-behavior check already passes before the change.

## Verdict

This is a lower-layer model defect, not a failed good patch.

F5 stops at A00 under the preregistered first-unmet-requirement rule. A01-A11 remain unexecuted.

## Required repair

Introduce a digest-bound check phase/role that distinguishes pre-implementation checks from final acceptance checks.

Minimum semantics:

- preflight-required checks must pass Doctor before implementation;
- acceptance-only required checks are not run by Doctor;
- all required checks run after the patch in F4;
- success criteria must be backed by final required acceptance evidence;
- the phase/role must be frozen inside F2 authority and cannot be silently changed;
- all previous F1-F4 safety invariants must survive replay.
