from __future__ import annotations

import json
from pathlib import Path
import shutil
import stat
import tempfile

from forge_core.codex_adapter import (
    events_to_w1_trace,
    execute_codex_adapter,
    inspect_codex_executable,
)
from forge_core.containment import _derive_patch, _validate_workspace
from forge_core.proposal import submit_proposal
from tests.f5_support import git
from tests.w2_support import setup_request

REPO_ROOT = Path(__file__).resolve().parents[1]
FAKE_CODEX_SOURCE = REPO_ROOT / "tests" / "w3_fixture" / "fake_codex.py"


def make_root(base: Path) -> Path:
    return setup_request(base)


def make_executable(base: Path, *, version: str | None = None) -> Path:
    executable = (base / "fake-codex").resolve()
    text = FAKE_CODEX_SOURCE.read_text(encoding="utf-8")
    if version is not None:
        text = text.replace('VERSION = "codex-cli 0.143.0"', f'VERSION = {version!r}')
    executable.write_text(text, encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def make_workspace(root: Path, base: Path) -> Path:
    workspace = (base / "codex-workspace").resolve()
    result = git(base, "clone", "--quiet", "--no-local", str(root), str(workspace), check=False)
    if result.returncode != 0:
        raise AssertionError((result.stdout, result.stderr))
    origin = git(workspace, "remote", "remove", "origin", check=False)
    if origin.returncode != 0:
        raise AssertionError((origin.stdout, origin.stderr))
    return workspace


def fresh_context(base: Path):
    root = make_root(base)
    workspace = make_workspace(root, base)
    executable = make_executable(base)
    manifest = inspect_codex_executable(executable)
    return root, workspace, executable, manifest


def run_mode(
    root: Path,
    workspace: Path,
    executable: Path,
    manifest: dict,
    mode: str,
    *,
    timeout_seconds: float = 20.0,
):
    return execute_codex_adapter(
        root,
        "U-0001",
        executable,
        manifest,
        workspace,
        adapter_id=f"codex-fixture:{mode}",
        fixture_mode=mode,
        timeout_seconds=timeout_seconds,
    )


def evidence_path(root: Path) -> Path:
    return root / ".forge/proposals/U-0001/request-0001/codex-execution-0001/EVIDENCE.json"


def proposal_path(root: Path) -> Path:
    return root / ".forge/proposals/U-0001/request-0001/proposal-0001/PROPOSAL.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def submit_workspace_as_w1_proposal(root: Path, workspace: Path, report: dict, base: Path):
    _validate_workspace(workspace)
    with tempfile.TemporaryDirectory(prefix="forge-w3-collector-") as collector_tmp:
        patch_bytes, changed_paths = _derive_patch(
            root,
            str(report["baseline_commit"]),
            workspace,
            Path(collector_tmp),
        )
        patch_file = base / "W3_DERIVED.patch"
        patch_file.write_bytes(patch_bytes)
        event_types = report.get("jsonl", {}).get("event_types", [])
        events = [{"type": event_type} for event_type in event_types]
        trace_file = base / "W3_TRACE.json"
        trace_file.write_bytes(events_to_w1_trace(events, adapter_id=str(report["adapter_id"])))
        proposal = submit_proposal(root, "U-0001", patch_file, trace_file)
        return proposal, changed_paths, patch_file, trace_file
