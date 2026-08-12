from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .contract import (
    ForgeContractError,
    amend_contract,
    contract_ready,
    create_contract,
    freeze_contract,
    verify_contract,
)
from .doctor import run_doctor
from .state import ForgeStateError, init_state, load_status


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="initialize deterministic F1 canonical state")
    sub.add_parser("status", help="read and validate canonical project state")
    doctor = sub.add_parser("doctor", help="verify F3 baseline environment readiness")
    doctor.add_argument("unit_id", nargs="?")

    contract = sub.add_parser("contract", help="manage frozen F2 work-unit authority")
    contract_sub = contract.add_subparsers(dest="contract_command", required=True)

    create = contract_sub.add_parser("create", help="create a draft unit contract")
    create.add_argument("unit_id")
    create.add_argument("--file", required=True, dest="authority_file")

    freeze = contract_sub.add_parser("freeze", help="freeze a draft contract")
    freeze.add_argument("unit_id")

    verify = contract_sub.add_parser("verify", help="verify frozen contract integrity")
    verify.add_argument("unit_id")

    ready = contract_sub.add_parser("ready", help="check implementation eligibility")
    ready.add_argument("unit_id")

    amend = contract_sub.add_parser("amend", help="create an explicit next revision")
    amend.add_argument("unit_id")
    amend.add_argument("--file", required=True, dest="authority_file")
    amend.add_argument("--reason", required=True)
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
        elif args.command == "doctor":
            if args.unit_id is None:
                raise ForgeContractError("invalid choice: doctor requires UNIT")
            result, doctor_exit = run_doctor(root, args.unit_id)
            print(json.dumps(result, sort_keys=True))
            return doctor_exit
        elif args.command == "contract":
            if args.contract_command == "create":
                record = create_contract(root, args.unit_id, Path(args.authority_file))
                result = {
                    "command": "contract.create",
                    "unit_id": record["unit_id"],
                    "revision": record["revision"],
                    "state": record["state"],
                }
            elif args.contract_command == "freeze":
                record = freeze_contract(root, args.unit_id)
                result = {
                    "command": "contract.freeze",
                    "unit_id": record["unit_id"],
                    "revision": record["revision"],
                    "state": record["state"],
                    "contract_digest": record["contract_digest"],
                }
            elif args.contract_command == "verify":
                result = {"command": "contract.verify", **verify_contract(root, args.unit_id)}
            elif args.contract_command == "ready":
                result = {"command": "contract.ready", **contract_ready(root, args.unit_id)}
            elif args.contract_command == "amend":
                record = amend_contract(
                    root, args.unit_id, Path(args.authority_file), args.reason
                )
                result = {
                    "command": "contract.amend",
                    "unit_id": record["unit_id"],
                    "revision": record["revision"],
                    "state": record["state"],
                    "parent_digest": record["parent_digest"],
                }
            else:
                raise ForgeContractError("unauthorized F2 contract command")
        else:
            raise ForgeStateError("unauthorized Forge command")
    except (ForgeStateError, ForgeContractError) as exc:
        print(f"FORGE_ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, sort_keys=True))
    return 0
