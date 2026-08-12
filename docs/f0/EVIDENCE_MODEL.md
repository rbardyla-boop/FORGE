# F0 Evidence Model

F0 uses two complementary labels.

## Provenance class

- **A — Direct recovered artifact:** an inspectable document/file exists now.
- **B — Version-control evidence:** repository/commit evidence establishes that implementation or tests existed at a revision.
- **C — Operator recollection:** stated history not yet tied to a recoverable artifact.
- **D — Synthesis:** a relationship inferred across projects.
- **E — Unrecovered:** named prior work not recovered in this pass.

## Mechanism evidence level

- **E0 CONCEPT:** design idea only.
- **E1 DOCUMENTED:** committed/recovered specification describes it.
- **E2 IMPLEMENTED:** identifiable implementation source exists.
- **E3 TESTED_HISTORICALLY:** tests or historical replay evidence exists at the source revision.
- **E4 REPRODUCED_FOR_FORGE:** independently replayed during Forge salvage against a pinned snapshot.
- **E5 SALVAGE_READY:** E4 plus sufficiently bounded dependencies/interfaces for adaptation.

## Rule

E3 is not E4.

An old release document saying "tests passed" is historical evidence, not a fresh Forge reproduction.

## Pinned source snapshots

```json
{
  "claude_powerplant": {
    "repo": "rbardyla-boop/claude_powerplant",
    "ref": "master",
    "commit": "cbe4455ed86338f0e684ccad4512d7acdb3c9a8c",
    "status": "archived"
  },
  "cognitive_os": {
    "repo": "rbardyla-boop/cognitive-os",
    "ref": "master",
    "commit": "76a369fb4a47054a35736126d91d65c7c3e4fbce",
    "status": "archived"
  },
  "stackverdict": {
    "repo": "rbardyla-boop/stackverdict",
    "ref": "main",
    "commit": "4b3b3c02a9eb57c909d3342d58cee4d60be30834",
    "status": "active"
  },
  "agent_reliability_harness": {
    "source": "ChatGPT Library artifact",
    "file_id": "file_00000000f1a081f9a25dd2b88b9e5925",
    "version_id": "1",
    "evidence": "direct recovered design artifact; not a verified code repository"
  },
  "ais_provenance_map": {
    "source": "ChatGPT Library artifact",
    "file_id": "file_0000000022b8822fa9bab70521779447",
    "version_id": "1",
    "evidence": "direct recovered provenance artifact"
  }
}
```
