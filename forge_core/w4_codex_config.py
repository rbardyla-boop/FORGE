from __future__ import annotations

import hashlib
from pathlib import Path
import re
import tomllib
from typing import Any
from urllib.parse import urlsplit

CONFIG_SCHEMA = "forge.w4-codex-config.v0.1"
PROVIDER_ID = "forge_broker"
PROVIDER_NAME = "Forge W4 Broker"
CAPABILITY_ENV = "FORGE_W4_CLIENT_TOKEN"
ALLOWED_BROKER_HOST = "forge-broker"
ALLOWED_BROKER_PORT = 8080
ALLOWED_BASE_URL = f"http://{ALLOWED_BROKER_HOST}:{ALLOWED_BROKER_PORT}/v1"
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class ForgeW4CodexConfigError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _validate_model(model: str) -> str:
    if not isinstance(model, str) or not MODEL_RE.fullmatch(model):
        raise ForgeW4CodexConfigError("pilot model identifier is invalid")
    return model


def _validate_base_url(base_url: str) -> str:
    if base_url != ALLOWED_BASE_URL:
        raise ForgeW4CodexConfigError("broker base URL must match frozen W4 private service endpoint")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != ALLOWED_BROKER_HOST
        or parsed.port != ALLOWED_BROKER_PORT
        or parsed.path != "/v1"
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ForgeW4CodexConfigError("broker base URL violates frozen W4 endpoint shape")
    return base_url


def render_config(*, model: str, base_url: str = ALLOWED_BASE_URL) -> bytes:
    model = _validate_model(model)
    base_url = _validate_base_url(base_url)
    text = (
        f'model = "{model}"\n'
        f'model_provider = "{PROVIDER_ID}"\n'
        'approval_policy = "never"\n'
        'sandbox_mode = "workspace-write"\n'
        '\n'
        f'[model_providers.{PROVIDER_ID}]\n'
        f'name = "{PROVIDER_NAME}"\n'
        f'base_url = "{base_url}"\n'
        f'env_key = "{CAPABILITY_ENV}"\n'
        'wire_api = "responses"\n'
        'requires_openai_auth = false\n'
        'request_max_retries = 0\n'
        'stream_max_retries = 0\n'
    )
    return text.encode("utf-8")


def expected_config(*, model: str, base_url: str = ALLOWED_BASE_URL) -> dict[str, Any]:
    model = _validate_model(model)
    base_url = _validate_base_url(base_url)
    return {
        "model": model,
        "model_provider": PROVIDER_ID,
        "approval_policy": "never",
        "sandbox_mode": "workspace-write",
        "model_providers": {
            PROVIDER_ID: {
                "name": PROVIDER_NAME,
                "base_url": base_url,
                "env_key": CAPABILITY_ENV,
                "wire_api": "responses",
                "requires_openai_auth": False,
                "request_max_retries": 0,
                "stream_max_retries": 0,
            }
        },
    }


def validate_config_bytes(data: bytes, *, model: str, base_url: str = ALLOWED_BASE_URL) -> dict[str, Any]:
    if len(data) > 64 * 1024:
        raise ForgeW4CodexConfigError("generated Codex config exceeds W4 bound")
    try:
        parsed = tomllib.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ForgeW4CodexConfigError("generated Codex config is invalid TOML") from exc
    expected = expected_config(model=model, base_url=base_url)
    if parsed != expected:
        raise ForgeW4CodexConfigError("Codex config contains unauthorized keys or values")
    return parsed


def create_codex_home(parent: Path, *, model: str, base_url: str = ALLOWED_BASE_URL) -> dict[str, Any]:
    parent = parent.resolve()
    codex_home = parent / "codex-home"
    if codex_home.exists() or codex_home.is_symlink():
        raise ForgeW4CodexConfigError("disposable CODEX_HOME already exists")
    data = render_config(model=model, base_url=base_url)
    validate_config_bytes(data, model=model, base_url=base_url)
    codex_home.mkdir(mode=0o700)
    config = codex_home / "config.toml"
    config.write_bytes(data)
    config.chmod(0o600)
    return {
        "schema": CONFIG_SCHEMA,
        "codex_home": str(codex_home),
        "config_file": str(config),
        "config_sha256": _sha256(data),
        "config_bytes": len(data),
        "model": model,
        "provider_id": PROVIDER_ID,
        "base_url": base_url,
        "capability_env": CAPABILITY_ENV,
        "auth_json_present": (codex_home / "auth.json").exists(),
    }
