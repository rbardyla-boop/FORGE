# FORGE-W3 Verdict — Codex Adapter Boundary

**Unit:** FORGE-W3
**Layer:** Walls / third unit
**Verdict:** `PASS`
**Validated branch head:** `afc4a13951daa171164afac2c315783886d3c20c`
**Terminal clean-room run:** `31632909434`
**Base:** canonical W2 `PASS`
**Real OpenAI/Codex remote inference in W3:** **NONE**

## Claim under test

Whether Forge can represent and invoke the current Codex CLI automation shape through a deterministic provider-specific adapter while preserving executable identity, stripped credential/config authority, bounded JSONL evidence, W2 containment, W1-only proposal authority, and every lower-layer completion/failure-memory invariant.

W3 intentionally did not test live OpenAI connectivity or credentials. Those remain a separate W4 boundary.

## Result

`PASS` within the frozen W3 fixture/interface boundary.

Terminal run `31632909434` completed with overall `success` on exact head `afc4a13951daa171164afac2c315783886d3c20c`.

### W3-specific evidence

- Repair 001 strict executable authority: **5/5**
- executable/config/credential authority: **12/12**
- JSONL/process behavior: **12/12**
- W2/W1 composition: **10/10**
- actual W2-contained Codex-shaped seam: **3/3**
- compile: **PASS**

The A00–A32 preregistered attack family plus the additional unsupported-version check all passed. The contained seam additionally proved the Codex-shaped provider could execute under the real W2 Docker profile and terminate only at W1 proposal authority.

### Predecessor evidence on the exact W3 candidate

- W2 Repair 001: **7/7**
- W2 active isolation: **12/12**
- W2 workspace/egress: **13/13**
- W2 execution authority/handoff: **13/13**
- W2 amended request/output: **2/2**
- W1 request authority: **7/7**
- W1 proposal submission: **10/10**
- W1 stale-integrity/handoff: **10/10**
- Foundation Repair 001: **5/5**
- Foundation Repair 002: **10/10**
- integrated Foundation FG-A00–A16: **PASS**, including its required **10/10 fresh-run reliability control**
- F6: **7/7 + 9/9 + 4/4**
- F5: **12/12 + 10/10**
- F4: **22/22 + 1/1**
- F3: **20/20 + 3/3**
- F2: **14/14 + 4/4**
- F1: **11/11**
- PR-base whitespace: **PASS**

## Failure discovered and preserved

### W3-F001 — relative executable path normalized before authority check

The initial implementation normalized a caller-supplied relative executable path with `Path.resolve()` before enforcing the absolute-path contract. This allowed ambient working directory to participate in executable selection.

Repair 001 added a strict supported public boundary (`codex_boundary.py`) that rejects a relative path before delegation, hashing, `--version`, or execution. The inner implementation remains a private kernel. Five permanent repair regressions prove relative inspection/execution fail before delegate invocation, absolute manifests remain exact, symlink rejection remains active, and supported W3 tests use the public boundary.

## Invalid validation run preserved as zero credit

After direct W3 was green, the first explicit W2-contained seam run failed because the test image used scripts with `/usr/bin/python3` shebangs while `python:3.12-alpine` exposed Python at `/usr/local/bin/python3`. Docker reported the wrapper itself as missing.

This was a fixture-packaging defect, not W3 runtime behavior. No W3 runtime byte changed. The fixture image added the interpreter symlink, and the complete direct + contained W3 gate restarted from zero before terminal predecessor replay.

## Proven W3 properties

Within the frozen fixture/interface boundary:

- supported W3 executable authority requires an absolute path;
- symlink executables are rejected;
- executable bytes are SHA-256 fingerprinted;
- bounded `--version` output is frozen into the manifest;
- executable identity is checked before and after execution;
- replacement before or during execution invalidates the run;
- invocation uses argv semantics with no shell interpolation;
- the frozen command shape includes `exec`, `--ephemeral`, `--json`, `--sandbox workspace-write`, `--ask-for-approval never`, `--ignore-user-config`, `--ignore-rules`, `--color never`, `--cd`, and stdin prompt `-`;
- forbidden high-authority Codex flags are not exposed by the adapter API;
- `CODEX_HOME` and `HOME` are fresh disposable directories;
- common API/cloud/GitHub credential variables are not passed to the fixture provider;
- prompt bytes are bounded and sent on stdin;
- stdout/stderr are file-backed and bounded;
- JSONL must be UTF-8, bounded per line/event/total size, and contain exactly one successful terminal event;
- malformed, oversized, non-UTF-8, nonzero, timeout, `turn.failed`, `error`, missing-terminal and contradictory-terminal cases reject;
- provider text claiming `PASS`, `DONE`, `CANDIDATE_VERIFIED`, `MERGE`, `DEPLOY`, or completion authority is inert;
- JSONL file-change claims never become patch authority;
- provider-local Git destruction never becomes patch authority;
- exact workspace bytes are externally validated and sent through W2's trusted collector;
- a successful Codex-shaped run can reach W1 `PROPOSAL_ACCEPTED` only;
- no F4/F5 artifact exists after W3 success;
- operator tracked state remains unchanged;
- stale W1 baseline/request authority invalidates execution;
- adapter evidence is single-write / overwrite-refusing;
- W3 contains no real credential bridge and no real network bridge;
- terminal W3 tests made no real OpenAI request;
- an explicit Codex-shaped fixture also passed while running under W2's actual `network none` Docker containment profile.

## Official-interface grounding

The W3 contract was frozen on 2026-08-12 against current official OpenAI Codex documentation for CLI/non-interactive execution, developer command flags, environment variables, sandboxing, and authentication handling.

Those external docs define the interface assumption; Forge's tests define the local authority claim. W3 does not claim OpenAI's CLI interface can never change.

## Explicit non-claims

W3 does not prove:

- that a live OpenAI Codex task can run with W2's current `--network none` boundary;
- that a real ChatGPT/Codex login token or API key can safely be injected into repository-controlled execution;
- arbitrary remote-service correctness;
- arbitrary container/kernel escape resistance;
- real model quality;
- automatic Foundation handoff;
- final PASS, merge, deploy, project-management, routing, swarm, or self-improvement authority.

## Authorization

W3 `PASS` authorizes exactly:

> **FORGE-W4 — Real Codex Pilot / Credential-Network Bridge:** design and falsify the smallest mechanism that permits one real Codex CLI request to reach OpenAI while keeping credentials outside repository-controlled execution and preserving W1/W2/Foundation authority boundaries. The first live task must still terminate at W1 `PROPOSAL_ACCEPTED` before any separate Foundation verification.

No automatic F4/F5 handoff, merge/deploy, multi-provider routing, project-management autonomy, swarm, or Roof capability is authorized.
