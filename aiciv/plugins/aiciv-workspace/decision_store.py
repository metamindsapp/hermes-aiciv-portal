"""Durable structured human-decision store for the AiCIV workspace.

This store records human judgment only. A resolved decision is not evidence
that any downstream side effect was executed successfully.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 1
FINAL_STATUSES = {"resolved", "withdrawn"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def db_path() -> Path:
    configured = os.environ.get("AICIV_DECISIONS_DB", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".hermes" / "aiciv" / "decisions.sqlite3"


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def request_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS aiciv_meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS decisions (
          id TEXT PRIMARY KEY,
          idempotency_key TEXT UNIQUE,
          request_hash TEXT NOT NULL,
          title TEXT NOT NULL,
          question TEXT NOT NULL,
          status TEXT NOT NULL,
          options_json TEXT NOT NULL,
          recommendation TEXT,
          rationale TEXT NOT NULL,
          evidence_refs_json TEXT NOT NULL,
          blocking_refs_json TEXT NOT NULL,
          urgency TEXT NOT NULL,
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          resolved_at TEXT,
          response_json TEXT
        );

        CREATE INDEX IF NOT EXISTS decisions_status_created_idx
          ON decisions(status, created_at DESC);

        CREATE TABLE IF NOT EXISTS decision_events (
          id TEXT PRIMARY KEY,
          decision_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(decision_id) REFERENCES decisions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS decision_events_decision_idx
          ON decision_events(decision_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS decision_response_requests (
          request_id TEXT PRIMARY KEY,
          decision_id TEXT NOT NULL,
          option_id TEXT NOT NULL,
          note TEXT NOT NULL,
          receipt_id TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL,
          FOREIGN KEY(decision_id) REFERENCES decisions(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO aiciv_meta(key, value) VALUES('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def row_to_decision(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "decisionId": row["id"],
        "idempotencyKey": row["idempotency_key"],
        "title": row["title"],
        "question": row["question"],
        "status": row["status"],
        "options": _loads(row["options_json"], []),
        "recommendation": row["recommendation"],
        "rationale": row["rationale"],
        "evidenceRefs": _loads(row["evidence_refs_json"], []),
        "blockingRefs": _loads(row["blocking_refs_json"], []),
        "urgency": row["urgency"],
        "createdBy": row["created_by"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "resolvedAt": row["resolved_at"],
        "response": _loads(row["response_json"], None),
    }


def append_event(
    conn: sqlite3.Connection,
    decision_id: str,
    kind: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "eventId": f"devevt_{secrets.token_hex(12)}",
        "decisionId": decision_id,
        "kind": kind,
        "payload": payload or {},
        "createdAt": now_iso(),
    }
    conn.execute(
        "INSERT INTO decision_events(id, decision_id, kind, payload_json, created_at) VALUES(?,?,?,?,?)",
        (event["eventId"], decision_id, kind, _json(event["payload"]), event["createdAt"]),
    )
    return event


def create_decision(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    fingerprint = request_hash(payload)
    idempotency_key = payload.get("idempotencyKey")
    with connect() as conn:
        if idempotency_key:
            existing = conn.execute(
                "SELECT * FROM decisions WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing:
                if existing["request_hash"] != fingerprint:
                    raise ValueError("idempotency_conflict")
                return row_to_decision(existing), False

        decision_id = f"dec_{secrets.token_hex(12)}"
        now = now_iso()
        conn.execute(
            """
            INSERT INTO decisions(
              id, idempotency_key, request_hash, title, question, status,
              options_json, recommendation, rationale, evidence_refs_json,
              blocking_refs_json, urgency, created_by, created_at, updated_at
            ) VALUES(?,?,?,?,?,'pending',?,?,?,?,?,?,?,?,?)
            """,
            (
                decision_id,
                idempotency_key,
                fingerprint,
                payload["title"],
                payload["question"],
                _json(payload["options"]),
                payload.get("recommendation"),
                payload.get("rationale", ""),
                _json(payload.get("evidenceRefs", [])),
                _json(payload.get("blockingRefs", [])),
                payload.get("urgency", "normal"),
                payload.get("createdBy", "aiciv"),
                now,
                now,
            ),
        )
        append_event(
            conn,
            decision_id,
            "decision.requested",
            {"urgency": payload.get("urgency", "normal")},
        )
        row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        return row_to_decision(row), True


def get_decision(decision_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        return row_to_decision(row) if row else None


def list_decisions(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    with connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [row_to_decision(row) for row in rows]


def respond_decision(
    decision_id: str,
    *,
    option_id: str,
    note: str,
    request_id: str,
    actor: str = "human",
) -> tuple[dict[str, Any], bool]:
    with connect() as conn:
        replay = conn.execute(
            "SELECT * FROM decision_response_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if replay:
            if replay["decision_id"] != decision_id or replay["option_id"] != option_id or replay["note"] != note:
                raise ValueError("response_idempotency_conflict")
            row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
            if not row:
                raise KeyError("decision_not_found")
            return row_to_decision(row), False

        row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        if not row:
            raise KeyError("decision_not_found")
        if row["status"] != "pending":
            raise ValueError("decision_not_pending")

        options = _loads(row["options_json"], [])
        allowed = {item.get("id") for item in options if isinstance(item, dict)}
        if option_id not in allowed:
            raise ValueError("invalid_option")

        now = now_iso()
        receipt_id = f"drcpt_{secrets.token_hex(12)}"
        response = {
            "optionId": option_id,
            "note": note,
            "actor": actor,
            "requestId": request_id,
            "receiptId": receipt_id,
            "recordedAt": now,
            "semantics": "human_decision_recorded_not_downstream_execution",
        }
        conn.execute(
            """
            INSERT INTO decision_response_requests(
              request_id, decision_id, option_id, note, receipt_id, created_at
            ) VALUES(?,?,?,?,?,?)
            """,
            (request_id, decision_id, option_id, note, receipt_id, now),
        )
        conn.execute(
            """
            UPDATE decisions
            SET status='resolved', updated_at=?, resolved_at=?, response_json=?
            WHERE id=?
            """,
            (now, now, _json(response), decision_id),
        )
        append_event(
            conn,
            decision_id,
            "decision.resolved",
            {"optionId": option_id, "receiptId": receipt_id, "actor": actor},
        )
        updated = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        return row_to_decision(updated), True


def withdraw_decision(decision_id: str, *, actor: str = "aiciv") -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        if not row:
            raise KeyError("decision_not_found")
        if row["status"] == "resolved":
            raise ValueError("decision_already_resolved")
        if row["status"] == "withdrawn":
            return row_to_decision(row)
        now = now_iso()
        conn.execute(
            "UPDATE decisions SET status='withdrawn', updated_at=? WHERE id=?",
            (now, decision_id),
        )
        append_event(conn, decision_id, "decision.withdrawn", {"actor": actor})
        updated = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        return row_to_decision(updated)


def list_events(after: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    with connect() as conn:
        if after:
            pivot = conn.execute("SELECT created_at FROM decision_events WHERE id = ?", (after,)).fetchone()
            if pivot:
                rows = conn.execute(
                    "SELECT * FROM decision_events WHERE created_at > ? ORDER BY created_at ASC LIMIT ?",
                    (pivot["created_at"], limit),
                ).fetchall()
            else:
                rows = []
        else:
            rows = conn.execute(
                "SELECT * FROM decision_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "eventId": row["id"],
                "decisionId": row["decision_id"],
                "kind": row["kind"],
                "payload": _loads(row["payload_json"], {}),
                "createdAt": row["created_at"],
            }
            for row in rows
        ]
