# FORGE-F2 Repair 001 — absolute argv portability guard

**Status:** `PASS`  
**Discovered during:** FORGE-F3 design review  
**Affected layer:** F2 Contract Authority

## Defect

F2 documented that structured contract authority must remain machine-portable, but the check validator accepted machine-specific absolute argv path tokens such as `/usr/bin/python3`. The same gap also allowed Windows drive paths and flag-embedded absolute paths such as `--config=/tmp/config.json`.

This was a documentation/enforcement mismatch. A contract could therefore freeze successfully while carrying machine-specific execution authority that contradicted the F2 portability boundary.

## Repair

`forge_core/contract.py` now validates every check argv token and rejects:

- POSIX absolute paths;
- Windows absolute/drive paths;
- absolute filesystem paths embedded after `=` in a flag token.

Relative/name-based tokens remain valid, including:

- `python3`;
- `tools/check.py`;
- `--config=config/test.json`.

Operator-authored prose is not parsed as a filesystem authority surface; the clarified contract limits the portability rule to structured path-bearing fields.

## Permanent regression

`tests/test_f2.py` now contains:

- `test_check_argv_rejects_absolute_machine_paths`;
- `test_relative_check_argv_paths_remain_allowed`.

## Replay

After the repair:

- F2 authority suite: **14/14 PASS** in two bounded groups;
- F1 regression suite: **11/11 PASS**;
- no F3 implementation was started before this lower-layer defect was repaired.

## Verdict

F2 remains `PASS` with Repair 001 applied. F3 may resume only from the repaired F2 tree.
