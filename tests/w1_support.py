from __future__ import annotations

import json
from pathlib import Path

from tests.f5_support import baseline, correct_calc, git, make_patch, run_forge

TRACE_SCHEMA = "forge.builder-trace.v0.1"


def good_trace(base: Path, *, summary: str = "prepared bounded patch", name: str = "trace.json") -> Path:
    path = base / name
    path.write_text(
        json.dumps(
            {
                "schema": TRACE_SCHEMA,
                "adapter": "fixture-adapter",
                "provider_run_id": "fixture-run-001",
                "events": [
                    {"seq": 1, "kind": "PLAN", "summary": "inspect frozen task authority"},
                    {"seq": 2, "kind": "EDIT", "summary": summary},
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def bad_behavior_calc() -> str:
    return "def divide(a, b):\n    return a / b\n\ndef safe_divide(a, b):\n    return a / b\n"


def request(root: Path):
    return run_forge(root, "proposal", "request", "U-0001")


def submit(root: Path, patch: Path, trace: Path):
    return run_forge(
        root,
        "proposal",
        "submit",
        "U-0001",
        "--patch",
        str(patch),
        "--trace",
        str(trace),
    )


def verify(root: Path):
    return run_forge(root, "proposal", "verify", "U-0001")


def request_path(root: Path) -> Path:
    return root / ".forge/proposals/U-0001/request-0001/REQUEST.json"


def proposal_dir(root: Path) -> Path:
    return root / ".forge/proposals/U-0001/request-0001/proposal-0001"


def make_good_proposal(base: Path):
    root = baseline(base)
    requested = request(root)
    if requested.returncode != 0:
        raise AssertionError(requested.stderr)
    patch = make_patch(root, base, {"calc.py": correct_calc()}, "good.patch")
    trace = good_trace(base)
    submitted = submit(root, patch, trace)
    if submitted.returncode != 0:
        raise AssertionError(submitted.stderr)
    return root, patch, trace, json.loads(submitted.stdout)
