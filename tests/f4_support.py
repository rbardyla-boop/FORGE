from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from forge_core.lifecycle import run_unit_attempt

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_forge(
    cwd: Path, *args: str, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{REPO_ROOT}{os.pathsep}{env.get('PATH', '')}"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["forge", *args], cwd=cwd, env=env, text=True, capture_output=True, check=False
    )


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def make_repo(base: Path, files: dict[str, str]) -> Path:
    root = base / "project"
    root.mkdir()
    result = git(root, "init", "-b", "main")
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    git(root, "config", "user.name", "Forge F4 Test")
    git(root, "config", "user.email", "forge-f4@example.invalid")
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(root, "add", ".")
    committed = git(root, "commit", "-m", "fixture baseline")
    if committed.returncode != 0:
        raise AssertionError(committed.stderr)
    return root


def init_project(root: Path) -> None:
    result = run_forge(root, "init")
    if result.returncode != 0:
        raise AssertionError(result.stderr)


def required(argv: list[str], check_id: str = "CHK_001") -> dict:
    return {"id": check_id, "required": True, "argv": argv}


def advisory(argv: list[str], check_id: str = "CHK_ADV") -> dict:
    return {"id": check_id, "required": False, "argv": argv}


def authority(
    checks: list[dict],
    *,
    allowed: list[str] | None = None,
    forbidden: list[str] | None = None,
) -> dict:
    required_id = next(item["id"] for item in checks if item["required"])
    return {
        "objective": "Apply one bounded manual implementation patch",
        "deliverables": ["mode.txt"],
        "success_criteria": [
            {
                "id": "SC_001",
                "statement": "Frozen required gate remains green after the patch",
                "check_ids": [required_id],
            }
        ],
        "scope": {
            "allowed_paths": allowed or ["mode.txt", "feature.txt", "guard.txt"],
            "forbidden_paths": forbidden or [".github/**"],
        },
        "checks": checks,
        "terminal_states": ["PASS", "REPAIR_REQUIRED", "BLOCKED_EXTERNAL"],
        "non_goals": ["No AI builder"],
        "forbidden_actions": ["Do not modify operator product files"],
    }


def create_contract(
    root: Path,
    checks: list[dict],
    *,
    freeze: bool = True,
    allowed: list[str] | None = None,
    forbidden: list[str] | None = None,
) -> dict:
    source = root / "authority.json"
    source.write_text(
        json.dumps(authority(checks, allowed=allowed, forbidden=forbidden), indent=2, sort_keys=True)
        + "\n"
    )
    created = run_forge(root, "contract", "create", "U-0001", "--file", str(source))
    if created.returncode != 0:
        raise AssertionError(created.stderr)
    if not freeze:
        return json.loads(created.stdout)
    frozen = run_forge(root, "contract", "freeze", "U-0001")
    if frozen.returncode != 0:
        raise AssertionError(frozen.stderr)
    return json.loads(frozen.stdout)


def patch_file(base: Path, root: Path, relative: str, new_text: str, name: str = "change.patch") -> Path:
    old_text = (root / relative).read_text(encoding="utf-8")
    patch = "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/{relative}",
            tofile=f"b/{relative}",
        )
    )
    path = base / name
    path.write_text(patch, encoding="utf-8")
    return path


def attempt_dir(root: Path) -> Path:
    return root / ".forge/runs/U-0001/attempt-0001"


def basic_repo(base: Path) -> Path:
    return make_repo(
        base,
        {
            "mode.txt": "ok\n",
            "feature.txt": "off\n",
            "guard.txt": "guard\n",
            "outside.txt": "outside\n",
            "secret.txt": "secret\n",
            "check.py": (
                "from pathlib import Path\n"
                "import sys, time\n"
                "mode = Path('mode.txt').read_text().strip()\n"
                "if mode == 'fail' or mode == 'PASS': sys.exit(9)\n"
                "if mode == 'external':\n"
                "    print('FORGE_BLOCKED_EXTERNAL: fixture dependency', file=sys.stderr)\n"
                "    sys.exit(75)\n"
                "if mode == 'slow': time.sleep(5)\n"
                "if mode == 'mutate': Path('guard.txt').write_text('mutated\\n')\n"
            ),
            "advisory.py": "import sys\nsys.exit(22)\n",
            "restage.py": (
                "from pathlib import Path\n"
                "import subprocess\n"
                "if Path('feature.txt').read_text() == 'on\\n':\n"
                "    Path('feature.txt').write_text('re-staged\\n')\n"
                "    subprocess.run(['git', 'add', 'feature.txt'], check=True)\n"
            ),
            "mutate_contract.py": (
                "from pathlib import Path\n"
                "import json, os\n"
                "if Path('feature.txt').read_text() == 'on\\n':\n"
                "    path = Path(os.environ['F4_OPERATOR_ROOT']) / '.forge/contracts/U-0001.json'\n"
                "    record = json.loads(path.read_text())\n"
                "    record['authority']['objective'] = 'changed during attempt'\n"
                "    path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\\n')\n"
            ),
        },
    )


