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
from .sealed_failures import (
    ForgeFailureError,
    close_failure,
    register_failure,
    replay_failure,
    verify_failure,
)
from .gate import ForgeGateError
from .lifecycle import ForgeLifecycleError
from .sealed_gate import run_final_gate
from .sealed_lifecycle import run_unit_attempt
from .state import ForgeStateError, init_state, load_status


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="initialize deterministic F1 canonical state")
    sub.add_parser("status", help="read and validate canonical project state")
    doctor = sub.add_parser("doctor", help="verify F3 baseline environment readiness")
    doctor.add_argument("unit_id", nargs="?")

    unit = sub.add_parser("unit", help="run the bounded F4 one-unit lifecycle")
    unit_sub = unit.add_subparsers(dest="unit_command", required=True)
    unit_run = unit_sub.add_parser("run", help="run one manually supplied patch attempt")
    unit_run.add_argument("unit_id")
    unit_run.add_argument("--patch", required=True, dest="patch_file")

    gate = sub.add_parser("gate", help="run the F5 independent final completion gate")
    gate_sub = gate.add_subparsers(dest="gate_command", required=True)
    gate_run = gate_sub.add_parser("run", help="evaluate one F4 verified candidate")
    gate_run.add_argument("unit_id")
    gate_run.add_argument("--evaluator", required=True, dest="evaluator_file")

    failure = sub.add_parser("failure", help="manage F6 permanent failure memory")
    failure_sub = failure.add_subparsers(dest="failure_command", required=True)
    failure_register = failure_sub.add_parser("register", help="freeze one serious failure")
    failure_register.add_argument("failure_id")
    failure_register.add_argument("--file", required=True, dest="spec_file")
    failure_close = failure_sub.add_parser("close", help="run all four repair-closure layers")
    failure_close.add_argument("failure_id")
    failure_close.add_argument("--candidate", required=True, dest="candidate")
    failure_replay = failure_sub.add_parser("replay", help="replay a locked permanent regression")
    failure_replay.add_argument("failure_id")
    failure_replay.add_argument("--candidate", required=True, dest="candidate")
    failure_verify = failure_sub.add_parser("verify", help="verify failure/evaluator integrity")
    failure_verify.add_argument("failure_id")

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
        elif args.command == "unit":
            if args.unit_command != "run":
                raise ForgeLifecycleError("unauthorized F4 unit command")
            result, unit_exit = run_unit_attempt(
                root, args.unit_id, Path(args.patch_file)
            )
            print(json.dumps(result, sort_keys=True))
            return unit_exit
        elif args.command == "gate":
            if args.gate_command != "run":
                raise ForgeGateError("unauthorized F5 gate command")
            result, gate_exit = run_final_gate(
                root, args.unit_id, Path(args.evaluator_file)
            )
            print(json.dumps(result, sort_keys=True))
            return gate_exit
        elif args.command == "failure":
            if args.failure_command == "register":
                record = register_failure(root, args.failure_id, Path(args.spec_file))
                result = {
                    "command": "failure.register",
                    "failure_id": record["failure_id"],
                    "status": record["status"],
                    "registration_digest": record["registration_digest"],
                }
            elif args.failure_command == "close":
                result, failure_exit = close_failure(
                    root, args.failure_id, Path(args.candidate)
                )
                print(json.dumps(result, sort_keys=True))
                return failure_exit
            elif args.failure_command == "replay":
                result, failure_exit = replay_failure(
                    root, args.failure_id, Path(args.candidate)
                )
                print(json.dumps(result, sort_keys=True))
                return failure_exit
            elif args.failure_command == "verify":
                result = {"command": "failure.verify", **verify_failure(root, args.failure_id)}
            else:
                raise ForgeFailureError("unauthorized F6 failure command")
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
    except (
        ForgeStateError,
        ForgeContractError,
        ForgeLifecycleError,
        ForgeGateError,
        ForgeFailureError,
    ) as exc:
        print(f"FORGE_ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, sort_keys=True))
    return 0
