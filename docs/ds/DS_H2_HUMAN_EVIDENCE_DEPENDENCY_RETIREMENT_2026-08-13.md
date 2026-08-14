# DS-H2 — Human-evidence dependency retirement

Status: **RETIRED AS DEPLOYMENT PREREQUISITE / HUMAN USABILITY NOT CLAIMED**

Date: 2026-08-13

## Decision

The five-person human-evidence gate is retired as a prerequisite for an
engineering-qualified experimental or beta release. The operating team is
limited to Ryan, ChatGPT, and Codex; no qualifying outside participant pool
is available. The project will not manufacture a human result from internal
agents or synthetic executions.

This is a governance decision, not a usability pass.

## Preserved records

- DS-H1 recruitment gate: `DS_H1_RECRUITMENT_BLOCKED`.
- Rebound human protocol: SHA-256
  `54360b4bd549a4b458288733ccdcfcaf703826a468d647f8d44a1796b44d52c1`.
- Repaired engineering candidate: commit
  `bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc`.
- DS-E1 result: `EXTERNAL_PASS / HUMAN_EVIDENCE_PENDING`.

The original H0/H1 records remain historical evidence. They are not deleted,
rewritten, or relabeled as a human pass.

## What is retired and what is not

Retired:

- human recruitment as a deployment prerequisite;
- the requirement to issue a human usability verdict when no qualifying
  participants exist.

Not retired:

- the distinction between human evidence and synthetic/operator evidence;
- the prohibition on claiming that real people understood, completed, or
  benefited from the system;
- the requirement to disclose the evidence boundary in any release decision.

## Replacement engineering gate

The replacement is **DS-X0 — Autonomous Operator Gauntlet**, run in FORGE
against a read-only snapshot of the DS-E1 candidate. It measures deterministic
engineering properties only: task completion, safe recovery, false-success
resistance, privacy, isolation, replay determinism, and candidate integrity.

The resulting terminal label may support an engineering-qualified experimental
or beta release. It may not be called `HUMAN_PASS`, `USABILITY_PASS`, or an
effectiveness result.

## Authoritative state

```text
DS-E0 / DS-E1          EXTERNAL_PASS
DS-H0                  COMPLETE
DS-H1                  RECRUITMENT_BLOCKED (historical)
DS-H2                  RETIRED_AS_DEPLOYMENT_PREREQUISITE
DS-X0                  NEXT ENGINEERING GATE
HUMAN USABILITY        NOT CLAIMED
```
