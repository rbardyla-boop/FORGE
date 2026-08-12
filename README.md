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

F1 adds only persistent canonical state plus `forge init` and `forge status`.

F2 adds frozen machine-readable contract authority and an explicit digest-linked amendment chain; it does not execute contract checks.

F3 adds a disposable Git-worktree Environment Doctor that classifies baseline readiness without modifying product code.

F4 adds one bounded manual-patch lifecycle that runs only in a disposable worktree and makes the harness, not the patch author, the terminal-state authority.

F4 authorizes exactly **FORGE-F5 — False-Completion Attack Harness**. No AI builder is authorized.
