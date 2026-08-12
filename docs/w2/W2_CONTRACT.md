# FORGE-W2 Contract — Provider Execution Containment

**Unit:** FORGE-W2
**Layer:** Walls / second unit
**State:** FROZEN BEFORE IMPLEMENTATION
**Base:** canonical FORGE-W1 `PASS`
**Real coding provider:** forbidden
**Codex integration:** deferred to W3

## Objective

Prove that Forge can execute a deterministic untrusted fixture provider inside an actual operating-system containment boundary, give it only W1-authorized inputs, collect only patch + trace outputs, and preserve zero completion/merge/deploy authority.

W2 does **not** connect Codex, Claude, an API key, or any networked coding service.

## Why W2 exists

W1 proved the data/trust boundary but did not execute provider code. Running a future provider with only a different working directory or stripped prompt is not containment: a same-user subprocess could still read credentials, traverse the host filesystem, modify the operator repository, access `.forge`, use the network, or interfere with sibling processes.

W2 therefore proves the process boundary before any real provider is connected.

## Initial supported backend

W2 supports exactly one Foundation-era execution backend:

```text
linux-docker-v0.1
```

The backend is acceptable only when its capability probe and malicious-fixture suite pass. Docker availability alone is not sufficient evidence.

If the backend is unavailable or its required isolation controls cannot be demonstrated, Forge must report:

```text
CONTAINMENT_UNAVAILABLE
```

and refuse provider execution.

No silent fallback to ordinary `subprocess`, shell execution, `cwd` isolation, or an uncontained provider is permitted.

## Runtime authority model

W2 consumes an existing, verified W1 request and executes a provider image whose exact local Docker image ID is pinned as `sha256:...` before execution.

The provider receives only:

- a tracked repository snapshot reconstructed from the exact W1 request baseline;
- the exact W1 `REQUEST.json`;
- an empty writable output directory;
- Forge-defined non-secret environment variables naming those three in-container paths.

The provider does not receive:

- the operator repository path/mount;
- `.forge` state or proposal/failure/evidence directories;
- the host home directory;
- Git credentials/config from the operator environment;
- environment secrets/API keys;
- Docker socket;
- host devices;
- host network access;
- writable repository snapshot;
- completion, merge, deploy, contract, evaluator, or failure-ledger authority.

## Repository snapshot

Forge reconstructs the provider workspace from the exact W1 request baseline using tracked Git content only.

Required properties:

- exact baseline commit is independently revalidated against W1 request/live authority before execution;
- snapshot is created outside the operator product repository;
- `.forge` and other untracked operator state are absent by construction;
- snapshot tree digest/identity is recorded;
- container mount is read-only;
- provider cannot alter the operator repository through the snapshot.

## Docker containment profile

The initial backend must invoke the provider with controls equivalent to:

- `--network none`;
- `--read-only` root filesystem;
- `--cap-drop ALL`;
- `--security-opt no-new-privileges`;
- non-root numeric user;
- bounded PID count;
- bounded memory;
- bounded CPU;
- bounded wall-clock timeout enforced by Forge;
- read-only workspace mount;
- read-only request-file mount;
- one writable output-directory mount only;
- bounded, noexec/nosuid/nodev temporary filesystem where required;
- no Docker socket mount;
- no host device mount;
- no host PID/IPC/network namespace sharing;
- no host-home mount;
- no inherited environment except Forge's explicit allowlist.

The exact command/flags used are evidence and must be inspectable.

## Provider image authority

W2 never executes an unpinned mutable tag as authority.

Before launch, Forge must resolve the selected fixture image to an exact local image ID and execute by that immutable image ID.

W2 tests may build deterministic local fixture images before provider execution. Pull/build network activity, if used by the trusted test harness to prepare an image, occurs **outside** provider execution and is not evidence of provider network access.

W3 must freeze its own image/provider acquisition policy separately before real Codex execution.

## Provider output protocol

Inside the writable output directory the provider may return exactly:

```text
PATCH.diff
TRACE.json
```

No other regular file, directory, symlink, device, FIFO, or socket is accepted.

Bounds:

- `PATCH.diff` <= 1 MiB;
- `TRACE.json` <= 256 KiB;
- captured stdout/stderr are bounded separately and are diagnostic only.

After containment exits successfully, W2 passes the returned files into the existing W1 `proposal submit` validator.

A successful W2 execution therefore yields at most:

```text
PROPOSAL_ACCEPTED
completion_authority: none
candidate_authority: none
```

W2 never calls `forge unit run` or `forge gate run` automatically.

## Execution evidence

Persist provider execution evidence under the W1 request authority without changing product files. Evidence binds at minimum:

- W1 request digest;
- exact baseline commit;
- snapshot identity;
- containment backend/version;
- exact Docker image ID;
- exact containment arguments/profile;
- provider fixture/adapter identity;
- exit code;
- timeout state;
- bounded stdout/stderr + truncation flags;
- exact returned patch/trace hashes and byte lengths when present;
- output-directory shape validation;
- operator tracked status/worktree-registry pre/post equality;
- W1 proposal digest if output reaches `PROPOSAL_ACCEPTED`;
- `completion_authority: none`;
- `candidate_authority: none`.

