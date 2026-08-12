from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATE_DIR = ".forge"
PROJECT_FILE = "project.json"
STATE_FILE = "state.json"
PROJECT_SCHEMA = "forge.project.v0.1"
STATE_SCHEMA = "forge.state.v0.1"


class ForgeStateError(RuntimeError):
    """Canonical state is absent, corrupt, or outside the F1 schema."""


def canonical_documents(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    project = {
        "schema": PROJECT_SCHEMA,
        "project_name": root.name,
        "canonical_state_dir": STATE_DIR,
        "f0_verdict": "PASS",
        "current_unit": "F1",
        "authorized_commands": ["init", "status"],
    }
    state = {
        "schema": STATE_SCHEMA,
        "current_unit": "F1",
        "unit_state": "INITIALIZED",
        "terminal_state": None,
        "last_verified_checkpoint": None,
        "largest_remaining_gap": "prove process-loss recovery",
    }
    return project, state


def _encode(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def init_state(root: Path) -> tuple[Path, Path, bool]:
    root = root.resolve()
    state_dir = root / STATE_DIR
    if state_dir.is_symlink():
        raise ForgeStateError("canonical state directory must not be a symlink")
    if state_dir.exists() and not state_dir.is_dir():
        raise ForgeStateError("canonical state path exists but is not a directory")
    project_path = state_dir / PROJECT_FILE
    state_path = state_dir / STATE_FILE
    expected_project, expected_state = canonical_documents(root)
    expected = {
        project_path: _encode(expected_project),
        state_path: _encode(expected_state),
    }

    state_dir.mkdir(exist_ok=True)
    existing = [path for path in expected if path.exists()]
    if existing:
        if len(existing) != len(expected):
            raise ForgeStateError("partial canonical state exists; refusing to overwrite")
        for path, wanted in expected.items():
            if path.read_bytes() != wanted:
                raise ForgeStateError(
                    f"canonical state differs from F1 initialization contract: {path.name}"
                )
        return project_path, state_path, False

    for path, content in expected.items():
        path.write_bytes(content)
    return project_path, state_path, True


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ForgeStateError(f"canonical state missing: {path.name}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ForgeStateError(f"canonical state unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise ForgeStateError(f"canonical state must be a JSON object: {path.name}")
    return value


def load_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    state_dir = root / STATE_DIR
    if state_dir.is_symlink() or not state_dir.is_dir():
        raise ForgeStateError("canonical state directory is missing or unsafe")
    project_path = state_dir / PROJECT_FILE
    state_path = state_dir / STATE_FILE
    if project_path.is_symlink() or state_path.is_symlink():
        raise ForgeStateError("canonical state files must not be symlinks")
    project = _read_json(project_path)
    state = _read_json(state_path)

    required_project = {
        "schema": PROJECT_SCHEMA,
        "project_name": root.name,
        "canonical_state_dir": STATE_DIR,
        "f0_verdict": "PASS",
        "current_unit": "F1",
        "authorized_commands": ["init", "status"],
    }
    required_state = {
        "schema": STATE_SCHEMA,
        "current_unit": "F1",
        "unit_state": "INITIALIZED",
        "terminal_state": None,
        "last_verified_checkpoint": None,
        "largest_remaining_gap": "prove process-loss recovery",
    }

    if project != required_project:
        raise ForgeStateError("project.json does not match the F1 canonical schema")
    if state != required_state:
        raise ForgeStateError("state.json does not match the F1 canonical schema")

    return {
        "project_name": project["project_name"],
        "current_unit": state["current_unit"],
        "unit_state": state["unit_state"],
        "terminal_state": state["terminal_state"],
        "largest_remaining_gap": state["largest_remaining_gap"],
        "canonical_state": "VALID",
    }
