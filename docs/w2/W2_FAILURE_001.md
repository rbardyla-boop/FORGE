# FORGE-W2 FAILURE 001 — Rejected Provider-Owned Tree Escaped Cleanup

**Unit:** FORGE-W2
**Failure:** W2-F001
**Terminal impact:** `REPAIR_REQUIRED`
**Discovered by:** terminal clean-room run `31627588031`
**First failing group:** W2 workspace and egress
**Attack:** provider creates forbidden `.forge/state.json` in disposable workspace

## Expected

Forge rejects the forbidden `.forge` authority path, persists a bounded rejection result, removes the entire disposable provider workspace, and returns without leaking an exception or temporary residue.

## Actual

The provider ran as container UID/GID `65534:65534` while Forge ran as a different non-root host user. The malicious fixture created `.forge/state.json` owned by UID 65534. Forge correctly identified the forbidden authority path, but `tempfile.TemporaryDirectory` cleanup then failed with `PermissionError` while trying to remove the provider-owned nested directory.

The terminal run therefore stopped after:

- W2 active isolation: **12/12 PASS**
- W2 workspace/egress: **12 PASS + 1 ERROR**
- all later W2/W1/Foundation/F6-F1 gates: **NOT CREDITED / SKIPPED**

## Root cause

W2 made the provider non-root, but it did not make provider-created bind-mount bytes reliably reclaimable by the non-root Forge host process. A different numeric container UID is not itself a security boundary once mount/network/capability isolation already exists, and it created an avoidable ownership mismatch on the disposable host bind mount.

## Security significance

This is not a completion-authority bypass: the malicious output never reached `PROPOSAL_ACCEPTED`, `CANDIDATE_VERIFIED`, or `PASS`.

It is still a real containment-lifecycle defect because a rejected provider can cause cleanup failure and leave disposable residue. W2 promises bounded execution and cleanup, so this must be repaired before W2 can pass.

## Permanent regression requirement

The repaired W2 must prove that:

1. provider execution always uses a numeric **non-root** identity;
2. provider-created workspace bytes are reclaimable by Forge without a privileged cleanup helper;
3. the original forbidden `.forge` attack returns a normal rejection rather than raising during cleanup;
4. no `forge-w2-exec-*` temporary directory remains after the rejected attempt;
5. running Forge as host root fails closed for this backend;
6. Docker user-namespace/rootless modes that break direct bind-mount ownership are not silently accepted by `linux-docker-v0.1`.
