# Bardyla Forge — F0 Foundation Survey

This repository contains the documentation-only FORGE-F0 survey and freeze package.

**F0 verdict:** `PASS`

The frozen F0 snapshot was canonicalized to GitHub with exact tree identity:

- remote: `rbardyla-boop/FORGE`
- frozen remote commit: `7d0b07ba01837ef09e8b8e79a015bb91f7c49a11`
- frozen tree: `d52bd244c0f4e33975a36ccc39ea767e18a299be`
- original local frozen tree: `d52bd244c0f4e33975a36ccc39ea767e18a299be`

No production code exists in F0.

F0 authorizes exactly one successor: **FORGE-F1 — persistent skeleton with only `forge init` and `forge status`, plus context/process-loss recovery proof.**

Start with:

- `docs/f0/CHARTER.md`
- `docs/f0/FORGE_0_1_CLAIM.md`
- `docs/f0/SALVAGE_LEDGER.md`
- `docs/f0/REPRODUCTION_MATRIX.md`
- `docs/f0/F0_VERDICT.md`

## Current construction state

- FORGE-F0: `PASS`
- FORGE-F1: `PASS`
- FORGE-F2: `PASS`
- FORGE-F3: `PASS`
- FORGE-F4: `PASS`
- FORGE-F5: `PASS`
- FORGE-F6: `PASS`
- FORGE FOUNDATION GATE: `PASS`
- FORGE-W1 BuilderAdapter proposal boundary: `PASS`
- FORGE-W2 Provider Execution Containment: `PASS`
- FORGE-W3 Codex Adapter Boundary: `PASS`

F1 adds only persistent canonical state plus `forge init` and `forge status`.

F2 adds frozen machine-readable contract authority and an explicit digest-linked amendment chain; it does not execute contract checks.

F3 adds a disposable Git-worktree Environment Doctor that classifies baseline readiness without modifying product code.

F4 adds one bounded manual-patch lifecycle that runs only in a disposable worktree. Mechanical success is now `CANDIDATE_VERIFIED`, not final completion.

F5 adds an exact-artifact-bound independent final gate. The frozen A00–A11 false-completion matrix finishes with zero final false completions after preserving and repairing the A08 visible-test-overfit failure.

F6 adds immutable serious-failure memory: repair requires four frozen evaluator layers, locked failures remain permanent regression obligations, and later F4 candidates must replay them before `CANDIDATE_VERIFIED`.

The Foundation Gate attacks F1–F6 as one composed system. It discovered and repaired two additional authority leaks: mutable baseline substitution at the final gate and deletion of a locked failure obligation. The terminal system matrix, 10/10 repeated fresh runs, full F1–F6 replay, compilation and whitespace gates all pass.

W1 adds a provider-agnostic proposal boundary with exactly `forge proposal request|submit|verify`. A proposal is only patch + bounded trace and is always non-final: `PROPOSAL_ACCEPTED`, `completion_authority: none`, `candidate_authority: none`. W1 executes no coding provider and no trusted completion gate.

W2 adds an actual Linux Docker provider-execution boundary before any real coding provider is connected. The operator repository and `.forge` authority are not mounted; provider code receives a writable disposable workspace, read-only W1 request, trace-only egress, no network, zero capabilities, no Docker socket/devices, bounded resources, and no completion authority. Forge independently validates the resulting workspace and derives the authoritative patch in a fresh trusted collector before W1 ingestion. W2 discovered and permanently repaired a rejected-provider cleanup ownership defect. Its terminal clean-room run passes 47/47 W2-specific tests plus the complete W1, Foundation and F6–F1 regression stack.

W3 adds a Codex-specific adapter boundary without making a real OpenAI request. The supported public boundary requires an absolute non-symlink executable path, fingerprints exact executable bytes, freezes the current non-interactive `codex exec` argv contract, strips ambient credentials and user configuration, uses a fresh disposable `CODEX_HOME`, bounds stdout/stderr/JSONL, rejects malformed or contradictory terminal events, and treats provider PASS/MERGE/file-change claims as untrusted evidence only. A Codex-shaped fixture also executes under W2's actual `network none` Docker profile; exact workspace bytes remain authoritative through W2's trusted patch collector and can reach only W1 `PROPOSAL_ACCEPTED`. W3 discovered and permanently repaired a relative-executable authority leak. Its terminal run replays the complete W2, W1, Foundation, and F6–F1 stack successfully.

W3 `PASS` authorizes exactly **W4 Real Codex Pilot / Credential-Network Bridge**. W4 must design and falsify the smallest mechanism that permits one real Codex CLI request to reach OpenAI while keeping credentials outside repository-controlled execution and preserving W1/W2/Foundation authority. The first live result may terminate only at W1 `PROPOSAL_ACCEPTED` before separate Foundation verification. Automatic Foundation handoff, final PASS authority, merge/deploy, project-management autonomy, routing, swarms and all Roof capabilities remain unauthorized.
