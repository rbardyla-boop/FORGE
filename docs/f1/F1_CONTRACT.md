# FORGE-F1 Contract

**Unit:** FORGE-F1  
**Authorized by:** FORGE-F0 PASS  
**Scope:** persistent skeleton only

## Objective

Create the smallest executable Forge skeleton that can initialize canonical project state and reconstruct that state from a completely new process without conversation context.

## Allowed implementation surface

- `pyproject.toml`
- `forge/__init__.py`
- `forge/__main__.py`
- `forge/cli.py`
- `forge/state.py`
- `tests/test_f1.py`
- `docs/f1/F1_CONTRACT.md`
- `docs/f1/F1_VERDICT.md` after verification

## Authorized commands

- `forge init`
- `forge status`

No other Forge command is authorized in F1.

## Canonical state

F1 may create only these project-state artifacts:

- `.forge/project.json`
- `.forge/state.json`

The files must be deterministic for the same repository name and F1 schema. F1 must not store conversation transcripts, model reasoning, timestamps, random identifiers, network-derived data, or machine-specific absolute paths.

## Acceptance criteria

F1 is correct only if all of the following pass:

1. `forge init` creates exactly the two authorized `.forge` state files.
2. The state files parse as JSON and match the frozen schemas/values expected by F1.
3. Running `forge init` again does not mutate either file.
4. `forge status` reads canonical state from disk and reports it without consulting conversation context.
5. A completely new Python process can run `forge status` after the initializing process exits and recover the same project name, current unit, unit state, terminal state, and largest remaining gap.
6. Corrupt or incomplete canonical state produces a non-zero exit and never a fabricated status.
7. F1 adds no network access, model/API integration, database, autonomous planning, Doctor behavior, verification engine, or additional commands.

## Falsification conditions

F1 fails if:

- state exists only in process memory;
- `status` succeeds with missing/corrupt state;
- a second `init` silently rewrites existing canonical state;
- state contains machine-specific or nondeterministic data;
- any unauthorized command or production subsystem is introduced.

## Terminal states

- `PASS`
- `REPAIR_REQUIRED`
- `BLOCKED_EXTERNAL`
- `ABANDONED_BY_OWNER`

## Next-unit boundary

F1 PASS may authorize F2 Contract Authority. It does not authorize F3 Doctor or any AI builder.

## Amendment F1-A1 — zero-dependency launcher

**Reason:** the first packaging check showed that a fresh offline virtual environment could fail before Forge ran because pip attempted to provision a PEP 517 build backend. That dependency is unnecessary for F1 and would make the first executable brick less reliable.

**Approved scope change:**

- retire `pyproject.toml` from F1;
- replace the import package directory `forge/` with `forge_core/`;
- add one executable repository-root launcher named `forge`;
- tests must invoke `forge` as an executable through `PATH`, not through pip installation or in-process imports.

This amendment does not add a new Forge command or capability. It removes a packaging dependency and strengthens the F1 acceptance boundary.
