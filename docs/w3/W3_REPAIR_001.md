# FORGE-W3 REPAIR 001 — Strict Public Executable Authority Boundary

**Unit:** FORGE-W3
**Repair:** W3-R001
**Repairs:** W3-F001
**State:** FROZEN BEFORE CODE

## Objective

Make the absolute executable-path requirement impossible to bypass through W3's supported public API while preserving the already-working fingerprint/version kernel.

## Repair architecture

W3 will separate:

- `codex_adapter.py` — inner implementation kernel;
- `codex_boundary.py` — the only supported public W3 authority entry point.

The public boundary SHALL reject a relative executable `Path` before calling `resolve()`, hashing bytes, running `--version`, or delegating to the inner kernel.

The public boundary SHALL expose the supported W3 operations needed by tests/callers:

- executable inspection;
- argv construction;
- adapter execution;
- event-to-W1-trace conversion;
- public constants/errors required for deterministic integration.

## Rules

1. Absolute-path validation occurs on the original caller value.
2. Symlink rejection remains in the inner kernel as a second defense.
3. `execute_codex_adapter()` validates the caller executable through the public boundary before delegation.
4. W3 tests and future W3/W4 integrations import the public boundary, not the inner kernel.
5. Direct inner-kernel import is treated as unsupported implementation access and receives no authority claim.
6. No credential, network, JSONL, W2, W1, F4/F5, or provider-execution policy changes are authorized by this repair.

## Required repair regressions

- R001-A00 relative inspection fails before delegate invocation;
- R001-A01 relative execution fails before delegate invocation;
- R001-A02 absolute executable inspection delegates and preserves exact manifest;
- R001-A03 symlink remains rejected;
- R001-A04 supported W3 tests import the public boundary rather than the inner kernel.

## Terminal rule

Repair 001 does not authorize W3 PASS. After the repair regressions pass, the entire W3 A00–A32 packet restarts from zero. Only after W3 direct success may predecessor replay begin.
