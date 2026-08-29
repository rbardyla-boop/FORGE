from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from forge_core.approval_binding import compile_action_manifest, issue_action_approval
from forge_core.effect_journal import (
    ForgeEffectJournalError,
    SimulatedCrash,
    get_effect_record,
    perform_prepared_effect,
    prepare_effect_intent,
)


def digest_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def fake_digest(seed: str) -> str:
    return f"sha256:{hashlib.sha256(seed.encode('utf-8')).hexdigest()}"


class NonIdempotentSink:
    supports_idempotency = False

    def __init__(self) -> None:
        self.calls = 0
        self.logical_effects = 0
        self.keys: list[str] = []

    def perform(self, manifest, *, idempotency_key: str):
        self.calls += 1
        self.logical_effects += 1
        self.keys.append(idempotency_key)
        return {"remote_id": f"effect-{self.logical_effects}", "manifest": manifest["manifest_digest"]}


class IdempotentSink:
    supports_idempotency = True

    def __init__(self) -> None:
        self.calls = 0
        self.effects: dict[str, dict[str, str]] = {}
        self.keys: list[str] = []

    @property
    def logical_effects(self) -> int:
        return len(self.effects)

    def perform(self, manifest, *, idempotency_key: str):
        self.calls += 1
        self.keys.append(idempotency_key)
        if idempotency_key not in self.effects:
            self.effects[idempotency_key] = {
                "remote_id": f"effect-{len(self.effects) + 1}",
                "manifest": manifest["manifest_digest"],
            }
        return self.effects[idempotency_key]


class CrashAfterEffectBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="forge-a3-")
        self.journal = Path(self.temp.name) / "effect-journal.sqlite3"
        self.arguments = {"recipient": "ops@example.test", "subject": "Status", "body": "Hello"}
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
            "parameters": {name: {"value_sha256": digest_text(value)} for name, value in self.arguments.items()},
            "execution_authority": "none",
        }
        self.manifest = compile_action_manifest(self.evaluation, self.arguments)
        self.key = b"a3-trusted-approval-key-material-000000000000000000"
        self.token = issue_action_approval(
            self.manifest,
            self.key,
            signer="human:test",
            nonce="a3-approval-001",
            issued_at=1000,
            expires_at=1100,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def prepare(self, *, semantics="NON_RETRYABLE", now=1050, manifest=None, token=None):
        return prepare_effect_intent(
            self.journal,
            self.manifest if manifest is None else manifest,
            self.token if token is None else token,
            self.key,
            now=now,
            allowed_signers=["human:test"],
            replay_semantics=semantics,
        )

    def test_a3_00_approval_consumption_and_intent_are_durable_together(self) -> None:
        record = self.prepare()
        self.assertEqual(record["state"], "PREPARED")
        with sqlite3.connect(self.journal) as connection:
            approvals = connection.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
            effects = connection.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
        self.assertEqual((approvals, effects), (1, 1))

    def test_a3_01_and_15_same_nonce_cannot_bind_different_action(self) -> None:
        self.prepare()
        evaluation = dict(self.evaluation)
        evaluation["action_id"] = "other_action"
        other_manifest = compile_action_manifest(evaluation, self.arguments)
        other_token = issue_action_approval(
            other_manifest,
            self.key,
            signer="human:test",
            nonce="a3-approval-001",
            issued_at=1000,
            expires_at=1100,
        )
        with self.assertRaises(ForgeEffectJournalError):
            self.prepare(manifest=other_manifest, token=other_token)
        self.assertIsNone(get_effect_record(self.journal, other_manifest["manifest_digest"]))

    def test_a3_02_exact_repeated_preparation_is_idempotent_locally(self) -> None:
        first = self.prepare()
        second = self.prepare()
        self.assertEqual(first, second)
        with sqlite3.connect(self.journal) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM effects").fetchone()[0], 1)

    def test_a3_03_intent_survives_journal_reopen(self) -> None:
        prepared = self.prepare()
        reopened = get_effect_record(self.journal, self.manifest["manifest_digest"])
        self.assertEqual(reopened, prepared)

    def test_a3_04_crash_after_remote_effect_leaves_in_flight(self) -> None:
        self.prepare()
        sink = NonIdempotentSink()
        with self.assertRaises(SimulatedCrash):
            perform_prepared_effect(self.journal, self.manifest, sink, crash_after_remote=True)
        record = get_effect_record(self.journal, self.manifest["manifest_digest"])
        self.assertEqual(record["state"], "IN_FLIGHT")
        self.assertEqual(record["attempts"], 1)
        self.assertEqual(sink.logical_effects, 1)

    def test_a3_05_non_retryable_recovery_refuses_automatic_retry(self) -> None:
        self.prepare()
        sink = NonIdempotentSink()
        with self.assertRaises(SimulatedCrash):
            perform_prepared_effect(self.journal, self.manifest, sink, crash_after_remote=True)
        recovery = perform_prepared_effect(self.journal, self.manifest, sink)
        self.assertEqual(recovery["state"], "EFFECT_UNCERTAIN")
        self.assertFalse(recovery["sink_called"])
        self.assertEqual(sink.logical_effects, 1)

    def test_a3_06_blind_retry_demonstrably_duplicates_non_idempotent_effect(self) -> None:
        self.prepare()
        sink = NonIdempotentSink()
        with self.assertRaises(SimulatedCrash):
            perform_prepared_effect(self.journal, self.manifest, sink, crash_after_remote=True)
        # Deliberately bypass the safe executor to demonstrate the ambiguity cost.
        sink.perform(self.manifest, idempotency_key="blind-retry-does-not-help")
        self.assertEqual(sink.logical_effects, 2)
        record = get_effect_record(self.journal, self.manifest["manifest_digest"])
        self.assertEqual(record["state"], "IN_FLIGHT")

    def test_a3_07_08_09_idempotency_keyed_retry_is_stable_and_commits_once(self) -> None:
        prepared = self.prepare(semantics="IDEMPOTENCY_KEYED")
        sink = IdempotentSink()
        with self.assertRaises(SimulatedCrash):
            perform_prepared_effect(self.journal, self.manifest, sink, crash_after_remote=True)
        self.assertEqual(sink.logical_effects, 1)
        result = perform_prepared_effect(self.journal, self.manifest, sink)
        self.assertEqual(result["state"], "COMMITTED")
        self.assertEqual(sink.calls, 2)
        self.assertEqual(sink.logical_effects, 1)
        self.assertEqual(sink.keys, [prepared["idempotency_key"], prepared["idempotency_key"]])

    def test_a3_10_committed_intent_never_calls_sink_again(self) -> None:
        self.prepare(semantics="IDEMPOTENCY_KEYED")
        sink = IdempotentSink()
        first = perform_prepared_effect(self.journal, self.manifest, sink)
        self.assertEqual(first["state"], "COMMITTED")
        calls = sink.calls
        second = perform_prepared_effect(self.journal, self.manifest, sink)
        self.assertEqual(second["state"], "COMMITTED")
        self.assertFalse(second["sink_called"])
        self.assertEqual(sink.calls, calls)

    def test_a3_11_receipt_is_stored_as_hash_not_raw_receipt(self) -> None:
        self.prepare(semantics="IDEMPOTENCY_KEYED")
        sink = IdempotentSink()
        result = perform_prepared_effect(self.journal, self.manifest, sink)
        receipt_hash = result["record"]["receipt_sha256"]
        self.assertTrue(receipt_hash.startswith("sha256:"))
        with sqlite3.connect(self.journal) as connection:
            columns = [row[1] for row in connection.execute("PRAGMA table_info(effects)").fetchall()]
        self.assertIn("receipt_sha256", columns)
        self.assertNotIn("receipt", columns)

    def test_a3_12_expiry_after_durable_preparation_does_not_erase_intent(self) -> None:
        first = self.prepare(now=1050)
        second = self.prepare(now=5000)
        self.assertEqual(second, first)

    def test_a3_13_expired_approval_cannot_create_new_intent(self) -> None:
        with self.assertRaises(ForgeEffectJournalError):
            self.prepare(now=5000)
        self.assertIsNone(get_effect_record(self.journal, self.manifest["manifest_digest"]))

    def test_a3_14_replay_semantics_cannot_change_after_preparation(self) -> None:
        self.prepare(semantics="NON_RETRYABLE")
        with self.assertRaises(ForgeEffectJournalError):
            self.prepare(semantics="IDEMPOTENCY_KEYED")

    def test_a3_16_sink_idempotency_does_not_override_non_retryable_policy(self) -> None:
        self.prepare(semantics="NON_RETRYABLE")
        sink = IdempotentSink()
        with self.assertRaises(SimulatedCrash):
            perform_prepared_effect(self.journal, self.manifest, sink, crash_after_remote=True)
        calls = sink.calls
        result = perform_prepared_effect(self.journal, self.manifest, sink)
        self.assertEqual(result["state"], "EFFECT_UNCERTAIN")
        self.assertEqual(sink.calls, calls)

    def test_a3_17_local_idempotency_label_requires_sink_contract_support(self) -> None:
        self.prepare(semantics="IDEMPOTENCY_KEYED")
        sink = NonIdempotentSink()
        with self.assertRaises(ForgeEffectJournalError):
            perform_prepared_effect(self.journal, self.manifest, sink)
        self.assertEqual(sink.calls, 0)

    def test_a3_18_unknown_journal_state_fails_closed(self) -> None:
        self.prepare()
        with sqlite3.connect(self.journal) as connection:
            connection.execute(
                "UPDATE effects SET state = 'MYSTERY' WHERE manifest_digest = ?",
                (self.manifest["manifest_digest"],),
            )
            connection.commit()
        with self.assertRaises(ForgeEffectJournalError):
            perform_prepared_effect(self.journal, self.manifest, NonIdempotentSink())


if __name__ == "__main__":
    unittest.main()
