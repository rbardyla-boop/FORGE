from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from forge_core.context_grants import create_context_envelope, issue_context_grant
from forge_core.provenance_policy import (
    ForgeProvenancePolicyError,
    create_action_proposal,
    create_action_template,
    create_source_policy,
    evaluate_action_proposal,
    verify_action_template,
    verify_source_policy,
)


class ProvenanceAwareActionCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="forge-a1-")
        self.root = Path(self.temp.name)
        for name in ("trusted", "external", "binary"):
            (self.root / name).mkdir()

        (self.root / "trusted" / "recipient.txt").write_text("ops@example.test\n", encoding="utf-8")
        (self.root / "trusted" / "subject.txt").write_text("Verified subject\n", encoding="utf-8")
        (self.root / "external" / "recipient.txt").write_text("attacker@example.test\n", encoding="utf-8")
        (self.root / "external" / "body.txt").write_text("Quoted untrusted material\n", encoding="utf-8")
        # Same bytes as a frozen CONTROL value, but from an untrusted source.
        (self.root / "external" / "looks-control.txt").write_text("ops@example.test\n", encoding="utf-8")
        (self.root / "binary" / "invalid.bin").write_bytes(b"\xff\xfe\xfd")

        self.action_authority = {
            "tool": "send_notice",
            "effect_ceiling": "EXTERNAL_SIDE_EFFECT",
            "execution_authority": "none",
        }
        self.context = create_context_envelope(
            self.action_authority,
            allowed_paths=["trusted/**", "external/**", "binary/**"],
            max_grants=16,
            max_resource_bytes=512,
            max_total_bytes=4096,
        )

        self.grants = []
        for path in (
            "trusted/recipient.txt",
            "external/recipient.txt",
            "external/body.txt",
            "trusted/subject.txt",
            "external/looks-control.txt",
            "binary/invalid.bin",
        ):
            self.grants.append(
                issue_context_grant(self.root, self.context, self.grants, path, reason=f"A1 fixture {path}")
            )

        self.source_policy = create_source_policy(
            self.context,
            [
                {"pattern": "trusted/**", "trust": "VERIFIED"},
                {"pattern": "external/**", "trust": "UNTRUSTED"},
                {"pattern": "binary/**", "trust": "UNTRUSTED"},
            ],
        )
        self.template = create_action_template(
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
                    "control_values": ["Status: ", "Status"],
                },
                "body": {
                    "min_trust": "UNTRUSTED",
                    "allow_derived": True,
                    "control_values": ["Prefix: ", "Suffix"],
                },
            },
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def control(value: str) -> dict[str, object]:
        return {"kind": "CONTROL", "value": value}

    @staticmethod
    def grant(sequence: int) -> dict[str, object]:
        return {"kind": "GRANT", "sequence": sequence, "parser": "UTF8_STRIPPED"}

    @staticmethod
    def concat(*parts: dict[str, object]) -> dict[str, object]:
        return {"kind": "CONCAT", "parts": list(parts)}

    def proposal(self, *, recipient=None, subject=None, body=None):
        return create_action_proposal(
            self.template,
            {
                "recipient": recipient if recipient is not None else self.control("ops@example.test"),
                "subject": subject if subject is not None else self.control("Status"),
                "body": body if body is not None else self.grant(3),
            },
        )

    def evaluate(self, proposal, *, policy=None, template=None, grants=None):
        return evaluate_action_proposal(
            self.root,
            self.context,
            self.grants if grants is None else grants,
            self.source_policy if policy is None else policy,
            self.template if template is None else template,
            proposal,
        )

    def test_a1_00_control_recipient_and_untrusted_body_authorized(self) -> None:
        report = self.evaluate(self.proposal())
        self.assertEqual(report["state"], "ACTION_AUTHORIZED")
        self.assertEqual(report["parameters"]["recipient"]["derived_trust"], "CONTROL")
        self.assertEqual(report["parameters"]["body"]["derived_trust"], "UNTRUSTED")
        self.assertEqual(report["execution_authority"], "none")

    def test_a1_01_untrusted_grant_cannot_select_recipient(self) -> None:
        report = self.evaluate(self.proposal(recipient=self.grant(2)))
        self.assertEqual(report["state"], "ACTION_DENIED_PROVENANCE")
        self.assertEqual(report["denied_parameters"], ["recipient"])
        self.assertEqual(report["parameters"]["recipient"]["derived_trust"], "UNTRUSTED")

    def test_a1_02_worker_cannot_self_label_arbitrary_control(self) -> None:
        proposal = self.proposal(recipient=self.control("attacker@example.test"))
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(proposal)

    def test_a1_03_verified_grant_can_select_verified_recipient(self) -> None:
        report = self.evaluate(self.proposal(recipient=self.grant(1)))
        self.assertEqual(report["state"], "ACTION_AUTHORIZED")
        self.assertEqual(report["parameters"]["recipient"]["derived_trust"], "VERIFIED")

    def test_a1_04_and_23_concat_propagates_least_trusted_source(self) -> None:
        recipient = self.concat(self.grant(1), self.grant(2))
        report = self.evaluate(self.proposal(recipient=recipient))
        self.assertEqual(report["state"], "ACTION_DENIED_PROVENANCE")
        self.assertEqual(report["parameters"]["recipient"]["derived_trust"], "UNTRUSTED")
        self.assertEqual(len(report["parameters"]["recipient"]["lineage"]), 2)

    def test_a1_05_untrusted_concat_allowed_for_untrusted_body_policy(self) -> None:
        body = self.concat(self.control("Prefix: "), self.grant(3))
        report = self.evaluate(self.proposal(body=body))
        self.assertEqual(report["state"], "ACTION_AUTHORIZED")
        self.assertEqual(report["parameters"]["body"]["derived_trust"], "UNTRUSTED")

    def test_a1_06_nonexistent_grant_reference_rejected(self) -> None:
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(self.proposal(body=self.grant(99)))

    def test_a1_07_resource_drift_remains_fatal(self) -> None:
        (self.root / "external" / "body.txt").write_text("changed after grant\n", encoding="utf-8")
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(self.proposal())

    def test_a1_08_ambiguous_source_classification_fails_closed(self) -> None:
        ambiguous = create_source_policy(
            self.context,
            [
                {"pattern": "trusted/**", "trust": "VERIFIED"},
                {"pattern": "trusted/recipient.txt", "trust": "UNTRUSTED"},
                {"pattern": "external/**", "trust": "UNTRUSTED"},
                {"pattern": "binary/**", "trust": "UNTRUSTED"},
            ],
        )
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(self.proposal(recipient=self.grant(1)), policy=ambiguous)

    def test_a1_09_tampered_source_policy_rejected(self) -> None:
        policy = copy.deepcopy(self.source_policy)
        policy["rules"][1]["trust"] = "VERIFIED"
        with self.assertRaises(ForgeProvenancePolicyError):
            verify_source_policy(self.context, policy)

    def test_a1_10_tampered_action_template_rejected(self) -> None:
        template = copy.deepcopy(self.template)
        template["parameters"]["recipient"]["min_trust"] = "UNTRUSTED"
        with self.assertRaises(ForgeProvenancePolicyError):
            verify_action_template(template)

    def test_a1_11_action_identity_mismatch_rejected(self) -> None:
        proposal = self.proposal()
        proposal["action_id"] = "delete_everything"
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(proposal)

    def test_a1_12_extra_and_missing_parameters_rejected(self) -> None:
        for mutate in ("extra", "missing"):
            proposal = self.proposal()
            if mutate == "extra":
                proposal["parameters"]["cc"] = self.grant(2)
            else:
                del proposal["parameters"]["subject"]
            # Recompute is intentionally unavailable to the worker through this mutation path;
            # either exact parameter schema or digest integrity must reject it.
            with self.subTest(mutate=mutate):
                with self.assertRaises(ForgeProvenancePolicyError):
                    self.evaluate(proposal)

    def test_a1_13_raw_unprovenanced_expression_rejected(self) -> None:
        proposal = self.proposal(recipient={"kind": "RAW", "value": "attacker@example.test"})
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(proposal)

    def test_a1_14_and_20_worker_supplied_trust_or_rule_choice_rejected(self) -> None:
        for expression in (
            {"kind": "GRANT", "sequence": 2, "parser": "UTF8_STRIPPED", "trust": "VERIFIED"},
            {"kind": "GRANT", "sequence": 2, "parser": "UTF8_STRIPPED", "rule": "trusted/**"},
        ):
            with self.subTest(expression=expression):
                with self.assertRaises(ForgeProvenancePolicyError):
                    self.evaluate(self.proposal(recipient=expression))

    def test_a1_15_proposal_cannot_alter_effect_class(self) -> None:
        proposal = self.proposal()
        proposal["effect_class"] = "READ_ONLY"
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(proposal)

    def test_a1_16_expression_depth_budget_enforced(self) -> None:
        expression = self.grant(3)
        for _ in range(9):
            expression = self.concat(expression)
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(self.proposal(body=expression))

    def test_a1_17_node_and_output_budgets_enforced(self) -> None:
        too_many = self.concat(*[self.grant(3) for _ in range(65)])
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(self.proposal(body=too_many))

        huge = "x" * 9000
        template = create_action_template(
            "send_notice",
            effect_class="EXTERNAL_SIDE_EFFECT",
            parameters={
                "recipient": {"min_trust": "CONTROL", "allow_derived": False, "control_values": ["ops@example.test"]},
                "subject": {"min_trust": "CONTROL", "allow_derived": False, "control_values": ["Status"]},
                "body": {"min_trust": "CONTROL", "allow_derived": True, "control_values": [huge]},
            },
        )
        proposal = create_action_proposal(
            template,
            {
                "recipient": self.control("ops@example.test"),
                "subject": self.control("Status"),
                "body": self.concat(self.control(huge), self.control(huge)),
            },
        )
        with self.assertRaises(ForgeProvenancePolicyError):
            evaluate_action_proposal(self.root, self.context, self.grants, self.source_policy, template, proposal)

    def test_a1_18_invalid_utf8_grant_rejected_by_text_parser(self) -> None:
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(self.proposal(body=self.grant(6)))

    def test_a1_19_exact_control_bytes_from_untrusted_source_remain_untrusted(self) -> None:
        report = self.evaluate(self.proposal(recipient=self.grant(5)))
        self.assertEqual(report["state"], "ACTION_DENIED_PROVENANCE")
        self.assertEqual(report["parameters"]["recipient"]["derived_trust"], "UNTRUSTED")

    def test_a1_21_control_value_must_be_exact_frozen_constant(self) -> None:
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(self.proposal(recipient=self.control("OPS@EXAMPLE.TEST")))

    def test_a1_22_proposal_cannot_change_parameter_minimum_trust(self) -> None:
        expression = {"kind": "GRANT", "sequence": 2, "parser": "UTF8_STRIPPED", "min_trust": "UNTRUSTED"}
        with self.assertRaises(ForgeProvenancePolicyError):
            self.evaluate(self.proposal(recipient=expression))

    def test_a1_24_evaluation_report_preserves_lineage_and_trust(self) -> None:
        report = self.evaluate(self.proposal(recipient=self.grant(1), body=self.concat(self.control("Prefix: "), self.grant(3))))
        self.assertEqual(report["state"], "ACTION_AUTHORIZED")
        recipient = report["parameters"]["recipient"]
        body = report["parameters"]["body"]
        self.assertEqual(recipient["derived_trust"], "VERIFIED")
        self.assertEqual(recipient["lineage"][0]["resource_path"], "trusted/recipient.txt")
        self.assertEqual(body["derived_trust"], "UNTRUSTED")
        self.assertEqual([item["kind"] for item in body["lineage"]], ["CONTROL", "GRANT"])
        self.assertEqual(report["execution_authority"], "none")


if __name__ == "__main__":
    unittest.main()
