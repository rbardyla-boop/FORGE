# FORGE-0.1 Claim and Falsification Boundary

## Frozen claim

> **Given a runnable software repository and a behaviorally specified change, Forge can repeatedly take the change from specification to a reviewable commit while preventing a deliberately defective implementation from reaching PASS and preserving every discovered defect as a permanent regression test.**

## Terms

### Runnable repository
A repository for which the required runtime, dependency, build, test, and application-start assumptions are explicitly known and can be checked by the future Forge Doctor.

### Behaviorally specified change
A bounded change whose observable success and failure conditions are declared before implementation begins.

### Reviewable commit
A source change tied to:
- a frozen unit contract;
- a base revision;
- exact changed artifacts;
- executed verification evidence;
- a deterministic gate verdict;
- an independent evaluation result when required.

### Preventing defective implementation from reaching PASS
Forge must deliberately reject known bad implementations in its controlled falsification suite. This is not a universal guarantee that no unknown bug can exist.

### Permanent regression
A serious discovered failure is not considered repaired until a minimal reproduction exists and is permanently replayed by later gates.

## Falsification conditions

FORGE-0.1 fails if any of the following occurs in the controlled evaluation:

1. a known-bad patch reaches PASS;
2. a worker can weaken or delete the acceptance condition and still reach PASS;
3. a worker can change files outside the contract ceiling and still reach PASS;
4. verification runs against different bytes than those eligible for approval;
5. a previous behavior regression is not detected;
6. the worker's own completion statement can bypass failed evidence;
7. a serious defect can be "fixed" without becoming a permanent evaluation/regression;
8. canonical state cannot be reconstructed after context/process loss.

## Non-equivalence

Passing FORGE-0.1 does **not** mean:
- all software built with Forge is bug-free;
- Forge proves semantic correctness for arbitrary programs;
- an AI evaluator is infallible;
- every language or deployment environment is supported;
- autonomous software engineering is solved.
