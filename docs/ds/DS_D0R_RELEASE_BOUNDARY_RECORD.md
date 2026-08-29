# DS-D0R — Release boundary decision

Status: **FROZEN / OPTION B**

## Decision

`DS-00 IS NOT part of the public release` for this unit.

The existing production boundary remains authoritative: the public static
upload for `wild-hat-6257` / `clovelearn.io` excludes all DS-I0–DS-I6 runtime
files. DS-D0R does not remove that lock and does not make a human-usability
claim.

The deployable public subset is therefore the exact production-curated
artifact generated from immutable commit `bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc`.
Its expected public file count is **302**. The artifact contains no
`digital-stewardship-00.html` or `digital-stewardship-00.js`.

## Meaning of the evidence boundary

DS-E1 and DS-X0 remain valid evidence about the frozen DS-E1 engineering
candidate and its private DS-00 runtime. The public subset carries no DS-00
runtime and therefore introduces no public DS behavior. This record does not
claim that the public subset exposes or proves DS usability.

## Required staging proof

The exact public subset must be built from immutable candidate source, deployed
to a workers.dev-only staging Worker, smoke-tested, replaced by the exact
parent artifact, smoke-tested again, and then restored to the candidate. The
production `wild-hat-6257` route must not be named in the staging config.
