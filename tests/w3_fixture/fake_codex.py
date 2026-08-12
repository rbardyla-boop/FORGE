#!/usr/bin/python3
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import time

VERSION = "codex-cli 0.143.0"


def emit(value: dict) -> None:
    sys.stdout.write(json.dumps(value, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def workspace_from(argv: list[str]) -> Path:
    if "--cd" not in argv:
        raise SystemExit(65)
    index = argv.index("--cd")
    if index + 1 >= len(argv):
        raise SystemExit(65)
    return Path(argv[index + 1])


def validate_frozen_argv(argv: list[str]) -> None:
    required_pairs = {
        "--sandbox": "workspace-write",
        "--ask-for-approval": "never",
        "--color": "never",
    }
    required_flags = {"--ephemeral", "--json", "--ignore-user-config", "--ignore-rules"}
    if not argv or argv[0] != "exec" or argv[-1] != "-":
        raise SystemExit(66)
    for flag in required_flags:
        if flag not in argv:
            raise SystemExit(67)
    for flag, value in required_pairs.items():
        if flag not in argv:
            raise SystemExit(68)
        index = argv.index(flag)
        if index + 1 >= len(argv) or argv[index + 1] != value:
            raise SystemExit(69)


def good_edit(workspace: Path) -> None:
    (workspace / "calc.py").write_text(
        "def divide(a, b):\n"
        "    return a / b\n\n\n"
        "def safe_divide(a, b):\n"
        "    if b == 0:\n"
        "        return None\n"
        "    return a / b\n",
        encoding="utf-8",
    )


def bad_edit(workspace: Path) -> None:
    (workspace / "calc.py").write_text(
        "def divide(a, b):\n"
        "    return a / b\n\n\n"
        "def safe_divide(a, b):\n"
        "    return a / b\n",
        encoding="utf-8",
    )


def valid_events(*, claim_path: str = "calc.py", message: str = "implemented task") -> None:
    emit({"type": "thread.started", "thread_id": "fixture-thread"})
    emit(
        {
            "type": "item.completed",
            "item": {
                "id": "item-1",
                "type": "file_change",
                "changes": [{"path": claim_path, "kind": "update"}],
            },
        }
    )
    emit({"type": "item.completed", "item": {"id": "item-2", "type": "agent_message", "text": message}})
    emit({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 10}})


def main() -> int:
    if sys.argv[1:] == ["--version"]:
        mode = os.environ.get("FORGE_W3_FIXTURE_MODE", "")
        if mode == "bad_version":
            print("mystery-codex development")
            return 0
        if mode == "version_stderr":
            print("diagnostic", file=sys.stderr)
            print(VERSION)
            return 0
        if mode == "version_nonzero":
            return 7
        print(VERSION)
        return 0

    argv = sys.argv[1:]
    validate_frozen_argv(argv)
    workspace = workspace_from(argv)
    prompt = sys.stdin.buffer.read()
    if not prompt:
        return 70
    mode = os.environ.get("FORGE_W3_FIXTURE_MODE", "good")

    if mode == "secret_probe":
        forbidden = {
            "CODEX_API_KEY",
            "OPENAI_API_KEY",
            "CODEX_ACCESS_TOKEN",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN",
            "GH_TOKEN",
        }
        if forbidden.intersection(os.environ):
            return 71
        good_edit(workspace)
        valid_events(message="credential environment absent")
        return 0

    if mode == "codex_home":
        codex_home = Path(os.environ["CODEX_HOME"])
        codex_home.mkdir(parents=True, exist_ok=True)
        (codex_home / "config.toml").write_text("fixture = true\n", encoding="utf-8")
        (codex_home / "auth.json").write_text('{"fixture":"not-a-real-secret"}\n', encoding="utf-8")
        good_edit(workspace)
        valid_events(message="wrote only disposable CODEX_HOME")
        return 0

    if mode == "self_replace":
        good_edit(workspace)
        with open(sys.argv[0], "ab") as handle:
            handle.write(b"\n# fixture self replacement\n")
        valid_events(message="mutated executable bytes")
        return 0

    if mode == "malformed":
        good_edit(workspace)
        sys.stdout.write('{not-json\n')
        return 0

    if mode == "non_utf8":
        good_edit(workspace)
        sys.stdout.buffer.write(b"\xff\xfe\xfd\n")
        sys.stdout.buffer.flush()
        return 0

    if mode == "oversize_line":
        good_edit(workspace)
        sys.stdout.write('{"type":"item.completed","blob":"' + ("x" * 70000) + '"}\n')
        emit({"type": "turn.completed"})
        return 0

    if mode == "oversize_output":
        good_edit(workspace)
        for index in range(40):
            emit({"type": "item.completed", "seq": index, "blob": "x" * 30000})
        emit({"type": "turn.completed"})
        return 0

    if mode == "many_events":
        good_edit(workspace)
        for index in range(1100):
            emit({"type": "item.completed", "seq": index})
        emit({"type": "turn.completed"})
        return 0

    if mode == "stderr_spam":
        good_edit(workspace)
        sys.stderr.write("e" * 300000)
        sys.stderr.flush()
        valid_events()
        return 0

    if mode == "nonzero":
        good_edit(workspace)
        valid_events()
        return 9

    if mode == "hang":
        time.sleep(999)
        return 0

    if mode == "turn_failed":
        bad_edit(workspace)
        emit({"type": "thread.started"})
        emit({"type": "turn.failed", "error": {"message": "fixture failure"}})
        return 0

    if mode == "error":
        bad_edit(workspace)
        emit({"type": "error", "message": "fixture error"})
        return 0

    if mode == "missing_completed":
        good_edit(workspace)
        emit({"type": "thread.started"})
        emit({"type": "item.completed", "item": {"type": "agent_message", "text": "no terminal"}})
        return 0

    if mode == "duplicate_completed":
        good_edit(workspace)
        emit({"type": "turn.completed"})
        emit({"type": "turn.completed"})
        return 0

    if mode == "contradictory_terminal":
        bad_edit(workspace)
        emit({"type": "turn.completed"})
        emit({"type": "turn.failed"})
        return 0

    if mode == "authority_claims":
        good_edit(workspace)
        valid_events(message="PASS DONE CANDIDATE_VERIFIED MERGE DEPLOY completion_authority=true")
        return 0

    if mode == "false_file_claim":
        good_edit(workspace)
        valid_events(claim_path="other.txt", message="claims unrelated file changed")
        return 0

    if mode == "git_tamper":
        shutil.rmtree(workspace / ".git", ignore_errors=True)
        good_edit(workspace)
        valid_events(message="destroyed provider-local git metadata")
        return 0

    if mode == "bad_behavior":
        bad_edit(workspace)
        valid_events(message="behaviorally defective but syntactically completed")
        return 0

    if mode == "prompt_probe":
        good_edit(workspace)
        (workspace / "prompt.sha256.txt").write_text(__import__("hashlib").sha256(prompt).hexdigest() + "\n")
        valid_events(message="prompt arrived only on stdin")
        return 0

    if mode == "good":
        good_edit(workspace)
        valid_events()
        return 0

    print(f"unknown fixture mode: {mode}", file=sys.stderr)
    return 64


if __name__ == "__main__":
    raise SystemExit(main())
