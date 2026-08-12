# FORGE-W3 Contract — Codex Adapter Boundary

**Unit:** FORGE-W3
**Layer:** Walls / third unit
**State:** FROZEN BEFORE IMPLEMENTATION
**Base:** canonical FORGE-W2 `PASS`
**Real remote Codex inference:** forbidden until the W3 fixture gate passes
**Automatic Foundation handoff:** forbidden
**Merge/deploy authority:** forbidden

## Objective

Prove that Forge can represent and invoke the current OpenAI Codex CLI through a deterministic, inspectable, provider-specific adapter without giving the provider credential authority, configuration authority, completion authority, or a route around W1/W2/Foundation.

W3 is the **Codex adapter boundary**, not yet the real-provider production pilot.

A W3 `PASS` means that a Codex-shaped executable can be fingerprinted, invoked with a frozen non-interactive argument contract, fed only the sealed task prompt/workspace, observed through bounded JSONL events, and converted back into the existing W2→W1 proposal path without trusting provider self-reports.

A W3 `PASS` does **not** mean a real OpenAI inference request has occurred. The first live remote Codex task is a separate successor gate.

## Current official interface assumptions frozen on 2026-08-12

Primary OpenAI documentation consulted before this contract was frozen:

- Codex CLI: https://developers.openai.com/codex/cli
- Non-interactive mode: https://developers.openai.com/codex/non-interactive-mode
- Developer command reference: https://learn.chatgpt.com/docs/developer-commands?surface=cli
- Codex environment variables: https://developers.openai.com/codex/config-file/environment-variables
- Codex sandboxing: https://developers.openai.com/codex/sandboxing

The current documented automation surface establishes that:

1. `codex exec` is the stable non-interactive command for scripted/CI-style work.
2. `--json` emits newline-delimited JSON events.
3. `--ephemeral` suppresses persisted rollout/session files.
4. `--ignore-user-config` prevents ambient `$CODEX_HOME/config.toml` from changing the run; authentication may still use `CODEX_HOME`.
5. `--ignore-rules` prevents ambient user/project execpolicy rules from silently changing the run.
6. `--sandbox workspace-write` is the explicit editing sandbox; `danger-full-access` is not authorized by W3.
7. `--cd` sets the workspace root.
8. Codex can read a prompt from stdin using `-`.
9. `CODEX_API_KEY` is supported for a single `codex exec`, but OpenAI explicitly warns not to expose API keys to automation environments that run repository-controlled code.
10. Saved `~/.codex/auth.json` contains access tokens and must be treated like a password.

These are **interface assumptions**, not Forge security claims. W3 must fail closed if the installed executable no longer exposes the frozen interface.

## Critical credential decision

W3 SHALL NOT:

- copy or mount the operator's real `~/.codex/auth.json` into a provider workspace;
- persist `CODEX_API_KEY`, `OPENAI_API_KEY`, `CODEX_ACCESS_TOKEN`, OAuth tokens, refresh tokens, or ChatGPT credentials in `.forge`, Git, test fixtures, traces, request files, proposal files, logs, stdout captures, or provider workspace files;
- set a real API/access token in a fixture provider process;
- rely on a job-wide secret environment variable;
- claim that W2 `--network none` can perform a real remote Codex inference.

The live credential/network bridge therefore remains **unauthorized and unresolved in W3**.

W3's fixture gate uses no secret and no external network. A successful W3 authorizes design of the first live-pilot credential/network bridge as a separate unit.

## Why the live call is separate

W2 deliberately proves a provider boundary with no outbound network. Real OpenAI Codex requires remote service connectivity unless a local provider mode is selected. Simply turning Docker networking back on would silently invalidate W2's proven containment claim.

Likewise, directly injecting an API key or mounted login token into a coding-agent environment would violate the credential separation required by this project and contradict OpenAI's automation guidance about repository-controlled code.

Therefore the live pilot must solve network and credential brokerage explicitly rather than smuggling them into W3.

## Executable authority

W3 accepts a Codex executable only when all are true:

- caller supplies an **absolute path**;
- path is a regular non-symlink executable file;
- executable bytes are SHA-256 hashed before invocation;
- the hash and a bounded `--version` result are recorded in adapter evidence;
- executable bytes are re-hashed immediately before every task invocation;
- executable bytes are re-hashed after the invocation;
- any hash change invalidates the run;
- W3 never downloads, updates, installs, or searches `PATH` for Codex during a task run.

Acquisition/update is an operator/admin action outside W3.

## Frozen Codex invocation contract

The fixture adapter must construct the semantic equivalent of:

```text
<ABSOLUTE_CODEX_PATH> exec
  --ephemeral
  --json
  --sandbox workspace-write
  --ask-for-approval never
  --ignore-user-config
  --ignore-rules
  --color never
  --cd <DISPOSABLE_WORKSPACE>
  -
```

The task prompt is supplied on stdin, not interpolated into a shell command.

The adapter SHALL:

- use `shell=False` / argv execution semantics;
- never use `--yolo`, `--dangerously-bypass-approvals-and-sandbox`, `danger-full-access`, `--full-auto`, `--dangerously-bypass-hook-trust`, `--skip-git-repo-check`, `--profile`, `--add-dir`, image input, MCP configuration, plugins, cloud commands, resume, or arbitrary `-c` overrides;
- run from a disposable Git repository/workspace supplied by the containment layer;
- use a bounded timeout;
- capture stdout/stderr to bounded files rather than unbounded memory;
- treat all Codex stdout/stderr and JSONL event content as **untrusted evidence**.

