"""Unit tests for EventLedger."""

import sqlite3
import sys
import time
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from aia_canvas.src.memory.event_ledger import EventLedger
except ModuleNotFoundError:
    from memory.event_ledger import EventLedger



@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "events.db"


def test_schema_initialization(db_path: Path):
    with EventLedger(db_path) as ledger:
        assert db_path.exists()
        cursor = ledger.conn.cursor()

        # Verify table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='interaction_events';"
        )
        assert cursor.fetchone() is not None

        # Verify indices exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IN ('idx_events_timestamp', 'idx_events_type');"
        )
        indices = {row[0] for row in cursor.fetchall()}
        assert "idx_events_timestamp" in indices
        assert "idx_events_type" in indices


def test_record_event(db_path: Path):
    with EventLedger(db_path) as ledger:
        payload = {"action": "node_dwell", "dwell_time": 1.45, "coordinates": [100, 250]}
        row_id_1 = ledger.record_event(
            event_type="hover",
            target_id=101,
            archetype="document",
            payload=payload,
        )
        assert row_id_1 == 1

        row_id_2 = ledger.record_event(
            event_type="click",
            target_id=202,
            archetype="cluster",
            payload=None,
        )
        assert row_id_2 == 2

        # Verify row contents
        cursor = ledger.conn.cursor()
        cursor.execute("SELECT id, event_type, target_id, archetype, payload FROM interaction_events WHERE id = 1;")
        row = cursor.fetchone()
        assert row["id"] == 1
        assert row["event_type"] == "hover"
        assert row["target_id"] == 101
        assert row["archetype"] == "document"
        assert '"action": "node_dwell"' in row["payload"]


def test_get_recent_events(db_path: Path):
    with EventLedger(db_path) as ledger:
        ledger.record_event("selection", target_id=1, archetype="terminal", payload={"selected": True})
        time.sleep(0.01)
        ledger.record_event("click", target_id=2, archetype="document", payload={"count": 1})
        time.sleep(0.01)
        ledger.record_event("selection", target_id=3, archetype="code", payload={"selected": False})

        # Fetch all without filter
        events = ledger.get_recent_events(limit=10)
        assert len(events) == 3
        # Should be ordered timestamp DESC
        assert events[0]["target_id"] == 3
        assert events[0]["payload"] == {"selected": False}
        assert events[1]["target_id"] == 2
        assert events[1]["payload"] == {"count": 1}
        assert events[2]["target_id"] == 1
        assert events[2]["payload"] == {"selected": True}

        # Fetch with event_type filter
        selection_events = ledger.get_recent_events(limit=10, event_type="selection")
        assert len(selection_events) == 2
        assert [e["target_id"] for e in selection_events] == [3, 1]

        # Fetch with limit
        limited_events = ledger.get_recent_events(limit=1)
        assert len(limited_events) == 1
        assert limited_events[0]["target_id"] == 3


def test_prune_events(db_path: Path):
    with EventLedger(db_path) as ledger:
        now = time.time()
        eight_days_ago = now - (8 * 86400)
        ten_days_ago = now - (10 * 86400)
        yesterday = now - (1 * 86400)

        # Directly insert events with historical timestamps
        cursor = ledger.conn.cursor()
        cursor.execute(
            "INSERT INTO interaction_events (timestamp, event_type, target_id, archetype, payload) VALUES (?, ?, ?, ?, ?)",
            (ten_days_ago, "old_event_1", 1, "doc", "{}"),
        )
        cursor.execute(
            "INSERT INTO interaction_events (timestamp, event_type, target_id, archetype, payload) VALUES (?, ?, ?, ?, ?)",
            (eight_days_ago, "old_event_2", 2, "doc", "{}"),
        )
        cursor.execute(
            "INSERT INTO interaction_events (timestamp, event_type, target_id, archetype, payload) VALUES (?, ?, ?, ?, ?)",
            (yesterday, "fresh_event_1", 3, "doc", "{}"),
        )
        ledger.conn.commit()

        # Also record one right now
        ledger.record_event("fresh_event_2", target_id=4, archetype="doc", payload={"fresh": True})

        # Total 4 events before prune
        assert len(ledger.get_recent_events(limit=10)) == 4

        # Prune events older than 7 days (default ttl_seconds=604800.0)
        deleted_count = ledger.prune_events()
        assert deleted_count == 2

        remaining_events = ledger.get_recent_events(limit=10)
        assert len(remaining_events) == 2
        remaining_ids = {e["target_id"] for e in remaining_events}
        assert remaining_ids == {3, 4}


def test_context_manager_cleanup(db_path: Path):
    ledger = EventLedger(db_path)
    with ledger:
        assert ledger.conn is not None
        ledger.record_event("test_event", target_id=99)

    assert ledger.conn is None
    with pytest.raises(RuntimeError, match="connection is closed"):
        ledger.record_event("after_close", target_id=100)
