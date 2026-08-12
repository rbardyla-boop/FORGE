# FORGE-W2 Amendment 001 — Writable Disposable Workspace, Harness-Derived Patch

**Unit:** FORGE-W2
**Amendment state:** APPROVED BEFORE W2 PRODUCTION IMPLEMENTATION
**Reason:** the frozen initial contract made the provider repository mount read-only. That can prove process isolation, but it is not a usable precursor to a real coding agent, which must edit/test an isolated copy. Building that version would optimize the fixture rather than the future W3 boundary.

This amendment changes no W1/Foundation completion authority.

## Superseded W2 clauses

The initial W2 contract statements that the provider workspace itself is read-only and that the provider is the authority producing `PATCH.diff` are superseded by the rules below.

The initial Docker capability probe remains valid evidence that the backend supports read-only mounts/rootfs and the required security flags, but W2 production validation must additionally prove the amended writable-workspace design.

## Amended workspace architecture

Forge creates three separate temporary authorities outside the operator product repository:

1. **trusted baseline source** — reconstructed from the exact W1 request baseline using trusted Git operations;
2. **provider workspace** — a disposable writable filesystem copy of that baseline, containing no operator `.forge` state and no reference/path that grants access to the operator repository;
3. **trusted collector** — created only after provider execution from the exact baseline by Forge, never mounted to the provider.

The operator repository itself is never mounted into provider containment.

### Provider workspace

The provider workspace:

- is writable by the non-root provider user;
- contains the baseline product files;
- may contain a synthetic/disposable local `.git` repository for provider ergonomics, but that `.git` metadata is **never authority** after provider execution;
- contains no operator Git remote/credentials/config and no operator `.forge` state;
- is mounted only at `/workspace` inside containment;
- may be arbitrarily edited by the untrusted provider within the filesystem/resource boundary.

Provider mutation of this workspace is expected. Mutation of the operator repository is forbidden.

## Harness-derived patch authority

After provider exit, Forge does **not** trust a provider-authored patch or the provider workspace's `.git` index/history.

Forge must:

1. validate the workspace tree from outside containment;
2. reject unsupported special files, unsafe symlinks, path/size/count violations, and escape conditions;
3. create a fresh trusted collector worktree at the exact W1 baseline;
4. replace the collector's product tree with the validated provider workspace product tree while excluding provider-local `.git` metadata;
5. run trusted `git add -A` in the collector;
6. derive the exact binary/full-index patch from the collector baseline;
7. require a non-empty patch;
8. write that Forge-derived patch as `PATCH.diff` in the controlled output/evidence area;
9. pass the derived patch plus provider `TRACE.json` to W1 `proposal submit`.

The provider's own Git state, claims, staging decisions, or patch text have zero authority.

If the provider creates `PATCH.diff` itself, W2 treats that as an unauthorized extra provider output and rejects the execution rather than confusing it with the harness-derived patch.

## Amended provider egress

At provider process exit, the writable `/output` mount may contain exactly:

```text
TRACE.json
```

and nothing else.

Forge validates `TRACE.json`, then creates `PATCH.diff` itself after independently deriving the workspace delta. The final controlled output area may then contain exactly:

```text
PATCH.diff
TRACE.json
```

before W1 ingestion.

## Isolation profile after amendment

Still required:

- Docker root filesystem read-only;
- `--network none`;
- all capabilities dropped;
- no-new-privileges;
- non-root user;
- PID/memory/CPU/time bounds;
- no Docker socket/device/host-home/operator-repo mounts;
- request input read-only;
- provider workspace is the only writable code tree;
- output directory writable only for trace egress;
- bounded tmpfs.

## Amended malicious-fixture expectations

The original W2 attack list remains, except:

- provider write to `/workspace` is now expected to **succeed** because it is a disposable copy;
- the decisive safety test becomes: provider can freely corrupt/edit `/workspace` while the operator repository and Forge authority remain byte/status/worktree unchanged;
- Forge must derive the same patch from workspace bytes regardless of provider-local `.git` staging/history manipulation;
- provider deleting/changing its synthetic `.git` must not alter harness-derived patch authority;
- provider-supplied `PATCH.diff` is rejected as unauthorized output;
- malicious special files/symlink escapes in the provider workspace are rejected before trusted collection/W1 ingestion.

## W3 compatibility rationale

This amendment creates the boundary a future Codex adapter actually needs:

```text
sealed W1 request
      ↓
trusted exact baseline copy
      ↓
UNTRUSTED PROVIDER
  edits disposable workspace
  may run its own local tools/tests
  writes bounded trace only
      ↓
trusted Forge collector
  ignores provider Git authority
  derives exact patch from bytes
      ↓
W1 proposal submit
      ↓
PROPOSAL_ACCEPTED only
```

W3 must still freeze its own network/credential/image/provider policy; W2 remains network-denied and credential-free.
