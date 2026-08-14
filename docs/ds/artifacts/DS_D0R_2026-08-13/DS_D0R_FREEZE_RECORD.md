# DS-D0R freeze record — 2026-08-13

Terminal ruling: **DS_D0R_RELEASE_PATH_PROVEN**

## Claim

The explicitly selected public subset can be built from immutable DS-E1 source,
deployed to a disposable workers.dev-only Cloudflare Worker, replaced by its
exact predecessor, restored to the candidate, and removed without touching the
production Worker or route.

## Frozen release boundary

- Release choice: **B** — DS-00 is not part of the public release.
- Candidate: `bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc`
- Predecessor: `d8727e7d5946f48ada39199e77df9564a62e4203`
- Public artifact: 302 files, with `digital-stewardship-00.html` and
  `digital-stewardship-00.js` absent.
- Production target observed but not modified: `wild-hat-6257` / `clovelearn.io`.

## Immutable staging sequence

Staging Worker: `clove-ds-d0r-staging-20260813-r1` (workers.dev only; no
routes; ASSETS binding only).

| State | Cloudflare version | Live checks |
|---|---|---|
| Candidate | `0799d26c-6f52-4c91-b6ee-27a33b7c0d50` | root 200; Research 200; manifest candidate; DS-00 404 |
| Predecessor rollback | `e2dbb457-a95e-4bbd-99a0-ae9555c25205` | root 200; Research 200; manifest predecessor; DS-00 404 |
| Candidate restore | `c050a6ba-f33f-422b-90f5-337ec05d6440` | root 200; Research 200; manifest candidate; DS-00 404 |

The public artifact's intentional redirect was preserved and verified:
`/index.html → 302 /deck.html`. Root byte checks use `/`, which serves the
artifact's `index.html`.

## Isolation and cleanup

- Production versions JSON before/after SHA-256:
  `33d05b9f78138b4811cbf7b0b8311ae78a1bbe2512d7adad6a4a9eeaa0e86972`
- Production deployments JSON before/after SHA-256:
  `aebed491b6e1b23035d51d6a1b7525aeec2f49d3f137d106159a672db6e2c8b2`
- Before/after files were byte-identical.
- Disposable staging Worker was deleted after evidence capture. A subsequent
  read returned Cloudflare API code `10007` (Worker does not exist).
- No production upload, route mutation, binding mutation, secret mutation, or
  production rollback was performed.

## Verification-grinder record

- Check: immutable source → exact 302-file public artifact → real staging
  upload → candidate/predecessor/candidate live rollback sequence → production
  metadata comparison → disposable cleanup.
- Criteria: exact source manifests; clean detached worktrees; both preflights
  PASS; no DS-00; all live smoke checks pass; source sequence exact; production
  metadata unchanged; cleanup confirmed.
- Verdict: **PASS — DS_D0R_RELEASE_PATH_PROVEN**.
- Assumptions: the production metadata endpoints are the relevant read-only
  Cloudflare version/deployment records; public release choice B remains
  authoritative.
- Credit: proves the release path and Cloudflare mechanics, not production
  correctness or human usability.
- Gap: DS-D0 must be rerun against this frozen release-boundary/staging
  evidence before any production deployment authorization.
- Stop/continue: stop DS-D0R; continue only with fresh DS-D0. DS-D1 remains
  unauthorized.
- Maturity: **M3 — externally exercised, production-isolated release proof**.
