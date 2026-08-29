# DS-D0 fresh re-evaluation — release authorization

Status: **FROZEN / BOUND TO DS-D0R**

This is the fresh DS-D0 gate required after `DS_D0R_RELEASE_PATH_PROVEN`.
The earlier blocked DS-D0 record remains immutable historical evidence.

## Claim under test

The exact public release subset can now be authorized for the identified
production deployment path without changing the candidate, silently adding
DS-00 to the public surface, introducing a human-usability claim, or losing
rollback readiness.

## Binding

```text
candidate:       bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc
predecessor:     d8727e7d5946f48ada39199e77df9564a62e4203
DS-D0R verdict:  docs/ds/artifacts/DS_D0R_2026-08-13/DS_D0R_VERDICT.json
release choice:  B — DS-00 excluded from public artifact
public files:    302
target:          wild-hat-6257 / clovelearn.io
```

## Required checks

1. DS-D0R terminal is `DS_D0R_RELEASE_PATH_PROVEN` and its hash manifest
   verifies.
2. Candidate and predecessor source manifests, preflights, exact public
   artifact counts, and DS-00 exclusion pass.
3. The executed staging sequence is candidate → predecessor → candidate, and
   every live smoke check passed.
4. Production version/deployment metadata is byte-identical before and after;
   no production write occurred during DS-D0R.
5. DS-E1, DS-X0, and DS-H2 evidence remains intact; human usability remains
   explicitly `NOT_CLAIMED`.
6. The current operator checkout is not used as an implicit candidate source.
   It may remain at another clean HEAD; deployment uses the frozen public
   artifact from immutable candidate source.
7. The production target and rollback path are identified. The rollback
   mechanics are proven on the disposable staging target; this gate does not
   claim that production has already been mutated or rolled back.
8. W2/W4 failures remain non-blocking because this deployment path does not
   traverse those Docker fixtures.

## Public-surface smoke for the selected boundary

```text
GET /                           → 200; exact 302-file artifact index bytes
GET /research/                  → 200; exact artifact bytes
GET /index.html                 → 302 /deck.html (intentional _redirects rule)
GET /_UPLOAD_MANIFEST.json      → source_sha + file_count 302
GET /digital-stewardship-00.html → 404; DS-00 remains non-public
```

## Terminal outcomes

```text
DS_D0_DEPLOYMENT_AUTHORIZED
DS_D0_DEPLOYMENT_BLOCKED
```

Authorization, if earned, applies only to the frozen 302-file public subset.
It does not authorize DS-00, alter the production route, or itself perform
DS-D1 deployment.
