# FORGE F0 Provenance Map

## Source graph

```text
[A] Agent Reliability Harness
    contract / canonical external state / bounded cycles /
    mechanical completion / recovery / traces / failure->eval
                |
                v
[B] Claude Powerplant --------------------+
    containment / write ceiling /         |
    sanitized copy / evidence bundle /    |
    dogfood trust-kernel failures         |
                                         |
[B] Cognitive OS -------------------------+----> FORGE FOUNDATION
    failure ledger / adversarial QA /     |      contract -> doctor ->
    replay / behavioral governance        |      one-unit -> verify -> gate
                                         |
[B] StackVerdict -------------------------+
    frozen evaluation contracts /
    receipts / claim-vs-evidence boundary
                |
                v
[D] Current synthesis:
    software-engineering control plane for AI builders
                |
          +-----+------+
          |            |
        WALLS         ROOF
   builder/verifier   AIS/swarm
```

## Evidence classes

### A — direct recovered artifact
The Agent Reliability Harness is recoverable in the ChatGPT Library as:
- file_id: `file_00000000f1a081f9a25dd2b88b9e5925`
- version_id: `1`

It is design/governance provenance, not verified Forge code.

### B — version-control evidence

Pinned heads at F0 survey time:

- `rbardyla-boop/claude_powerplant` @ `cbe4455ed86338f0e684ccad4512d7acdb3c9a8c`
- `rbardyla-boop/cognitive-os` @ `76a369fb4a47054a35736126d91d65c7c3e4fbce`
- `rbardyla-boop/stackverdict` @ `4b3b3c02a9eb57c909d3342d58cee4d60be30834`

These repositories establish that mechanisms and historical test claims existed. Fresh Forge reproduction has not yet occurred.

### D — synthesis

The proposition that these projects are components of one missing software-engineering control plane is a current synthesis. It is useful architecture, not evidence that Forge works.

## Important non-claim

This map records recoverable internal development lineage. It does not claim public priority or invention of general agentic software-engineering concepts.

## Source artifacts consulted

### Claude Powerplant
- `README.md`
- `docs/PROJECT_CHARTER.md`
- `docs/WHAT_POWERPLANT_IS_SAFE_FOR.md`
- `docs/DOGFOOD_COVERAGE_LEDGER.md`
- `src/contracts/project-pilot-contract.ts`
- repository source-tree evidence for `src/contracts/`, `src/approvals/`, verification and run infrastructure

### Cognitive OS
- `README.md`
- `QA_PLAN.md`
- `FAILURE_LEDGER.md`
- `GOVERNANCE_MILESTONE.md`

### StackVerdict
- `README.md`
- `release/V1_1_CONTRACT.md`
- commit lineage including contract, receipt workflow, evidence comparison, release gate and reproduced CUDA verdict

### Reliability Harness / Gauntlet
- recovered ChatGPT Library artifact `file_00000000f1a081f9a25dd2b88b9e5925`, version 1
- recovered AIS provenance artifact `file_0000000022b8822fa9bab70521779447`, version 1
