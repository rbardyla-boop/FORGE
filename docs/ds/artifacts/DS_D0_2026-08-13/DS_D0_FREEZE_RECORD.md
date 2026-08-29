# DS-D0 freeze record — 2026-08-13

## Terminal ruling

```text
DS_D0_DEPLOYMENT_BLOCKED
```

This is an authorization block, not a candidate defect. The exact DS-E1
candidate passed its local production package checks and rollback-source
reconstruction. No Cloudflare write or deployment was attempted.

## Frozen identity

```text
candidate commit:             bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc
candidate parent:             d8727e7d5946f48ada39199e77df9564a62e4203
candidate archive SHA-256:    a941574c970acd16f71c91b3c628e28b9ab9b8aeee9eefd7cfde87b56204f28c
rollback archive SHA-256:     d1ad3fdd8959d4b2d6f9a2fa9ad914a4cffbf22cf69b3ec49d4c7cac2fcd115e
DS-00–DS-06 manifest:         2e566f69b9f67f21f642549a409c4fb3ea569e5d067a3db9988172bc3879031d
DS-E1 packet:                 2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817
DS-X0 verdict:                590304137f648a5f62ea8d06f69f4537e9146cfa613947ad83b11edfd238aadd
```

## Criteria

```text
exact candidate/delta                 PASS
DS-E1/DS-X0/DS-H2 evidence            PASS
candidate archive/source              PASS
candidate release preflight           PASS
302-file public baseline              PASS
DS-00 remains excluded                PASS
source rollback reconstruction        PASS
human-usability claim absent          PASS
W2/W4 dependency classification       NON-BLOCKING
current HEAD bound to candidate       FAIL
public DS release authorization       FAIL — separate unit required
production Cloudflare rollback path  FAIL — not proven here
```

Candidate package preflight result:

```text
status: PASS
included: 302
excluded: 881
hardening exclusions: 112
errors: 0
```

## Blocking reasons

1. The current Clove `main` HEAD is not the frozen DS-E1 candidate. A later
   deployment must use an explicitly candidate-bound staging/source path.
2. The existing `wild-hat-6257` / `clovelearn.io` public static upload still
   deliberately excludes `digital-stewardship-00.html/js`. DS-D0 has no
   authority to remove that release lock or publish a private slice.
3. This environment exposes no Cloudflare deployment action or credential, so
   production upload and rollback have not been proven.

W2/W4 Docker-fixture failures are classified as **non-blocking**: DS-D0 uses
only local Git/archive/Node package-preflight paths and does not traverse W2 or
W4 execution paths.

## Claim boundary

```text
engineering release: supported by DS-X0
external validation: passed by DS-E1
human usability:     NOT CLAIMED
deployment:          NOT AUTHORIZED
```

The next valid unit is a separately authorized deployment-target/release-
boundary decision, followed by DS-D1 only if the target and rollback path are
actually established.
