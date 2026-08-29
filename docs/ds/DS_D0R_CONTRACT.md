# DS-D0R — Release Boundary + Staging + Rollback Proof

Status: **FROZEN**

## Claim under test

The explicitly selected public subset can be built from immutable DS-E1 source
and can be deployed, rolled back to the exact predecessor, and restored on a
non-production Cloudflare Worker without touching `wild-hat-6257` or changing
the DS public release boundary.

## Frozen controls

```text
candidate:       bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc
predecessor:     d8727e7d5946f48ada39199e77df9564a62e4203
release choice:  B — DS-00 excluded from public artifact
staging Worker:  clove-ds-d0r-staging-20260813-r1
staging surface: workers.dev only; no route; no bindings
```

## Required sequence

1. Create clean detached source worktrees for candidate and predecessor.
2. Run the exact production preflight from each source.
3. Build each public upload artifact and freeze a per-file SHA-256 manifest.
4. Verify exactly 302 public files and zero DS-00 runtime files.
5. Deploy candidate to the staging Worker; capture version and workers.dev URL.
6. Smoke candidate HTTP behavior and source manifest.
7. Deploy predecessor to the same staging Worker; verify predecessor source
   manifest and HTTP behavior.
8. Redeploy candidate; verify candidate source manifest again.
9. Capture production Worker metadata before and after; prove no production
   route/config/version change.
10. Remove the disposable staging Worker only after all evidence is written.

## Terminal outcomes

```text
DS_D0R_RELEASE_PATH_PROVEN
DS_D0R_REPAIR_REQUIRED
DS_D0R_BLOCKED
```

Any missing live staging deployment, wrong source manifest, DS-00 leakage,
production metadata change, or failed predecessor restoration is terminal for
this unit. No production deployment is authorized by DS-D0R.
