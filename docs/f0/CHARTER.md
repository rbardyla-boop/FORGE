# FORGE F0 Charter

**Unit:** FORGE-F0  
**Status:** documentation-only foundation survey  
**Production code:** forbidden  
**Authorized successor:** FORGE-F1 only after F0 PASS

## Purpose

Forge exists to make AI-assisted software development dependable for an operator who can define desired behavior but cannot personally inspect or supervise every line of generated code.

The foundation problem is not "make an AI write code." The foundation problem is to ensure that a worker cannot redefine success, lose the task, mistake structural checks for behavioral correctness, silently widen scope, or call incomplete work finished.

## Core invariant

> **No unverified behavior may be counted as completed behavior.**

A worker may propose, plan, build, diagnose, repair, and summarize. Completion authority belongs to the harness.

## FORGE-0.1 claim

> **Given a runnable software repository and a behaviorally specified change, Forge can repeatedly take the change from specification to a reviewable commit while preventing a deliberately defective implementation from reaching PASS and preserving every discovered defect as a permanent regression test.**

This is the first claim Forge is allowed to try to prove.

## Foundation construction rule

> A higher layer is authorized only after the lower layer survives deliberate attempts to break its declared guarantees.

Writing the layer is not evidence that the layer works.

## F0 objective

F0 must:

1. freeze the FORGE-0.1 claim;
2. freeze non-goals and terminal states;
3. identify candidate mechanisms from Powerplant, Cognitive OS, StackVerdict, the Agent Reliability Harness, and Gauntlet/Forge design work;
4. distinguish recoverable implementation evidence from documentation, recollection, and synthesis;
5. classify each mechanism as SALVAGE, ADAPT, REFERENCE_ONLY, DEFER, or REJECT;
6. define a reproduction test for every SALVAGE or ADAPT mechanism;
7. define the foundation / walls / roof boundary;
8. make zero production-code changes.

## F0 does not prove

F0 does not prove that any inherited mechanism works in Forge. It only establishes provenance, candidate evidence, boundaries, and future tests.

## Authority rule

No F0 document may upgrade a legacy mechanism from "documented/tested historically" to "reproduced for Forge" without a fresh replay against a pinned source snapshot.

## Next unit rule

If F0 passes, it authorizes exactly:

> **FORGE-F1 — create the deterministic repository skeleton and persistent state model, with only `forge init` and `forge status`; prove canonical state survives a new process/session.**

F0 does not authorize Doctor, AI builders, autonomous planning, multi-agent routing, deployment, or self-improvement.
