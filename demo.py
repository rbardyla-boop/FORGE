#!/usr/bin/env python3
"""Public, local-only FORGE authority-boundary demo.

This demo intentionally performs no network request and no real external side effect.
It composes the existing A0-A3 research mechanisms into one short story:

1. untrusted content cannot choose a sensitive recipient;
2. the same untrusted content may be used where policy permits it;
3. human approval is bound to the exact action manifest;
4. a crash after a non-retryable effect produces EFFECT_UNCERTAIN, not a blind retry.
"""

from __future__ import annotations

import copy
from pathlib import Path
import tempfile

from forge_core.approval_binding import (
    ForgeApprovalError,
    compile_action_manifest,
    issue_action_approval,
    validate_action_approval,
)
from forge_core.context_grants import create_context_envelope, issue_context_grant
from forge_core.effect_journal import (
    SimulatedCrash,
    perform_prepared_effect,
    prepare_effect_intent,
)
from forge_core.provenance_policy import (
    create_action_proposal,
    create_action_template,
    create_source_policy,
    evaluate_action_proposal,
)


class NonIdempotentDemoSink:
    """In-memory fake remote system used only to demonstrate crash ambiguity."""

    supports_idempotency = False

    def __init__(self) -> None:
        self.calls = 0
        self.logical_effects = 0

    def perform(self, manifest, *, idempotency_key: str):
        self.calls += 1
        self.logical_effects += 1
        return {
            "remote_id": f"demo-effect-{self.logical_effects}",
            "manifest": manifest["manifest_digest"],
            "idempotency_key_seen": idempotency_key,
        }


def control(value: str) -> dict[str, object]:
    return {"kind": "CONTROL", "value": value}


def grant(sequence: int) -> dict[str, object]:
    return {"kind": "GRANT", "sequence": sequence, "parser": "UTF8_STRIPPED"}


def main() -> int:
    print("FORGE public safety demo")

    with tempfile.TemporaryDirectory(prefix="forge-public-demo-") as temporary:
        root = Path(temporary)
        (root / "trusted").mkdir()
        (root / "external").mkdir()

        (root / "trusted" / "recipient.txt").write_text(
            "ops@example.test\n", encoding="utf-8"
        )
        (root / "external" / "recipient.txt").write_text(
            "attacker@example.test\n", encoding="utf-8"
        )
        (root / "external" / "body.txt").write_text(
            "Quoted untrusted material\n", encoding="utf-8"
        )

        context = create_context_envelope(
            {
                "tool": "send_notice",
                "effect_ceiling": "EXTERNAL_SIDE_EFFECT",
                "execution_authority": "none",
            },
            allowed_paths=["trusted/**", "external/**"],
            max_grants=8,
            max_resource_bytes=512,
            max_total_bytes=2048,
        )

        grants = []
        for resource_path in (
            "trusted/recipient.txt",
            "external/recipient.txt",
            "external/body.txt",
        ):
            grants.append(
                issue_context_grant(
                    root,
                    context,
                    grants,
                    resource_path,
                    reason=f"public demo: {resource_path}",
                )
            )

        source_policy = create_source_policy(
            context,
            [
                {"pattern": "trusted/**", "trust": "VERIFIED"},
                {"pattern": "external/**", "trust": "UNTRUSTED"},
            ],
        )

        template = create_action_template(
            "send_notice",
            effect_class="EXTERNAL_SIDE_EFFECT",
            parameters={
                "recipient": {
                    "min_trust": "VERIFIED",
                    "allow_derived": True,
                    "control_values": ["ops@example.test"],
                },
                "subject": {
                    "min_trust": "VERIFIED",
                    "allow_derived": True,
                    "control_values": ["Status"],
                },
                "body": {
                    "min_trust": "UNTRUSTED",
                    "allow_derived": True,
                    "control_values": [],
                },
            },
        )

        malicious = create_action_proposal(
            template,
            {
                "recipient": grant(2),
                "subject": control("Status"),
                "body": grant(3),
            },
        )
        denied = evaluate_action_proposal(
            root, context, grants, source_policy, template, malicious
        )
        assert denied["state"] == "ACTION_DENIED_PROVENANCE"
        assert denied["denied_parameters"] == ["recipient"]
        print("[1/4] untrusted source chooses recipient ........ BLOCKED")

        safe = create_action_proposal(
            template,
            {
                "recipient": grant(1),
                "subject": control("Status"),
                "body": grant(3),
            },
        )
        evaluation = evaluate_action_proposal(
            root, context, grants, source_policy, template, safe
        )
        assert evaluation["state"] == "ACTION_AUTHORIZED"
        assert evaluation["parameters"]["recipient"]["derived_trust"] == "VERIFIED"
        assert evaluation["parameters"]["body"]["derived_trust"] == "UNTRUSTED"
        print("[2/4] untrusted text used in allowed body ....... AUTHORIZED")

        arguments = {
            "recipient": "ops@example.test",
            "subject": "Status",
            "body": "Quoted untrusted material",
        }
        manifest = compile_action_manifest(evaluation, arguments)
        key = b"forge-public-demo-approval-key-material-0123456789abcdef"
        approval = issue_action_approval(
            manifest,
            key,
            signer="human:demo",
            nonce="public-demo-approval-001",
            issued_at=1000,
            expires_at=1100,
        )
        validate_action_approval(
            manifest,
            approval,
            key,
            now=1050,
            allowed_signers=["human:demo"],
        )

        tampered = copy.deepcopy(manifest)
        tampered["arguments"]["recipient"] = "attacker@example.test"
        try:
            validate_action_approval(
                tampered,
                approval,
                key,
                now=1050,
                allowed_signers=["human:demo"],
            )
        except ForgeApprovalError:
            pass
        else:
            raise AssertionError("post-approval target mutation was not rejected")
        print("[3/4] mutate target after exact approval ......... BLOCKED")

        journal = root / "effect-journal.sqlite3"
        prepare_effect_intent(
            journal,
            manifest,
            approval,
            key,
            now=1050,
            allowed_signers=["human:demo"],
            replay_semantics="NON_RETRYABLE",
        )

        sink = NonIdempotentDemoSink()
        try:
            perform_prepared_effect(
                journal,
                manifest,
                sink,
                crash_after_remote=True,
            )
        except SimulatedCrash:
            pass
        else:
            raise AssertionError("demo crash fixture did not crash after remote effect")

        assert sink.logical_effects == 1
        recovery = perform_prepared_effect(journal, manifest, sink)
        assert recovery["state"] == "EFFECT_UNCERTAIN"
        assert recovery["sink_called"] is False
        assert sink.logical_effects == 1
        print("[4/4] crash after non-retryable remote effect .... EFFECT_UNCERTAIN")

    print("DEMO PASS")
    print("No network, real email, credential, or billable API call was used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