Execution evidence is append-only for the one W2 attempt and cannot overwrite W1 request/proposal evidence.

## Capability probe

Before any provider fixture execution, the backend probe must establish at minimum:

- Linux host;
- Docker CLI exists;
- daemon is reachable;
- required run flags are supported in the current environment;
- a minimal locally available/test image can execute under the full profile;
- read-only mounts and writable output mount behave as expected.

Probe result:

- `CONTAINMENT_READY`; or
- `CONTAINMENT_UNAVAILABLE` with explicit reason.

A failed probe cannot be waived by provider prose or user trace.

## Preregistered malicious fixture attacks

W2 must prove at least:

1. good fixture receives request + tracked baseline snapshot and produces a W1-valid patch + trace -> `PROPOSAL_ACCEPTED` only;
2. operator tracked repository bytes/status/worktree registry remain unchanged;
3. `.forge` is absent from provider workspace;
4. provider workspace is read-only;
5. container root filesystem is read-only except explicit output/tmp mounts;
6. host environment secret sentinel is absent from provider environment;
7. host-home/operator-only sentinel is unreadable even when its host absolute path is known to the malicious fixture;
8. outbound network attempt cannot reach an external address;
9. Docker socket is absent/unusable;
10. host devices are not exposed beyond the constrained container defaults required by runtime;
11. provider lacks privileged Linux capabilities and cannot gain new privileges;
12. provider cannot access host process namespace as host PID 1 / enumerate arbitrary host processes;
13. fork/process amplification is bounded by PID limit;
14. wall-clock timeout kills/cleans a hanging provider;
15. memory/CPU bounds are present in the exact run profile and malicious resource case cannot bypass the containment decision;
16. provider attempt to alter the read-only workspace fails and resulting host snapshot remains unchanged;
17. provider attempt to write outside `/output` and permitted tmpfs fails;
18. extra output file is rejected;
19. output symlink/FIFO/directory/device/socket is rejected;
20. missing `PATCH.diff` or `TRACE.json` is rejected;
21. oversize patch/trace is rejected;
22. malformed patch/trace is rejected by existing W1 validation;
23. trace claiming `PASS`, `DONE`, `MERGE`, `DEPLOY` has zero authority;
24. provider non-zero exit is not proposal success;
25. provider-generated behaviorally bad but well-scoped patch may be W1 `PROPOSAL_ACCEPTED`, but still has zero candidate/final authority and Foundation later rejects it;
26. mutable image tag cannot be execution authority; exact local image ID is required;
27. request/baseline/contract/failure-anchor drift before execution is rejected;
28. execution evidence cannot be overwritten;
29. no ordinary-subprocess fallback exists when Docker containment is unavailable;
30. CLI introduces no Codex/Claude/provider-specific networked execution, merge, deploy, retry/replan, or PASS authority;
31. W1 + Foundation + F1-F6 historical regressions remain green.

## Threat boundary

W2 treats the Docker daemon, Linux kernel, and trusted Forge harness as part of the trusted computing base. It does not claim resistance to:

- a malicious host root/administrator;
- a compromised Docker daemon/kernel;
- a container-runtime escape vulnerability outside Forge's control;
- a hostile repository owner who deliberately rewrites all Forge authority and Git history coherently.

Within that boundary, the provider process/image is treated as untrusted.

## Non-goals

W2 does not:

- connect Codex/Claude/OpenAI/Anthropic or any real provider;
- place an API key in provider execution;
- permit provider network access;
- select or route models;
- give provider shell access to the operator repository;
- automatically hand a proposal to F4;
- decide `CANDIDATE_VERIFIED` or final `PASS`;
- merge or deploy;
- retry/replan;
- add project-management autonomy;
- add multiple agents/swarm/AIS/Roof behavior.

## Terminal gate

W2 receives `PASS` only if:

- backend capability probe is reproducibly `CONTAINMENT_READY` in the validation environment;
- complete malicious-fixture containment suite passes;
- W1 proposal-boundary suite remains green;
- integrated Foundation Gate remains green;
- F1-F6 predecessor suites remain green;
- temporary validation/build infrastructure is removed from the merge candidate unless explicitly part of W2 production behavior;
- no runtime/test byte changes after terminal validation except documented non-executable closeout files;
- final GitHub merge tree equals the reviewed candidate tree.

If a real containment backend cannot satisfy these requirements, W2 terminates `BLOCKED_EXTERNAL` or `REPAIR_REQUIRED`; it does not authorize W3.

## Authorization on PASS

W2 `PASS` may authorize exactly:

> **W3 — Codex Adapter: freeze and prove one Codex-specific provider adapter that consumes the W1 request through the W2 execution boundary and returns only patch + trace, while all W1/Foundation completion authority remains external to Codex.**

W3 remains unauthorized until W2 is canonical `PASS`.
