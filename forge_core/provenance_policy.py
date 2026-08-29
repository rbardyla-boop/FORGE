from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Sequence

from .context_grants import (
    ForgeContextGrantError,
    read_granted_content,
    verify_context_envelope,
    verify_context_grant_chain,
)


SOURCE_POLICY_SCHEMA = "forge.research-source-policy.v0.1"
ACTION_TEMPLATE_SCHEMA = "forge.research-action-template.v0.1"
ACTION_PROPOSAL_SCHEMA = "forge.research-action-proposal.v0.1"
EVALUATION_SCHEMA = "forge.research-action-evaluation.v0.1"

TRUST_LEVELS = {"UNTRUSTED": 0, "VERIFIED": 1, "CONTROL": 2}
EFFECT_CLASSES = {"READ_ONLY", "REVERSIBLE_LOCAL", "EXTERNAL_SIDE_EFFECT", "IRREVERSIBLE"}
MAX_EXPRESSION_DEPTH = 8
MAX_EXPRESSION_NODES = 64
MAX_RESOLVED_TEXT_BYTES = 16 * 1024
MAX_PARAMETERS = 32


class ForgeProvenancePolicyError(RuntimeError):
    """A1 provenance policy/proposal is malformed, stale, ambiguous, or tampered."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _digest_payload(value: dict[str, Any], digest_key: str) -> str:
    return _sha256(_canonical({key: item for key, item in value.items() if key != digest_key}))


def _validate_pattern(pattern: Any) -> str:
    if not isinstance(pattern, str) or not pattern or len(pattern) > 512 or "\x00" in pattern:
        raise ForgeProvenancePolicyError("source policy pattern must be bounded non-empty text")
    if pattern.startswith("/") or any(part in {"", ".", ".."} for part in pattern.split("/")):
        raise ForgeProvenancePolicyError("source policy pattern must be safe relative POSIX text")
    return pattern


def _path_matches(path: str, pattern: str) -> bool:
    regex: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                regex.append(".*")
                index += 2
                continue
            regex.append("[^/]*")
        elif char == "?":
            regex.append("[^/]")
        else:
            regex.append(re.escape(char))
        index += 1
    regex.append("$")
    return re.fullmatch("".join(regex), path) is not None


def create_source_policy(context_envelope: dict[str, Any], rules: Sequence[dict[str, str]]) -> dict[str, Any]:
    verify_context_envelope(context_envelope)
    if not isinstance(rules, (list, tuple)) or not rules or len(rules) > 64:
        raise ForgeProvenancePolicyError("source policy requires 1..64 rules")
    normalized: list[dict[str, str]] = []
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"pattern", "trust"}:
            raise ForgeProvenancePolicyError("source policy rule keys do not match schema")
        pattern = _validate_pattern(rule["pattern"])
        trust = rule["trust"]
        if trust not in {"UNTRUSTED", "VERIFIED"}:
            raise ForgeProvenancePolicyError("discovered-source trust must be UNTRUSTED or VERIFIED")
        normalized.append({"pattern": pattern, "trust": trust})
    policy = {
        "schema": SOURCE_POLICY_SCHEMA,
        "context_envelope_digest": context_envelope["envelope_digest"],
        "rules": normalized,
        "policy_digest": None,
    }
    policy["policy_digest"] = _digest_payload(policy, "policy_digest")
    verify_source_policy(context_envelope, policy)
    return policy


def verify_source_policy(context_envelope: dict[str, Any], policy: Any) -> dict[str, Any]:
    verify_context_envelope(context_envelope)
    expected = {"schema", "context_envelope_digest", "rules", "policy_digest"}
    if not isinstance(policy, dict) or set(policy) != expected:
        raise ForgeProvenancePolicyError("source policy keys do not match schema")
    if policy["schema"] != SOURCE_POLICY_SCHEMA:
        raise ForgeProvenancePolicyError("source policy schema mismatch")
    if policy["context_envelope_digest"] != context_envelope["envelope_digest"]:
        raise ForgeProvenancePolicyError("source policy points at wrong context envelope")
    rules = policy["rules"]
    if not isinstance(rules, list) or not rules or len(rules) > 64:
        raise ForgeProvenancePolicyError("source policy rules invalid")
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"pattern", "trust"}:
            raise ForgeProvenancePolicyError("source policy rule schema mismatch")
        _validate_pattern(rule["pattern"])
        if rule["trust"] not in {"UNTRUSTED", "VERIFIED"}:
            raise ForgeProvenancePolicyError("source policy trust invalid")
    if policy["policy_digest"] != _digest_payload(policy, "policy_digest"):
        raise ForgeProvenancePolicyError("source policy digest mismatch")
    return policy


def _classify_path(policy: dict[str, Any], path: str) -> str:
    matches = [rule["trust"] for rule in policy["rules"] if _path_matches(path, rule["pattern"])]
    if len(matches) != 1:
        raise ForgeProvenancePolicyError("source path must match exactly one trust rule")
    return matches[0]


def create_action_template(
    action_id: str,
    *,
    effect_class: str,
    parameters: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(action_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", action_id):
        raise ForgeProvenancePolicyError("action_id is invalid")
    if effect_class not in EFFECT_CLASSES:
        raise ForgeProvenancePolicyError("effect_class is invalid")
    if not isinstance(parameters, dict) or not parameters or len(parameters) > MAX_PARAMETERS:
        raise ForgeProvenancePolicyError("action template requires bounded parameters")

    normalized: dict[str, dict[str, Any]] = {}
    for name, spec in parameters.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", name):
            raise ForgeProvenancePolicyError("parameter name is invalid")
        if not isinstance(spec, dict) or set(spec) != {"min_trust", "allow_derived", "control_values"}:
            raise ForgeProvenancePolicyError("parameter policy keys do not match schema")
        min_trust = spec["min_trust"]
        if min_trust not in TRUST_LEVELS:
            raise ForgeProvenancePolicyError("parameter min_trust is invalid")
        if not isinstance(spec["allow_derived"], bool):
            raise ForgeProvenancePolicyError("allow_derived must be boolean")
        values = spec["control_values"]
        if not isinstance(values, list) or len(values) > 32:
            raise ForgeProvenancePolicyError("control_values must be a bounded list")
        for value in values:
            if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_RESOLVED_TEXT_BYTES:
                raise ForgeProvenancePolicyError("control value must be bounded text")
        normalized[name] = {
            "min_trust": min_trust,
            "allow_derived": spec["allow_derived"],
            "control_values": values,
        }

    template = {
        "schema": ACTION_TEMPLATE_SCHEMA,
        "action_id": action_id,
        "effect_class": effect_class,
        "parameters": normalized,
        "template_digest": None,
    }
    template["template_digest"] = _digest_payload(template, "template_digest")
    verify_action_template(template)
    return template


def verify_action_template(template: Any) -> dict[str, Any]:
    expected = {"schema", "action_id", "effect_class", "parameters", "template_digest"}
    if not isinstance(template, dict) or set(template) != expected:
        raise ForgeProvenancePolicyError("action template keys do not match schema")
    if template["schema"] != ACTION_TEMPLATE_SCHEMA:
        raise ForgeProvenancePolicyError("action template schema mismatch")
    if not isinstance(template["action_id"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", template["action_id"]):
        raise ForgeProvenancePolicyError("action template id invalid")
    if template["effect_class"] not in EFFECT_CLASSES:
        raise ForgeProvenancePolicyError("action template effect invalid")
    params = template["parameters"]
    if not isinstance(params, dict) or not params or len(params) > MAX_PARAMETERS:
        raise ForgeProvenancePolicyError("action template parameters invalid")
    for name, spec in params.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", name):
            raise ForgeProvenancePolicyError("action parameter name invalid")
        if not isinstance(spec, dict) or set(spec) != {"min_trust", "allow_derived", "control_values"}:
            raise ForgeProvenancePolicyError("action parameter policy schema mismatch")
        if spec["min_trust"] not in TRUST_LEVELS or not isinstance(spec["allow_derived"], bool):
            raise ForgeProvenancePolicyError("action parameter policy invalid")
        if not isinstance(spec["control_values"], list) or len(spec["control_values"]) > 32:
            raise ForgeProvenancePolicyError("action control values invalid")
        for value in spec["control_values"]:
            if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_RESOLVED_TEXT_BYTES:
                raise ForgeProvenancePolicyError("action control value invalid")
    if template["template_digest"] != _digest_payload(template, "template_digest"):
        raise ForgeProvenancePolicyError("action template digest mismatch")
    return template


def create_action_proposal(template: dict[str, Any], expressions: dict[str, Any]) -> dict[str, Any]:
    verify_action_template(template)
    if not isinstance(expressions, dict):
        raise ForgeProvenancePolicyError("proposal expressions must be an object")
    proposal = {
        "schema": ACTION_PROPOSAL_SCHEMA,
        "action_id": template["action_id"],
        "template_digest": template["template_digest"],
        "parameters": expressions,
        "proposal_digest": None,
    }
    proposal["proposal_digest"] = _digest_payload(proposal, "proposal_digest")
    return proposal


def _verify_proposal_shape(template: dict[str, Any], proposal: Any) -> dict[str, Any]:
    expected = {"schema", "action_id", "template_digest", "parameters", "proposal_digest"}
    if not isinstance(proposal, dict) or set(proposal) != expected:
        raise ForgeProvenancePolicyError("action proposal keys do not match schema")
    if proposal["schema"] != ACTION_PROPOSAL_SCHEMA:
        raise ForgeProvenancePolicyError("action proposal schema mismatch")
    if proposal["action_id"] != template["action_id"]:
        raise ForgeProvenancePolicyError("action proposal identity mismatch")
    if proposal["template_digest"] != template["template_digest"]:
        raise ForgeProvenancePolicyError("action proposal points at wrong template")
    params = proposal["parameters"]
    if not isinstance(params, dict) or set(params) != set(template["parameters"]):
        raise ForgeProvenancePolicyError("action proposal parameters do not exactly match template")
    if proposal["proposal_digest"] != _digest_payload(proposal, "proposal_digest"):
        raise ForgeProvenancePolicyError("action proposal digest mismatch")
    return proposal


def _resolve_expression(
    root: Path,
    context_envelope: dict[str, Any],
    grants: Sequence[dict[str, Any]],
    source_policy: dict[str, Any],
    spec: dict[str, Any],
    expression: Any,
    *,
    depth: int,
    budget: list[int],
) -> dict[str, Any]:
    if depth > MAX_EXPRESSION_DEPTH:
        raise ForgeProvenancePolicyError("provenance expression exceeds depth budget")
    budget[0] += 1
    if budget[0] > MAX_EXPRESSION_NODES:
        raise ForgeProvenancePolicyError("provenance expression exceeds node budget")
    if not isinstance(expression, dict) or "kind" not in expression:
        raise ForgeProvenancePolicyError("parameter expression must be a typed object")

    kind = expression["kind"]
    if kind == "CONTROL":
        if set(expression) != {"kind", "value"}:
            raise ForgeProvenancePolicyError("CONTROL expression keys do not match schema")
        value = expression["value"]
        if not isinstance(value, str) or value not in spec["control_values"]:
            raise ForgeProvenancePolicyError("CONTROL value is not an exact frozen constant")
        return {"value": value, "trust": "CONTROL", "lineage": [{"kind": "CONTROL", "value_sha256": _sha256(value.encode("utf-8"))}]}

    if kind == "GRANT":
        if set(expression) != {"kind", "sequence", "parser"}:
            raise ForgeProvenancePolicyError("GRANT expression keys do not match schema")
        if expression["parser"] != "UTF8_STRIPPED":
            raise ForgeProvenancePolicyError("unsupported grant parser")
        sequence = expression["sequence"]
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1 or sequence > len(grants):
            raise ForgeProvenancePolicyError("grant sequence does not exist")
        grant = grants[sequence - 1]
        try:
            raw = read_granted_content(root, context_envelope, grants, sequence)
        except ForgeContextGrantError as exc:
            raise ForgeProvenancePolicyError(f"A0 grant cannot be resolved: {exc}") from exc
        try:
            value = raw.decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError as exc:
            raise ForgeProvenancePolicyError("grant text parser requires valid UTF-8") from exc
        if len(value.encode("utf-8")) > MAX_RESOLVED_TEXT_BYTES:
            raise ForgeProvenancePolicyError("resolved grant text exceeds output budget")
        trust = _classify_path(source_policy, grant["resource_path"])
        return {
            "value": value,
            "trust": trust,
            "lineage": [{
                "kind": "GRANT",
                "sequence": sequence,
                "grant_digest": grant["grant_digest"],
                "resource_path": grant["resource_path"],
                "content_sha256": grant["content_sha256"],
                "trust": trust,
            }],
        }

    if kind == "CONCAT":
        if set(expression) != {"kind", "parts"}:
            raise ForgeProvenancePolicyError("CONCAT expression keys do not match schema")
        if not spec["allow_derived"]:
            raise ForgeProvenancePolicyError("derived composition is forbidden for this parameter")
        parts = expression["parts"]
        if not isinstance(parts, list) or not parts or len(parts) > MAX_EXPRESSION_NODES:
            raise ForgeProvenancePolicyError("CONCAT parts are invalid")
        resolved = [
            _resolve_expression(
                root,
                context_envelope,
                grants,
                source_policy,
                spec,
                part,
                depth=depth + 1,
                budget=budget,
            )
            for part in parts
        ]
        value = "".join(item["value"] for item in resolved)
        if len(value.encode("utf-8")) > MAX_RESOLVED_TEXT_BYTES:
            raise ForgeProvenancePolicyError("derived text exceeds output budget")
        trust = min((item["trust"] for item in resolved), key=lambda item: TRUST_LEVELS[item])
        lineage: list[dict[str, Any]] = []
        for item in resolved:
            lineage.extend(item["lineage"])
        return {"value": value, "trust": trust, "lineage": lineage}

    raise ForgeProvenancePolicyError("raw or unsupported parameter expression is forbidden")


def evaluate_action_proposal(
    root: Path,
    context_envelope: dict[str, Any],
    grants: Sequence[dict[str, Any]],
    source_policy: dict[str, Any],
    template: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    verify_context_envelope(context_envelope)
    verify_context_grant_chain(context_envelope, grants)
    verify_source_policy(context_envelope, source_policy)
    verify_action_template(template)
    _verify_proposal_shape(template, proposal)

    parameter_reports: dict[str, Any] = {}
    denied: list[str] = []
    for name, spec in template["parameters"].items():
        resolved = _resolve_expression(
            root,
            context_envelope,
            grants,
            source_policy,
            spec,
            proposal["parameters"][name],
            depth=1,
            budget=[0],
        )
        sufficient = TRUST_LEVELS[resolved["trust"]] >= TRUST_LEVELS[spec["min_trust"]]
        if not sufficient:
            denied.append(name)
        parameter_reports[name] = {
            "value_sha256": _sha256(resolved["value"].encode("utf-8")),
            "value_bytes": len(resolved["value"].encode("utf-8")),
            "derived_trust": resolved["trust"],
            "minimum_trust": spec["min_trust"],
            "trust_sufficient": sufficient,
            "lineage": resolved["lineage"],
        }

    return {
        "schema": EVALUATION_SCHEMA,
        "action_id": template["action_id"],
        "effect_class": template["effect_class"],
        "context_envelope_digest": context_envelope["envelope_digest"],
        "source_policy_digest": source_policy["policy_digest"],
        "template_digest": template["template_digest"],
        "proposal_digest": proposal["proposal_digest"],
        "state": "ACTION_AUTHORIZED" if not denied else "ACTION_DENIED_PROVENANCE",
        "denied_parameters": denied,
        "parameters": parameter_reports,
        "execution_authority": "none",
    }
