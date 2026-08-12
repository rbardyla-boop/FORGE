from __future__ import annotations

import json
from pathlib import Path
import tempfile

from tests.f4_support import basic_repo, create_contract, git, init_project, patch_file, run_forge

LAYERS = (
    "MINIMAL_REPRODUCTION",
    "ORIGINAL_BROADER_CHECK",
    "UNRELATED_REGRESSIONS",
    "PERMANENT_EVALUATION",
)


def evaluator_text(*, expected: str = "fixed", fail: bool = False, mutate_when: str | None = None) -> str:
    lines = [
        "from pathlib import Path",
        "import sys",
        "root = Path(sys.argv[1])",
        "value = (root / 'bug.txt').read_text().strip()",
    ]
    if mutate_when is not None:
        lines.extend(
            [
                f"if value == {mutate_when!r}:",
                "    (root / 'bug.txt').write_text('mutated\\n')",
                "    sys.exit(0)",
            ]
        )
    if fail:
        lines.append("sys.exit(9)")
    else:
        lines.append(f"sys.exit(0 if value == {expected!r} else 9)")
    return "\n".join(lines) + "\n"


def make_candidate(base: Path, value: str = "fixed") -> Path:
    root = basic_repo(base)
    (root / "bug.txt").write_text(value + "\n")
    git(root, "add", "bug.txt")
    committed = git(root, "commit", "-m", "add F6 candidate state")
    if committed.returncode != 0:
        raise AssertionError(committed.stderr)
    init_project(root)
    return root


def write_evaluators(
    base: Path,
    *,
    fail_layer: str | None = None,
    permanent_mutate_when: str | None = None,
    expected: str = "fixed",
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for layer in LAYERS:
        path = base / f"{layer}.py"
        path.write_text(
            evaluator_text(
                expected=expected,
                fail=(layer == fail_layer),
                mutate_when=(permanent_mutate_when if layer == "PERMANENT_EVALUATION" else None),
            ),
            encoding="utf-8",
        )
        paths[layer] = str(path)
    return paths


def write_spec(base: Path, evaluators: dict[str, str]) -> Path:
    spec = {
        "unit_id": "F5-A08",
        "scenario": "Known serious defect must remain permanently reproducible",
        "expected_behavior": "All frozen repair and permanent evaluators pass",
        "observed_behavior": "Defect previously escaped a completion boundary",
        "root_cause": "test authority gap",
        "evaluators": evaluators,
    }
    path = base / "failure-spec.json"
    path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def register_failure_fixture(
    root: Path,
    base: Path,
    *,
    failure_id: str = "FAIL-F6A",
    fail_layer: str | None = None,
    permanent_mutate_when: str | None = None,
    expected: str = "fixed",
):
    evaluators = write_evaluators(
        base,
        fail_layer=fail_layer,
        permanent_mutate_when=permanent_mutate_when,
        expected=expected,
    )
    spec = write_spec(base, evaluators)
    result = run_forge(root, "failure", "register", failure_id, "--file", str(spec))
    return result, evaluators, spec


def close_failure_fixture(root: Path, failure_id: str = "FAIL-F6A"):
    return run_forge(root, "failure", "close", failure_id, "--candidate", str(root))


def replay_failure_fixture(root: Path, failure_id: str = "FAIL-F6A"):
    return run_forge(root, "failure", "replay", failure_id, "--candidate", str(root))


def locked_record(root: Path, failure_id: str = "FAIL-F6A") -> dict:
    return json.loads((root / ".forge" / "failures" / failure_id / "record.json").read_text())


def make_f4_failure_project(
    base: Path,
    *,
    accepted_feature_values: tuple[str, ...] = ("off",),
    mutate_when: str | None = None,
) -> tuple[Path, Path]:
    root = basic_repo(base)
    (root / "bug.txt").write_text("fixed\n")
    git(root, "add", "bug.txt")
    committed = git(root, "commit", "-m", "add F6 locked-regression fixture")
    if committed.returncode != 0:
        raise AssertionError(committed.stderr)
    init_project(root)
    create_contract(root, [{"id": "CHK_001", "required": True, "argv": ["python3", "check.py"]}], allowed=["feature.txt"])
    evaluators = write_evaluators(base, expected="fixed")
    # Closure layers inspect bug.txt; permanent replay is replaced before registration
    # with an evaluator for feature.txt so the baseline can lock and later patches can be challenged.
    permanent = Path(evaluators["PERMANENT_EVALUATION"])
    lines = [
        "from pathlib import Path",
        "import sys",
        "root = Path(sys.argv[1])",
        "value = (root / 'feature.txt').read_text().strip()",
    ]
    if mutate_when is not None:
        lines.extend(
            [
                f"if value == {mutate_when!r}:",
                "    (root / 'guard.txt').write_text('mutated\\n')",
                "    sys.exit(0)",
            ]
        )
    allowed_literal = repr(tuple(accepted_feature_values))
    lines.append(f"sys.exit(0 if value in {allowed_literal} else 9)")
    permanent.write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec = write_spec(base, evaluators)
    registered = run_forge(root, "failure", "register", "FAIL-F6L", "--file", str(spec))
    if registered.returncode != 0:
        raise AssertionError(registered.stderr)
    closed = run_forge(root, "failure", "close", "FAIL-F6L", "--candidate", str(root))
    if closed.returncode != 0:
        raise AssertionError(closed.stderr)
    return root, spec
