# FORGE-W3 FAILURE 001 — Relative Executable Path Normalized Before Authority Check

**Unit:** FORGE-W3
**Failure:** W3-F001
**Terminal impact:** `REPAIR_REQUIRED`
**Discovered by:** W3 direct clean-room run `31632082006`
**First failing attack:** A01

## Expected

The W3 public Codex adapter accepts only a caller-supplied **absolute**, regular, non-symlink executable path. A relative path must fail before path normalization, executable hashing, version invocation, or task execution.

## Actual

The initial `inspect_codex_executable()` implementation performed `Path.resolve()` before `_executable_bytes()` checked `is_absolute()`. A caller could therefore supply `fake-codex`, have it resolved against ambient process working directory, and still receive a valid executable manifest.

Symlink rejection remained correct. A00 exact fingerprinting passed; A01 then failed on the relative-path negative control and the direct workflow stopped. JSONL and W2/W1 composition groups received zero credit from that run.

## Security significance

This is an executable-authority defect, not a completion bypass. No W1 proposal, F4 candidate, F5 PASS, real credential, or remote OpenAI request was involved.

It matters because W3 explicitly removes PATH/cwd discovery from provider authority. If ambient cwd can determine the executable, the frozen executable identity is weaker than declared.

## Required permanent regression

- relative path rejected before normalization;
- symlink path remains rejected;
- absolute regular executable still fingerprints normally;
- task execution cannot bypass the strict path check by calling the inner kernel directly through the public W3 API;
- no subprocess/version invocation occurs for a relative executable negative control.