`approval_policy=never` is acceptable only because W3 itself grants no external escalation route: W2 remains the outer authority boundary and the fixture has no network or credentials. A future live pilot may revise this only by explicit amendment.

## Environment contract

Fixture execution environment is allowlisted, not inherited wholesale.

Allowed provider-facing environment entries are limited to variables required for deterministic process/runtime operation and fixture identification. The W3 fixture must prove that common credential variables are absent, including at minimum:

```text
CODEX_API_KEY
OPENAI_API_KEY
CODEX_ACCESS_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
GITHUB_TOKEN
GH_TOKEN
```

`CODEX_HOME` may point only to a fresh disposable empty directory created for the run. No operator Codex state is copied into it.

## JSONL evidence contract

W3 parses stdout line-by-line with hard limits.

For the frozen fixture protocol:

- every non-empty stdout line must be valid UTF-8 JSON object;
- event count and total stdout bytes are bounded;
- unknown event types are recorded but cannot create authority;
- malformed JSON, oversized lines/output, duplicate terminal events, or contradictory terminal state cause rejection;
- at least one terminal `turn.completed` event is required for provider-success classification;
- any `turn.failed` or top-level `error` event prevents provider-success classification;
- provider text such as `PASS`, `DONE`, `MERGE`, `DEPLOY`, `CANDIDATE_VERIFIED`, or `completion_authority` is inert text only;
- token/usage fields are evidence only and are never completion authority.

W3 never derives the patch from JSONL `file_change` claims. Workspace bytes remain authoritative through W2's independent filesystem/collector path.

## W2/W1 handoff

The Codex adapter does not create a second proposal system.

The required composition is:

```text
W1 frozen request
    ↓
W2 disposable contained workspace
    ↓
W3 Codex-shaped invocation adapter
    ↓
untrusted Codex JSONL + workspace mutations
    ↓
W2 external workspace validation + trusted patch derivation
    ↓
W1 proposal validation
    ↓
PROPOSAL_ACCEPTED only
```

The Codex adapter must not call F4/F5 directly and must not create `CANDIDATE_VERIFIED` or `PASS` artifacts.

## Fixture provider requirement

Before any real Codex remote inference, W3 must ship a deterministic fake `codex` executable that supports only enough of the frozen interface to attack the adapter.

Fixture modes must cover at minimum:

- correct version + valid JSONL + scoped edit;
- executable symlink/replacement/hash drift;
- unsupported/changed CLI version surface;
- argv injection attempt through prompt/unit metadata;
- secret-environment probe;
- attempted writes outside supplied workspace;
- malformed JSONL;
- non-UTF-8 stdout;
- oversized stdout/event count/line;
- stderr spam;
- nonzero exit;
- timeout/hang;
- `turn.failed`;
- top-level `error` event;
- missing `turn.completed`;
- duplicate/contradictory terminal events;
- fake `PASS/MERGE/DEPLOY` claims;
- fake JSONL file-change claims that do not match workspace bytes;
- local Git destruction/tamper;
- attempt to write into disposable `CODEX_HOME` and treat it as authority;
- parent/operator repository unchanged after every run.

## W3 direct falsification gate

At minimum W3 must prove:

```text
A00 exact executable fingerprint
A01 non-symlink absolute executable only
A02 executable replacement before run rejected
A03 executable replacement during/after run rejected
A04 exact frozen argv generated
A05 prompt delivered by stdin; no shell interpolation
A06 forbidden Codex flags impossible through adapter API
A07 ambient user config ignored
A08 ambient execpolicy rules ignored
A09 disposable CODEX_HOME only
A10 credential environment absent
A11 provider stdout bounded
A12 provider stderr bounded
A13 malformed JSONL rejected
A14 oversized JSONL rejected
A15 non-UTF-8 JSONL rejected
A16 nonzero provider exit rejected
A17 timeout kills run and cleans process
A18 turn.failed rejected
A19 error event rejected
A20 missing turn.completed rejected
A21 duplicate/contradictory terminal events rejected
A22 provider PASS/DONE/MERGE/DEPLOY claims inert
A23 provider file-change claims never become patch authority
A24 provider-local Git tamper has no patch authority
A25 exact workspace bytes still feed W2 trusted collector
A26 successful Codex-shaped run reaches PROPOSAL_ACCEPTED only
A27 no F4/F5 artifact exists after W3 success
A28 operator tracked state unchanged
A29 W1 request/contract/F6 drift invalidates run
A30 adapter evidence cannot be overwritten
A31 no network/credential bridge exists in W3
A32 no real Codex remote request occurs in terminal W3 tests
```

All attacks are preregistered before terminal execution. Any new serious failure becomes a named permanent regression before W3 can pass.

## Terminal states

W3 uses the existing Forge vocabulary:

- `PASS`
- `REPAIR_REQUIRED`
- `BLOCKED_EXTERNAL`
- `SEALED_NEGATIVE_RESULT`

A missing real credential/network bridge is **not** a W3 failure because real inference is explicitly outside this unit. W3 may pass only the adapter-boundary claim above.

## W3 PASS authorization

W3 `PASS` authorizes exactly:

> **FORGE-W4 — Real Codex Pilot / Credential-Network Bridge:** design and falsify a narrow mechanism that lets the real Codex CLI reach OpenAI while keeping credentials outside repository-controlled execution, then run one bounded real task whose result still terminates only at W1 `PROPOSAL_ACCEPTED` before Foundation verification.

No automatic F4/F5 handoff, merge, deploy, multi-provider routing, project-management autonomy, swarm, or Roof capability is authorized by W3.
