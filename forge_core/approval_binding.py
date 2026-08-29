from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any, MutableSet, Sequence


ACTION_MANIFEST_SCHEMA = "forge.research-action-manifest.v0.1"
APPROVAL_TOKEN_SCHEMA = "forge.research-action-approval.v0.1"
APPROVAL_PRESENTATION_SCHEMA = "forge.research-approval-presentation.v0.1"
MAX_ARGUMENTS = 32
MAX_ARGUMENT_BYTES = 16 * 1024
MAX_NONCE_CHARS = 256
MAX_SIGNER_CHARS = 256
MAX_APPROVAL_TTL_SECONDS = 24 * 60 * 60


class ForgeApprovalError(RuntimeError):
    """A2 approval or exact-action binding is malformed, stale, tampered, or replayed."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _digest_payload(value: dict[str, Any], digest_key: str) -> str:
    return _sha256(_canonical({key: item for key, item in value.items() if key != digest_key}))


def _validate_digest(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise ForgeApprovalError(f"{label} is not a SHA-256 digest")
    return value


def _validate_action_evaluation(evaluation: Any) -> dict[str, Any]:
    expected = {
        "schema",
        "action_id",
        "effect_class",
        "context_envelope_digest",
        "source_policy_digest",
        "template_digest",
        "proposal_digest",
        "state",
        "denied_parameters",
        "parameters",
        "execution_authority",
    }
    if not isinstance(evaluation, dict) or set(evaluation) != expected:
        raise ForgeApprovalError("A1 evaluation keys do not match expected schema")
    if evaluation["schema"] != "forge.research-action-evaluation.v0.1":
        raise ForgeApprovalError("A1 evaluation schema mismatch")
    if evaluation["state"] != "ACTION_AUTHORIZED":
        raise ForgeApprovalError("only ACTION_AUTHORIZED A1 evaluations can compile an action manifest")
    if evaluation["execution_authority"] != "none" or evaluation["denied_parameters"] != []:
        raise ForgeApprovalError("A1 evaluation authority/state is inconsistent")
    if not isinstance(evaluation["action_id"], str) or not evaluation["action_id"]:
        raise ForgeApprovalError("A1 action identity invalid")
    if not isinstance(evaluation["effect_class"], str) or not evaluation["effect_class"]:
        raise ForgeApprovalError("A1 effect class invalid")
    for label in (
        "context_envelope_digest",
        "source_policy_digest",
        "template_digest",
        "proposal_digest",
    ):
        _validate_digest(evaluation[label], label=label)
    parameters = evaluation["parameters"]
    if not isinstance(parameters, dict) or not parameters or len(parameters) > MAX_ARGUMENTS:
        raise ForgeApprovalError("A1 parameter report invalid")
    for name, report in parameters.items():
        if not isinstance(name, str) or not name:
            raise ForgeApprovalError("A1 parameter name invalid")
        if not isinstance(report, dict) or "value_sha256" not in report:
            raise ForgeApprovalError("A1 parameter report lacks value hash")
        _validate_digest(report["value_sha256"], label=f"A1 parameter {name} value hash")
    return evaluation


def compile_action_manifest(evaluation: dict[str, Any], arguments: dict[str, str]) -> dict[str, Any]:
    evaluation = _validate_action_evaluation(evaluation)
    if not isinstance(arguments, dict) or set(arguments) != set(evaluation["parameters"]):
        raise ForgeApprovalError("execution arguments must exactly match A1 parameter names")
    normalized: dict[str, str] = {}
    for name, value in arguments.items():
        if not isinstance(value, str):
            raise ForgeApprovalError("action arguments must be UTF-8 strings")
        encoded = value.encode("utf-8")
        if len(encoded) > MAX_ARGUMENT_BYTES:
            raise ForgeApprovalError("action argument exceeds byte bound")
        if _sha256(encoded) != evaluation["parameters"][name]["value_sha256"]:
            raise ForgeApprovalError(f"action argument {name} does not match A1-evaluated bytes")
        normalized[name] = value

    manifest = {
        "schema": ACTION_MANIFEST_SCHEMA,
        "action_id": evaluation["action_id"],
        "effect_class": evaluation["effect_class"],
        "arguments": normalized,
        "context_envelope_digest": evaluation["context_envelope_digest"],
        "source_policy_digest": evaluation["source_policy_digest"],
        "template_digest": evaluation["template_digest"],
        "proposal_digest": evaluation["proposal_digest"],
        "manifest_digest": None,
    }
    manifest["manifest_digest"] = _digest_payload(manifest, "manifest_digest")
    verify_action_manifest(manifest)
    return manifest


def verify_action_manifest(manifest: Any) -> dict[str, Any]:
    expected = {
        "schema",
        "action_id",
        "effect_class",
        "arguments",
        "context_envelope_digest",
        "source_policy_digest",
        "template_digest",
        "proposal_digest",
        "manifest_digest",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise ForgeApprovalError("action manifest keys do not match schema")
    if manifest["schema"] != ACTION_MANIFEST_SCHEMA:
        raise ForgeApprovalError("action manifest schema mismatch")
    if not isinstance(manifest["action_id"], str) or not manifest["action_id"]:
        raise ForgeApprovalError("action manifest identity invalid")
    if not isinstance(manifest["effect_class"], str) or not manifest["effect_class"]:
        raise ForgeApprovalError("action manifest effect class invalid")
    arguments = manifest["arguments"]
    if not isinstance(arguments, dict) or not arguments or len(arguments) > MAX_ARGUMENTS:
        raise ForgeApprovalError("action manifest arguments invalid")
    for name, value in arguments.items():
        if not isinstance(name, str) or not name or not isinstance(value, str):
            raise ForgeApprovalError("action manifest argument invalid")
        if len(value.encode("utf-8")) > MAX_ARGUMENT_BYTES:
            raise ForgeApprovalError("action manifest argument exceeds byte bound")
    for label in (
        "context_envelope_digest",
        "source_policy_digest",
        "template_digest",
        "proposal_digest",
    ):
        _validate_digest(manifest[label], label=label)
    if manifest["manifest_digest"] != _digest_payload(manifest, "manifest_digest"):
        raise ForgeApprovalError("action manifest digest mismatch")
    return manifest


def render_approval_presentation(manifest: dict[str, Any]) -> dict[str, Any]:
    verify_action_manifest(manifest)
    return {
        "schema": APPROVAL_PRESENTATION_SCHEMA,
        "action_id": manifest["action_id"],
        "effect_class": manifest["effect_class"],
        "arguments": dict(manifest["arguments"]),
        "manifest_digest": manifest["manifest_digest"],
    }


def _validate_signing_key(key: Any) -> bytes:
    if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
        raise ForgeApprovalError("approval signing key must contain at least 256 bits")
    return bytes(key)


def _signature(token: dict[str, Any], key: bytes) -> str:
    payload = {name: value for name, value in token.items() if name != "signature"}
    return f"hmac-sha256:{hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()}"


def issue_action_approval(
    manifest: dict[str, Any],
    signing_key: bytes,
    *,
    signer: str,
    nonce: str,
    issued_at: int,
    expires_at: int,
) -> dict[str, Any]:
    verify_action_manifest(manifest)
    key = _validate_signing_key(signing_key)
    if not isinstance(signer, str) or not signer.strip() or len(signer) > MAX_SIGNER_CHARS:
        raise ForgeApprovalError("approval signer identity invalid")
    if not isinstance(nonce, str) or not nonce.strip() or len(nonce) > MAX_NONCE_CHARS:
        raise ForgeApprovalError("approval nonce invalid")
    if not isinstance(issued_at, int) or isinstance(issued_at, bool) or not isinstance(expires_at, int) or isinstance(expires_at, bool):
        raise ForgeApprovalError("approval time fields must be integer epoch seconds")
    if expires_at <= issued_at or expires_at - issued_at > MAX_APPROVAL_TTL_SECONDS:
        raise ForgeApprovalError("approval validity interval invalid")
    token = {
        "schema": APPROVAL_TOKEN_SCHEMA,
        "manifest_digest": manifest["manifest_digest"],
        "signer": signer,
        "nonce": nonce,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "signature": None,
    }
    token["signature"] = _signature(token, key)
    return token


def validate_action_approval(
    manifest: dict[str, Any],
    token: Any,
    signing_key: bytes,
    *,
    now: int,
    allowed_signers: Sequence[str],
    spent_nonces: MutableSet[str] | None = None,
    consume: bool = False,
) -> dict[str, Any]:
    verify_action_manifest(manifest)
    key = _validate_signing_key(signing_key)
    expected = {"schema", "manifest_digest", "signer", "nonce", "issued_at", "expires_at", "signature"}
    if not isinstance(token, dict) or set(token) != expected:
        raise ForgeApprovalError("approval token keys do not match schema")
    if token["schema"] != APPROVAL_TOKEN_SCHEMA:
        raise ForgeApprovalError("approval token schema mismatch")
    if token["manifest_digest"] != manifest["manifest_digest"]:
        raise ForgeApprovalError("approval token is bound to a different action manifest")
    if not isinstance(token["signer"], str) or token["signer"] not in set(allowed_signers):
        raise ForgeApprovalError("approval signer is not authorized")
    if not isinstance(token["nonce"], str) or not token["nonce"].strip() or len(token["nonce"]) > MAX_NONCE_CHARS:
        raise ForgeApprovalError("approval nonce invalid")
    if not isinstance(token["issued_at"], int) or isinstance(token["issued_at"], bool) or not isinstance(token["expires_at"], int) or isinstance(token["expires_at"], bool):
        raise ForgeApprovalError("approval time fields invalid")
    if token["expires_at"] <= token["issued_at"] or token["expires_at"] - token["issued_at"] > MAX_APPROVAL_TTL_SECONDS:
        raise ForgeApprovalError("approval validity interval invalid")
    if not isinstance(now, int) or isinstance(now, bool):
        raise ForgeApprovalError("approval validation time invalid")
    if now < token["issued_at"]:
        raise ForgeApprovalError("approval token is not yet valid")
    if now > token["expires_at"]:
        raise ForgeApprovalError("approval token expired")
    signature = token["signature"]
    if not isinstance(signature, str) or re.fullmatch(r"hmac-sha256:[0-9a-f]{64}", signature) is None:
        raise ForgeApprovalError("approval signature malformed")
    if not hmac.compare_digest(signature, _signature(token, key)):
        raise ForgeApprovalError("approval signature mismatch")
    if spent_nonces is not None and token["nonce"] in spent_nonces:
        raise ForgeApprovalError("approval nonce already consumed")
    if consume:
        if spent_nonces is None:
            raise ForgeApprovalError("approval consumption requires a replay guard")
        spent_nonces.add(token["nonce"])
    return token
