from __future__ import annotations

import json
import os
from pathlib import Path

from forge_core.containment import execute_provider, probe_backend
from tests.f5_support import baseline, run_forge


def image_id() -> str:
    value = os.environ.get("FORGE_W2_IMAGE_ID", "")
    if not value.startswith("sha256:"):
        raise AssertionError("FORGE_W2_IMAGE_ID must be set to the exact local fixture image ID")
    return value


def setup_request(base: Path) -> Path:
    root = baseline(base)
    requested = run_forge(root, "proposal", "request", "U-0001")
    if requested.returncode != 0:
        raise AssertionError(requested.stderr)
    return root


def execute(root: Path, mode: str, *args: str, timeout_seconds: float = 30.0):
    return execute_provider(
        root,
        "U-0001",
        image_id(),
        [mode, *args],
        adapter_id=f"w2-fixture:{mode}",
        timeout_seconds=timeout_seconds,
    )


def execution_path(root: Path) -> Path:
    return root / ".forge/proposals/U-0001/request-0001/execution-0001/EVIDENCE.json"


def proposal_path(root: Path) -> Path:
    return root / ".forge/proposals/U-0001/request-0001/proposal-0001/PROPOSAL.json"


def stored_patch(root: Path) -> Path:
    return root / ".forge/proposals/U-0001/request-0001/proposal-0001/PATCH.diff"


def stored_trace(root: Path) -> Path:
    return root / ".forge/proposals/U-0001/request-0001/proposal-0001/TRACE.json"


def probe():
    return probe_backend(image_id(), ["probe"])


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
