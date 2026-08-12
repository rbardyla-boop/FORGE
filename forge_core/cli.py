from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .state import ForgeStateError, init_state, load_status


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="initialize deterministic F1 canonical state")
    sub.add_parser("status", help="read and validate canonical project state")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path.cwd()
    try:
        if args.command == "init":
            project_path, state_path, created = init_state(root)
            result = {
                "command": "init",
                "created": created,
                "project_file": project_path.relative_to(root).as_posix(),
                "state_file": state_path.relative_to(root).as_posix(),
            }
        elif args.command == "status":
            result = {"command": "status", **load_status(root)}
        else:  # argparse prevents this path
            raise ForgeStateError("unauthorized F1 command")
    except ForgeStateError as exc:
        print(f"FORGE_STATE_ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, sort_keys=True))
    return 0
