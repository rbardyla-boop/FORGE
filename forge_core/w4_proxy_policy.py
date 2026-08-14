from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

PROXY_PORT = 9090
PROXY_MAX_BYTES = 256 * 1024 * 1024
OFFICIAL_DEFAULT_UPSTREAM = "https://api.openai.com/v1/responses"
FORBIDDEN_PROXY_ARGS = {
    "--upstream-url",
    "--dump-dir",
    "--http-shutdown",
    "--server-info",
}


class ForgeW4ProxyPolicyError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def inspect_proxy_executable(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_absolute():
        raise ForgeW4ProxyPolicyError("Responses proxy executable path must be absolute")
    if path.is_symlink():
        raise ForgeW4ProxyPolicyError("Responses proxy executable must not be a symlink")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ForgeW4ProxyPolicyError("Responses proxy executable is unreadable") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ForgeW4ProxyPolicyError("Responses proxy executable must be a regular file")
        if metadata.st_size <= 0 or metadata.st_size > PROXY_MAX_BYTES:
            raise ForgeW4ProxyPolicyError("Responses proxy executable size is outside W4 bounds")
        if not metadata.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            raise ForgeW4ProxyPolicyError("Responses proxy executable is not executable")
        data = bytearray()
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > PROXY_MAX_BYTES:
                raise ForgeW4ProxyPolicyError("Responses proxy executable exceeds W4 bound")
    finally:
        os.close(descriptor)
    return {
        "schema": "forge.w4-official-proxy.v0.1",
        "path": str(path),
        "sha256": _sha256(bytes(data)),
        "bytes": len(data),
        "expected_default_upstream": OFFICIAL_DEFAULT_UPSTREAM,
    }


def build_live_proxy_argv(path: Path) -> list[str]:
    manifest = inspect_proxy_executable(path)
    argv = [manifest["path"], "--port", str(PROXY_PORT)]
    if FORBIDDEN_PROXY_ARGS.intersection(argv):
        raise ForgeW4ProxyPolicyError("frozen live proxy argv contains forbidden option")
    return argv


def verify_live_proxy_manifest(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    current = inspect_proxy_executable(path)
    if current != manifest:
        raise ForgeW4ProxyPolicyError("Responses proxy executable no longer matches frozen manifest")
    return current
