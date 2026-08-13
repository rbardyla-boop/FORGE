# W4-F001 — Artifact digest prefix was passed to `sha256sum`

**Class:** `REAL_FORGE_DEFECT`

## Reproducer

Run the artifact-resolution step with a GitHub release digest in its native
form:

```text
sha256:0246e2e773834e07f0fb5249ed6ebad12e4591e608f8c7bb97dd6a9690544c36
```

The first implementation executed:

```bash
printf '%s  %s\n' "$CLI_DIGEST" "$CLI_FILE" | sha256sum --check --strict
```

and failed with:

```text
sha256sum: 'standard input': no properly formatted checksum lines found
```

## Expected behavior

The downloaded bytes must be checked against the exact release digest and the
gate must proceed only on an exact match.

## Root cause

GitHub release metadata uses the `sha256:` algorithm prefix; GNU `sha256sum`
expects only the hexadecimal digest in its check-input format.

## Bounded repair

Strip only the literal `sha256:` metadata prefix at the shell boundary before
calling `sha256sum --check --strict`. The frozen release digest remains stored
and printed with its algorithm prefix, and the independent observed hash is
still computed by `sha256sum`.

## Permanent regression

The W4 artifact-resolution workflow now performs the exact release metadata
lookup, byte download, and strict prefixed-digest conversion for both pinned
assets. The terminal replay must execute both checks before extraction or
binary execution.

## Runtime impact

None. The failure occurred in validation before extraction; no W4 runtime or
official binary was executed under the failed attempt.
