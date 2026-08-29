from __future__ import annotations

import copy
import hashlib
import unittest

from forge_core.approval_binding import (
    ForgeApprovalError,
    compile_action_manifest,
    issue_action_approval,
    render_approval_presentation,
    validate_action_approval,
    verify_action_manifest,
)


def digest_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def fake_digest(seed: str) -> str:
    return f"sha256:{hashlib.sha256(seed.encode('utf-8')).hexdigest()}"


class ExactActionApprovalBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.arguments = {
            "recipient": "ops@example.test",
            "subject": "Status",
            "body": "Quoted untrusted material",
        }
        self.evaluation = {
            "schema": "forge.research-action-evaluation.v0.1",
            "action_id": "send_notice",
            "effect_class": "EXTERNAL_SIDE_EFFECT",
            "context_envelope_digest": fake_digest("context"),
            "source_policy_digest": fake_digest("policy"),
            "template_digest": fake_digest("template"),
            "proposal_digest": fake_digest("proposal"),
            "state": "ACTION_AUTHORIZED",
            "denied_parameters": [],
            "parameters": {
                name: {"value_sha256": digest_text(value)} for name, value in self.arguments.items()
            },
            "execution_authority": "none",
        }
        self.manifest = compile_action_manifest(self.evaluation, self.arguments)
        self.key = b"a2-trusted-approval-key-material-000000000000000000"
        self.other_key = b"a2-wrong-approval-key-material-00000000000000000000"
        self.token = issue_action_approval(
            self.manifest,
            self.key,
            signer="human:test",
            nonce="approval-001",
            issued_at=1000,
            expires_at=1100,
        )

    def validate(self, manifest=None, token=None, *, now=1050, spent=None, consume=False, allowed=None, key=None):
        return validate_action_approval(
            self.manifest if manifest is None else manifest,
            self.token if token is None else token,
            self.key if key is None else key,
            now=now,
            allowed_signers=["human:test"] if allowed is None else allowed,
            spent_nonces=spent,
            consume=consume,
        )

    def test_a2_00_exact_manifest_can_be_approved_and_validated(self) -> None:
        validated = self.validate()
        self.assertEqual(validated["manifest_digest"], self.manifest["manifest_digest"])

    def test_a2_01_and_02_argument_substitution_after_approval_rejected(self) -> None:
        for name, replacement in (("recipient", "attacker@example.test"), ("body", "changed payload")):
            manifest = copy.deepcopy(self.manifest)
            manifest["arguments"][name] = replacement
            with self.subTest(name=name):
                with self.assertRaises(ForgeApprovalError):
                    self.validate(manifest=manifest)

    def test_a2_03_effect_class_mutation_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["effect_class"] = "READ_ONLY"
        with self.assertRaises(ForgeApprovalError):
            self.validate(manifest=manifest)

    def test_a2_04_authority_digest_mutations_rejected(self) -> None:
        for field in ("context_envelope_digest", "source_policy_digest", "template_digest", "proposal_digest"):
            manifest = copy.deepcopy(self.manifest)
            manifest[field] = fake_digest(f"mutated-{field}")
            with self.subTest(field=field):
                with self.assertRaises(ForgeApprovalError):
                    self.validate(manifest=manifest)

    def test_a2_05_denied_a1_evaluation_cannot_compile_manifest(self) -> None:
        evaluation = copy.deepcopy(self.evaluation)
        evaluation["state"] = "ACTION_DENIED_PROVENANCE"
        evaluation["denied_parameters"] = ["recipient"]
        with self.assertRaises(ForgeApprovalError):
            compile_action_manifest(evaluation, self.arguments)

    def test_a2_06_execution_arguments_must_match_a1_hashes(self) -> None:
        arguments = dict(self.arguments)
        arguments["recipient"] = "attacker@example.test"
        with self.assertRaises(ForgeApprovalError):
            compile_action_manifest(self.evaluation, arguments)

    def test_a2_07_extra_or_missing_arguments_rejected(self) -> None:
        extra = dict(self.arguments)
        extra["cc"] = "other@example.test"
        missing = dict(self.arguments)
        del missing["subject"]
        for arguments in (extra, missing):
            with self.assertRaises(ForgeApprovalError):
                compile_action_manifest(self.evaluation, arguments)

    def test_a2_08_wrong_signing_key_rejected(self) -> None:
        with self.assertRaises(ForgeApprovalError):
            self.validate(key=self.other_key)

    def test_a2_09_signature_mutation_rejected(self) -> None:
        token = copy.deepcopy(self.token)
        token["signature"] = token["signature"][:-1] + ("0" if token["signature"][-1] != "0" else "1")
        with self.assertRaises(ForgeApprovalError):
            self.validate(token=token)

    def test_a2_10_and_11_signer_substitution_or_unapproved_signer_rejected(self) -> None:
        substituted = copy.deepcopy(self.token)
        substituted["signer"] = "human:mallory"
        with self.assertRaises(ForgeApprovalError):
            self.validate(token=substituted)

        mallory = issue_action_approval(
            self.manifest,
            self.key,
            signer="human:mallory",
            nonce="approval-mallory",
            issued_at=1000,
            expires_at=1100,
        )
        with self.assertRaises(ForgeApprovalError):
            self.validate(token=mallory)

    def test_a2_12_expired_token_rejected(self) -> None:
        with self.assertRaises(ForgeApprovalError):
            self.validate(now=1101)

    def test_a2_13_future_token_rejected(self) -> None:
        with self.assertRaises(ForgeApprovalError):
            self.validate(now=999)

    def test_a2_14_invalid_nonce_rejected(self) -> None:
        with self.assertRaises(ForgeApprovalError):
            issue_action_approval(
                self.manifest,
                self.key,
                signer="human:test",
                nonce="",
                issued_at=1000,
                expires_at=1100,
            )

    def test_a2_15_manifest_digest_substitution_in_token_rejected(self) -> None:
        token = copy.deepcopy(self.token)
        token["manifest_digest"] = fake_digest("other-manifest")
        with self.assertRaises(ForgeApprovalError):
            self.validate(token=token)

    def test_a2_16_and_17_consumption_is_one_shot_for_replay_guard(self) -> None:
        spent: set[str] = set()
        self.validate(spent=spent, consume=True)
        self.assertIn("approval-001", spent)
        with self.assertRaises(ForgeApprovalError):
            self.validate(spent=spent, consume=True)

    def test_a2_18_approval_for_action_a_cannot_approve_action_b(self) -> None:
        evaluation = copy.deepcopy(self.evaluation)
        evaluation["action_id"] = "send_other_notice"
        other = compile_action_manifest(evaluation, self.arguments)
        with self.assertRaises(ForgeApprovalError):
            self.validate(manifest=other)

    def test_a2_19_presentation_is_derived_only_from_manifest(self) -> None:
        presentation = render_approval_presentation(self.manifest)
        self.assertEqual(
            set(presentation),
            {"schema", "action_id", "effect_class", "arguments", "manifest_digest"},
        )
        self.assertEqual(presentation["arguments"], self.manifest["arguments"])
        self.assertEqual(presentation["manifest_digest"], self.manifest["manifest_digest"])

    def test_a2_20_canonical_argument_key_order_is_stable(self) -> None:
        reversed_arguments = dict(reversed(list(self.arguments.items())))
        other = compile_action_manifest(self.evaluation, reversed_arguments)
        self.assertEqual(other["manifest_digest"], self.manifest["manifest_digest"])

    def test_a2_21_visually_similar_unicode_is_byte_distinct(self) -> None:
        latin = "a@example.test"
        cyrillic = "\u0430@example.test"
        self.assertNotEqual(latin, cyrillic)
        eval_latin = copy.deepcopy(self.evaluation)
        args_latin = dict(self.arguments, recipient=latin)
        eval_latin["parameters"]["recipient"]["value_sha256"] = digest_text(latin)
        eval_cyrillic = copy.deepcopy(self.evaluation)
        args_cyrillic = dict(self.arguments, recipient=cyrillic)
        eval_cyrillic["parameters"]["recipient"]["value_sha256"] = digest_text(cyrillic)
        manifest_latin = compile_action_manifest(eval_latin, args_latin)
        manifest_cyrillic = compile_action_manifest(eval_cyrillic, args_cyrillic)
        self.assertNotEqual(manifest_latin["manifest_digest"], manifest_cyrillic["manifest_digest"])

    def test_a2_22_token_has_no_execution_or_completion_authority_field(self) -> None:
        self.assertNotIn("execution_authority", self.token)
        self.assertNotIn("completion_authority", self.token)
        verify_action_manifest(self.manifest)


if __name__ == "__main__":
    unittest.main()
