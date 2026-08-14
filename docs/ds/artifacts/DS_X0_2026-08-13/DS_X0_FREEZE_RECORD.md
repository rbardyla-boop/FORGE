# DS-X0 freeze record — 2026-08-13

## Terminal ruling

```text
ENGINEERING_RELEASE_SUPPORTED / HUMAN_USABILITY_NOT_CLAIMED
```

DS-X0 executed the frozen engineering gauntlet against a temporary
`git archive` of the DS-E1 candidate. No Clove checkout or candidate source
was modified. This result authorizes, at most, a separately reviewed
engineering-qualified experimental/beta release; it does not authorize
deployment by itself and does not establish human usability.

## Frozen bindings

```text
candidate commit:             bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc
candidate parent:             d8727e7d5946f48ada39199e77df9564a62e4203
DS-E1 packet SHA-256:         2c54e87a123b8afe5d9719c45ad39655af896e0ebf3c51ccfdf89801f4c7c817
DS-X0 contract SHA-256:       37a6fd797702511d842fd8c25bf650f2159fd0b316b527535d8be17a0b6b4567
snapshot DS-00–DS-06 hash:    2e566f69b9f67f21f642549a409c4fb3ea569e5d067a3db9988172bc3879031d
browser:                      Firefox headless
execution count:              50
network:                      local fixture server only
```

## Results

```text
core task completion:         20/20 (100%)
failure/recovery completion:  8/8 (100%)
safe-stop executions:         6/6
false-success outcomes:       0
safety/privacy failures:      0
irrecoverable corruption:     0
candidate mutations:          0
cross-run leakage:            0
deterministic replay:         2/2 (100%)
DS-I0 regression:              31/31 PASS
DS-E1 properties:              PASS
```

The operator evidence and machine verdict are retained beside this record.
The earlier invalid attempt exposed two harness-only issues—reading DS-I0
from the wrong checkout and not providing a temporary Git index to the
archive-bound release test. Both were corrected before this frozen run; no
Clove source or acceptance criterion was changed.

## Human-evidence boundary

```text
human evidence:               unavailable
human usability claim:        NOT CLAIMED
human effectiveness claim:    NOT CLAIMED
```

This synthetic operator result must not be relabeled as a participant study.
