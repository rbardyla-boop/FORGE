# DS-D0 — Deployment Authorization Gate

Status: **FROZEN / READ-ONLY GATE**

## Claim under test

The exact DS-E1 candidate can be authorized for its identified CloveLearn
deployment target without changing the candidate, weakening the non-public
release boundary, introducing a human-usability claim, or losing rollback
readiness.

DS-D0 authorizes no deployment. It only returns one of:

```text
DS_D0_DEPLOYMENT_AUTHORIZED
DS_D0_DEPLOYMENT_BLOCKED
```

## Frozen candidate

```text
candidate commit:       bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc
parent / rollback:      d8727e7d5946f48ada39199e77df9564a62e4203
DS-E1 packet:            2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817
DS-X0 contract:          37a6fd797702511d842fd8c25bf650f2159fd0b316b527535d8be17a0b6b4567
DS-X0 verdict:           590304137f648a5f62ea8d06f69f4537e9146cfa613947ad83b11edfd238aadd
DS-H2 record:            8591fddf8cdef4224b97b68e374052efb6596ce6281a58535ac78784ee31b549
```

The candidate is read from an exact `git archive` snapshot. The current
Clove checkout is never modified or used as an implicit substitute.

## Deployment target

The identified production static target is the Cloudflare Workers static-assets
Worker `wild-hat-6257` serving `clovelearn.io`, using the existing owner
dashboard static-file upload path. This gate does not invoke Wrangler, the
dashboard, or any Cloudflare write operation.

The current production policy explicitly excludes all DS-I0–DS-I6 runtime
files from that public upload. Removing that lock is a separate release unit;
DS-D0 may not infer that authorization.

## Required checks

1. Exact candidate commit, parent, authorized one-file delta, and DS-00–DS-06
   source manifest match the frozen DS-E1/DS-X0 records.
2. DS-E1, DS-X0, and DS-H2 evidence hashes verify.
3. Candidate archive production preflight passes, with no secrets/configs
   entering the package.
4. Candidate runtime/public surface matches the frozen 302-file baseline,
   unless an explicit release record says otherwise.
5. The candidate checkout/source snapshot is clean and no implicit current
   HEAD or unrelated delta is substituted.
6. The deployment target and post-deploy smoke checks are named.
7. The exact parent candidate can be reconstructed before deployment as the
   rollback source.
8. A production-level rollback operator path is available and proven.
9. No UI, documentation, metadata, or package record introduces a
   `HUMAN_USABILITY` claim.
10. W2/W4 Docker fixture paths are classified as non-blocking only if this
    gate does not traverse them.

## Frozen post-deploy smoke specification

If DS-D0 ever authorizes a later DS-D1 deployment, the smoke must verify:

```text
GET /                           → 200
GET /digital-stewardship-00.html → expected target status
DS-00 source bytes              → exact candidate hash
DS-00 safe known path           → COMPLETE
DS-00 unknown path              → Recovery still unknown
DS-00 STOP path                 → STOPPED SAFELY
network writes                  → 0
HUMAN_USABILITY claim           → absent
existing public surface         → unchanged
```

## Terminal discipline

Any missing release target, public-surface mismatch, absent production rollback
path, changed release lock, or candidate substitution blocks authorization.
W2/W4 failures are not DS-D0 blockers unless the verifier demonstrates that
the deployment path actually traverses those systems.
