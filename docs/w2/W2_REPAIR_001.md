# FORGE-W2 REPAIR 001 — Reclaimable Non-Root Provider Identity

**Unit:** FORGE-W2
**Repair:** W2-R001
**Repairs:** W2-F001
**State:** FROZEN BEFORE CODE

## Objective

Preserve the existing Docker containment boundary while guaranteeing that malicious provider-created bind-mount bytes remain reclaimable by Forge after rejection, without adding any privileged cleanup mechanism.

## Repair rule

`linux-docker-v0.1` will execute the provider as the **numeric effective UID/GID of the Forge host process**, provided that Forge itself is non-root.

This does not grant host filesystem access because the provider still receives only the disposable workspace, read-only request, and bounded output mounts inside its isolated mount namespace. Existing network, capability, namespace, device, rootfs, resource and credential restrictions remain unchanged.

## Fail-closed host/backend requirements

The backend must return `CONTAINMENT_UNAVAILABLE` when:

- Forge effective UID is `0`;
- Docker reports rootless execution or user-namespace remapping incompatible with direct bind-mount ownership for this v0.1 backend;
- the host identity cannot be represented as numeric UID/GID;
- post-container workspace ownership/permissions cannot be normalized by Forge.

W2 will not add `sudo`, a root cleanup container, a privileged helper, `--privileged`, added capabilities, or a daemon-side chown service.

## Runtime change

1. Resolve and record Forge host effective UID/GID.
2. Use `--user <euid>:<egid>` for provider containers.
3. After every provider exit — success, nonzero, timeout, or malicious output — normalize disposable workspace directory/file permissions as the owning Forge user before validation/cleanup.
4. Continue to reject `.forge`, unsafe symlinks, special files, invalid output and all existing attacks exactly as before.
5. Persist the selected numeric provider UID/GID in inspectable containment-profile evidence.

## Required repair regressions

- R001-A00: profile uses exact non-root Forge effective UID/GID.
- R001-A01: simulated host root identity fails closed.
- R001-A02: original forbidden `.forge/state.json` attack returns `PROVIDER_REJECTED`, not a cleanup exception.
- R001-A03: original attack leaves no new `forge-w2-exec-*` temporary directory.
- R001-A04: provider-owned restrictive nested directories are normalized/reclaimable before cleanup.
- R001-A05: no privileged cleanup command/path is introduced.
- R001-A06: existing active isolation profile remains intact apart from the numeric UID/GID value.

## Terminal rule

Repair 001 does not authorize W2 PASS by itself. After these regressions pass, the entire W2 40-test packet and every W1/Foundation/F6-F1 predecessor gate must restart from zero on the repaired candidate.
