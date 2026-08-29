from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Protocol, Sequence

from .approval_binding import (
    ForgeApprovalError,
    validate_action_approval,
    verify_action_manifest,
)


REPLAY_SEMANTICS = {"IDEMPOTENCY_KEYED", "NON_RETRYABLE"}
EFFECT_STATES = {"PREPARED", "IN_FLIGHT", "COMMITTED"}


class ForgeEffectJournalError(RuntimeError):
    """A3 durable effect intent is malformed, inconsistent, or unsafe to continue."""


class SimulatedCrash(RuntimeError):
    """Research-only crash injected after the simulated remote effect."""


class EffectSink(Protocol):
    supports_idempotency: bool

    def perform(self, manifest: dict[str, Any], *, idempotency_key: str) -> Any: ...


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _token_digest(token: dict[str, Any]) -> str:
    return _sha256(_canonical(token))


def _idempotency_key(manifest_digest: str) -> str:
    return f"forge:{manifest_digest}"


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS approvals (
            nonce TEXT PRIMARY KEY,
            manifest_digest TEXT NOT NULL,
            token_digest TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS effects (
            manifest_digest TEXT PRIMARY KEY,
            approval_nonce TEXT NOT NULL UNIQUE,
            token_digest TEXT NOT NULL,
            replay_semantics TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            receipt_sha256 TEXT,
            FOREIGN KEY (approval_nonce) REFERENCES approvals(nonce)
        )
        """
    )
    connection.commit()
    return connection


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "manifest_digest": row["manifest_digest"],
        "approval_nonce": row["approval_nonce"],
        "token_digest": row["token_digest"],
        "replay_semantics": row["replay_semantics"],
        "idempotency_key": row["idempotency_key"],
        "state": row["state"],
        "attempts": row["attempts"],
        "receipt_sha256": row["receipt_sha256"],
    }


def get_effect_record(journal_path: Path, manifest_digest: str) -> dict[str, Any] | None:
    with _connect(journal_path) as connection:
        row = connection.execute(
            "SELECT * FROM effects WHERE manifest_digest = ?",
            (manifest_digest,),
        ).fetchone()
        return None if row is None else _row_to_record(row)


def prepare_effect_intent(
    journal_path: Path,
    manifest: dict[str, Any],
    approval_token: dict[str, Any],
    signing_key: bytes,
    *,
    now: int,
    allowed_signers: Sequence[str],
    replay_semantics: str,
) -> dict[str, Any]:
    verify_action_manifest(manifest)
    if replay_semantics not in REPLAY_SEMANTICS:
        raise ForgeEffectJournalError("unsupported replay semantics")
    if not isinstance(approval_token, dict):
        raise ForgeEffectJournalError("approval token must be an object")
    nonce = approval_token.get("nonce")
    if not isinstance(nonce, str) or not nonce:
        raise ForgeEffectJournalError("approval token nonce unavailable")
    token_digest = _token_digest(approval_token)
    manifest_digest = manifest["manifest_digest"]
    stable_key = _idempotency_key(manifest_digest)

    connection = _connect(journal_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        approval_row = connection.execute(
            "SELECT * FROM approvals WHERE nonce = ?",
            (nonce,),
        ).fetchone()
        effect_row = connection.execute(
            "SELECT * FROM effects WHERE manifest_digest = ?",
            (manifest_digest,),
        ).fetchone()

        if approval_row is not None:
            if approval_row["manifest_digest"] != manifest_digest or approval_row["token_digest"] != token_digest:
                raise ForgeEffectJournalError("approval nonce is already bound to a different durable intent")
            if effect_row is None:
                raise ForgeEffectJournalError("journal approval/effect atomicity invariant is broken")
            record = _row_to_record(effect_row)
            if record["approval_nonce"] != nonce or record["token_digest"] != token_digest:
                raise ForgeEffectJournalError("durable effect intent does not match approval record")
            if record["replay_semantics"] != replay_semantics:
                raise ForgeEffectJournalError("replay semantics cannot change after durable preparation")
            if record["idempotency_key"] != stable_key:
                raise ForgeEffectJournalError("durable idempotency key drift detected")
            connection.commit()
            return record

        if effect_row is not None:
            raise ForgeEffectJournalError("effect intent exists without matching approval consumption")

        try:
            validate_action_approval(
                manifest,
                approval_token,
                signing_key,
                now=now,
                allowed_signers=allowed_signers,
                spent_nonces=None,
                consume=False,
            )
        except ForgeApprovalError as exc:
            raise ForgeEffectJournalError(f"approval is not valid for new durable intent: {exc}") from exc

        connection.execute(
            "INSERT INTO approvals(nonce, manifest_digest, token_digest) VALUES (?, ?, ?)",
            (nonce, manifest_digest, token_digest),
        )
        connection.execute(
            """
            INSERT INTO effects(
                manifest_digest,
                approval_nonce,
                token_digest,
                replay_semantics,
                idempotency_key,
                state,
                attempts,
                receipt_sha256
            ) VALUES (?, ?, ?, ?, ?, 'PREPARED', 0, NULL)
            """,
            (manifest_digest, nonce, token_digest, replay_semantics, stable_key),
        )
        connection.commit()
        record = get_effect_record(journal_path, manifest_digest)
        if record is None:
            raise ForgeEffectJournalError("durable effect intent disappeared after commit")
        return record
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def perform_prepared_effect(
    journal_path: Path,
    manifest: dict[str, Any],
    sink: EffectSink,
    *,
    crash_after_remote: bool = False,
) -> dict[str, Any]:
    verify_action_manifest(manifest)
    manifest_digest = manifest["manifest_digest"]
    connection = _connect(journal_path)
    try:
        row = connection.execute(
            "SELECT * FROM effects WHERE manifest_digest = ?",
            (manifest_digest,),
        ).fetchone()
        if row is None:
            raise ForgeEffectJournalError("no durable approved effect intent exists")
        record = _row_to_record(row)
        if record["state"] not in EFFECT_STATES:
            raise ForgeEffectJournalError("unknown durable effect state")
        if record["idempotency_key"] != _idempotency_key(manifest_digest):
            raise ForgeEffectJournalError("idempotency key does not match exact action manifest")

        if record["state"] == "COMMITTED":
            return {"state": "COMMITTED", "sink_called": False, "record": record}

        if record["state"] == "IN_FLIGHT":
            if record["replay_semantics"] == "NON_RETRYABLE":
                return {"state": "EFFECT_UNCERTAIN", "sink_called": False, "record": record}
            if record["replay_semantics"] != "IDEMPOTENCY_KEYED":
                raise ForgeEffectJournalError("unsupported in-flight replay semantics")
            if not bool(getattr(sink, "supports_idempotency", False)):
                raise ForgeEffectJournalError("local idempotency label is insufficient without sink contract support")

        if record["state"] == "PREPARED" and record["replay_semantics"] == "IDEMPOTENCY_KEYED":
            if not bool(getattr(sink, "supports_idempotency", False)):
                raise ForgeEffectJournalError("sink does not satisfy frozen idempotency-keyed contract")

        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE effects SET state = 'IN_FLIGHT', attempts = attempts + 1 WHERE manifest_digest = ?",
            (manifest_digest,),
        )
        connection.commit()

        receipt = sink.perform(manifest, idempotency_key=record["idempotency_key"])
        if crash_after_remote:
            raise SimulatedCrash("simulated process loss after remote effect and before local commit")

        receipt_hash = _sha256(_canonical(receipt))
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT state, replay_semantics, idempotency_key FROM effects WHERE manifest_digest = ?",
            (manifest_digest,),
        ).fetchone()
        if current is None or current["state"] != "IN_FLIGHT":
            raise ForgeEffectJournalError("effect state changed unexpectedly before commit")
        if current["replay_semantics"] != record["replay_semantics"] or current["idempotency_key"] != record["idempotency_key"]:
            raise ForgeEffectJournalError("effect authority changed unexpectedly before commit")
        connection.execute(
            "UPDATE effects SET state = 'COMMITTED', receipt_sha256 = ? WHERE manifest_digest = ?",
            (receipt_hash, manifest_digest),
        )
        connection.commit()
        committed = get_effect_record(journal_path, manifest_digest)
        if committed is None:
            raise ForgeEffectJournalError("committed effect record disappeared")
        return {"state": "COMMITTED", "sink_called": True, "record": committed}
    finally:
        connection.close()
