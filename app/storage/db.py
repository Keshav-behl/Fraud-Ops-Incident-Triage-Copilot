import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS triage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_key TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    triaged_at TEXT,
    risk_tier TEXT,
    confidence REAL,
    suggested_team TEXT,
    suggested_sop TEXT,
    rationale TEXT,
    escalated INTEGER NOT NULL DEFAULT 0,
    decision TEXT NOT NULL DEFAULT 'pending',
    final_risk_tier TEXT,
    final_team TEXT,
    resolved_at TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(SCHEMA)


def insert_triage(
    ticket_key: str,
    risk_tier: str,
    confidence: float,
    suggested_team: str,
    suggested_sop: str,
    rationale: str,
    escalated: bool,
    decision: str = "pending",
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO triage_history
                (ticket_key, ingested_at, triaged_at, risk_tier, confidence,
                 suggested_team, suggested_sop, rationale, escalated, decision)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_key,
                _now(),
                _now(),
                risk_tier,
                confidence,
                suggested_team,
                suggested_sop,
                rationale,
                int(escalated),
                decision,
            ),
        )
        return cur.lastrowid


def get_pending_by_ticket_key(ticket_key: str) -> sqlite3.Row | None:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM triage_history WHERE ticket_key = ? AND decision = 'pending' "
            "ORDER BY id DESC LIMIT 1",
            (ticket_key,),
        )
        return cur.fetchone()


def resolve_decision(ticket_key: str, decision: str, final_risk_tier: str, final_team: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE triage_history
            SET decision = ?, final_risk_tier = ?, final_team = ?, resolved_at = ?
            WHERE ticket_key = ? AND decision = 'pending'
            """,
            (decision, final_risk_tier, final_team, _now(), ticket_key),
        )


def get_history(ticket_key: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM triage_history WHERE ticket_key = ? ORDER BY id", (ticket_key,)
        )
        return cur.fetchall()
