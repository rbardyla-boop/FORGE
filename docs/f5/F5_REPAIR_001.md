# F5 Repair 001 — Final Completion Authority Gate

**Triggered by:** `F5_FAILURE_002.md`
**Status:** `PASS`

F4 mechanical success is now `CANDIDATE_VERIFIED`, never final completion.

Final `PASS` belongs only to:

```text
forge gate run UNIT --evaluator EVALUATOR.py
```

The gate requires F4 `CANDIDATE_VERIFIED` evidence, binds the current frozen contract, exact baseline and `APPLIED.diff`, recreates the exact candidate in a disposable detached worktree, descriptor-reads and SHA-256 binds an evaluator outside the product repository, executes it with `shell=False`, rejects evaluator mutation, preserves operator/worktree state, and writes non-overwritable `FINAL_EVALUATION.json` evidence.

Evaluator result semantics:

- exit 0 -> `PASS`;
- exit 75 with `FORGE_BLOCKED_EXTERNAL:` -> `BLOCKED_EXTERNAL`;
- otherwise -> `REPAIR_REQUIRED`.

The repaired runtime passes the frozen A00-A11 matrix and direct gate tamper/mutation suite. A08 now reaches only `CANDIDATE_VERIFIED` before the held-out evaluator returns final `REPAIR_REQUIRED`.
