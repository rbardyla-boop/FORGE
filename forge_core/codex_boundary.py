from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from . import codex_adapter as _kernel

ADAPTER_SCHEMA = _kernel.ADAPTER_SCHEMA
EXECUTION_ID = _kernel.EXECUTION_ID
CREDENTIAL_ENV_KEYS = _kernel.CREDENTIAL_ENV_KEYS
FROZEN_EXEC_ARGS = _kernel.FROZEN_EXEC_ARGS
FORBIDDEN_ARG_TOKENS = _kernel.FORBIDDEN_ARG_TOKENS
ForgeCodexAdapterError = _kernel.ForgeCodexAdapterError


def _absolute_executable(executable: Path) -> Path:
    path = Path(executable)
    if not path.is_absolute():
        raise ForgeCodexAdapterError("Codex executable path must be absolute")
    return path


def inspect_codex_executable(executable: Path) -> dict[str, Any]:
    return _kernel.inspect_codex_executable(_absolute_executable(executable))


def build_codex_argv(executable: Path, workspace: Path) -> list[str]:
    return _kernel.build_codex_argv(_absolute_executable(executable), workspace)


def events_to_w1_trace(events: Sequence[dict[str, Any]], *, adapter_id: str) -> bytes:
    return _kernel.events_to_w1_trace(events, adapter_id=adapter_id)


def execute_codex_adapter(
    root: Path,
    unit_id: str,
    executable: Path,
    manifest: dict[str, Any],
    workspace: Path,
    *,
    adapter_id: str = "codex-cli",
    fixture_mode: str | None = None,
    timeout_seconds: float = _kernel.DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], int]:
    path = _absolute_executable(executable)
    return _kernel.execute_codex_adapter(
        root,
        unit_id,
        path,
        manifest,
        workspace,
        adapter_id=adapter_id,
        fixture_mode=fixture_mode,
        timeout_seconds=timeout_seconds,
    )
