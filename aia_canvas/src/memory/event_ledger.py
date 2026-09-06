"""SQLite Event Ledger for living memory interaction tracking."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


class EventLedger:
    """Manages persistent SQLite interaction event ledger."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self.db_path = Path.home() / ".local" / "share" / "aether" / "events.db"
        else:
            self.db_path = Path(db_path)

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn: Optional[sqlite3.Connection] = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        self._init_schema()

    def _init_schema(self) -> None:
        if self.conn is None:
            return

        cursor = self.conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS interaction_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                target_id INTEGER DEFAULT 0,
                archetype TEXT DEFAULT '',
                payload TEXT DEFAULT '{}'
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON interaction_events(timestamp);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_type ON interaction_events(event_type);"
        )
        self.conn.commit()

    def record_event(
        self,
        event_type: str,
        target_id: int = 0,
        archetype: str = "",
        payload: dict[str, Any] | str | None = None,
    ) -> int:
        """Record an interaction event and return the inserted row id."""
        if self.conn is None:
            raise RuntimeError("EventLedger connection is closed.")

        ts = time.time()
        if payload is None:
            payload_str = "{}"
        elif isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO interaction_events (timestamp, event_type, target_id, archetype, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, event_type, target_id, archetype, payload_str),
        )
        self.conn.commit()
        return cursor.lastrowid or 0

    def prune_events(self, ttl_seconds: float = 604800.0) -> int:
        """Prune events older than ttl_seconds (default: 7 days) and return deleted count."""
        if self.conn is None:
            raise RuntimeError("EventLedger connection is closed.")

        cutoff = time.time() - ttl_seconds
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM interaction_events WHERE timestamp < ?",
            (cutoff,),
        )
        deleted_count = cursor.rowcount
        self.conn.commit()
        return deleted_count

    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve recent events ordered by timestamp DESC."""
        if self.conn is None:
            raise RuntimeError("EventLedger connection is closed.")

        cursor = self.conn.cursor()
        if event_type is not None:
            cursor.execute(
                """
                SELECT id, timestamp, event_type, target_id, archetype, payload
                FROM interaction_events
                WHERE event_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (event_type, limit),
            )
        else:
            cursor.execute(
                """
                SELECT id, timestamp, event_type, target_id, archetype, payload
                FROM interaction_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

        rows = cursor.fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            raw_payload = row["payload"]
            try:
                deserialized_payload = json.loads(raw_payload) if raw_payload else {}
            except (json.JSONDecodeError, TypeError):
                deserialized_payload = raw_payload

            events.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "event_type": row["event_type"],
                    "target_id": row["target_id"],
                    "archetype": row["archetype"],
                    "payload": deserialized_payload,
                }
            )
        return events

    def close(self) -> None:
        """Close SQLite database connection."""
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> EventLedger:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self.close()
