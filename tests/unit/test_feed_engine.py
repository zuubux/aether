"""
Unit tests for FeedEngine and FeedItem data models.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from aia_canvas.src.plate_engine.feed_engine import (
    FeedConfig,
    FeedEngine,
    FeedGraduatedTier,
    FeedItem,
)
from aia_canvas.src.plate_engine.models import PlateArchetype, PlateNodePayload


def test_feed_item_defaults_and_contracts():
    item = FeedItem(
        id="item-1",
        title="Welcome to Aether",
        type="notification",
    )
    assert item.id == "item-1"
    assert item.item_id == "item-1"
    assert item.title == "Welcome to Aether"
    assert item.type == "notification"
    assert item.is_pinned is False
    assert item.is_active_glow is False
    assert item.has_dot is False
    assert item.recency_score == 1.0
    assert item.priority_score == 1.0
    assert item.effective_score == 1.0
    assert item.view_tier == FeedGraduatedTier.FULL
    assert item.is_ephemeral is False

    d = item.to_dict()
    assert d["id"] == "item-1"
    assert d["itemId"] == "item-1"
    assert d["isPinned"] is False
    assert d["is_pinned"] is False
    assert d["isActiveGlow"] is False
    assert d["hasDot"] is False
    assert d["recencyScore"] == 1.0
    assert d["viewTier"] == "full"


def test_feed_item_from_dict_explicit_lookups():
    raw_qml = {
        "itemId": "node-99",
        "displayTitle": "Kernel Pipeline",
        "feedType": "system",
        "createdAt": 1700000000.0,
        "isPinned": True,
        "isActiveGlow": True,
        "hasDot": True,
        "contentPayload": {"status": "ok", "latency": 4.2},
        "recencyScore": 0.85,
        "priorityScore": 2.5,
        "viewTier": "compact",
        "isEphemeral": True,
        "ttlSeconds": 300.0,
        "metadata": {"cluster": "alpha"},
    }
    item = FeedItem.from_dict(raw_qml)
    assert item.id == "node-99"
    assert item.title == "Kernel Pipeline"
    assert item.type == "system"
    assert item.timestamp == 1700000000.0
    assert item.is_pinned is True
    assert item.is_active_glow is True
    assert item.has_dot is True
    assert item.content_payload == {"status": "ok", "latency": 4.2}
    assert item.recency_score == 0.85
    assert item.priority_score == 2.5
    assert item.view_tier == FeedGraduatedTier.COMPACT
    assert item.is_ephemeral is True
    assert item.ttl_seconds == 300.0
    assert item.metadata == {"cluster": "alpha"}


def test_feed_item_from_plate_node():
    plate = PlateNodePayload(
        node_id=42,
        file_path="/workspace/docs/charter.md",
        display_title="Aether Charter",
        archetype=PlateArchetype.DOCUMENT,
        snippet="System axioms and rules...",
        mass=2.5,
    )
    plate.temporal.is_pinned = True
    plate.temporal.recency_score = 0.95

    feed_item = FeedItem.from_plate_node(plate, is_active_glow=True, has_dot=True)
    assert feed_item.id == "42"
    assert feed_item.title == "Aether Charter"
    assert feed_item.type == "document"
    assert feed_item.is_pinned is True
    assert feed_item.is_active_glow is True
    assert feed_item.has_dot is True
    assert feed_item.content_payload["snippet"] == "System axioms and rules..."
    assert feed_item.priority_score == 2.5
    assert feed_item.recency_score == 0.95


def test_notification_states():
    engine = FeedEngine()
    item = engine.add_item({"id": "item-10", "title": "System Alert", "type": "alert"})

    assert item.is_active_glow is False
    assert item.has_dot is False

    # Trigger notification
    engine.trigger_notification("item-10", glow=True, dot=True)
    updated = engine.get_item("item-10")
    assert updated.is_active_glow is True
    assert updated.has_dot is True

    # Mark seen (clears glow and dot)
    engine.mark_seen("item-10")
    assert updated.is_active_glow is False
    assert updated.has_dot is False

    # Granular update
    engine.set_notification_state("item-10", is_active_glow=True)
    assert updated.is_active_glow is True
    assert updated.has_dot is False


def test_header_anchors_query():
    engine = FeedEngine()
    now = time.time()

    # Add unpinned items
    engine.add_item({"id": "unpinned-1", "title": "Regular 1", "is_pinned": False, "timestamp": now})
    engine.add_item({"id": "unpinned-2", "title": "Regular 2", "is_pinned": False, "timestamp": now})

    # Add pinned items for the top micro-pill cluster
    engine.add_item({
        "id": "pin-1",
        "title": "Low Priority Pin",
        "is_pinned": True,
        "priority_score": 1.0,
        "timestamp": now - 100,
    })
    engine.add_item({
        "id": "pin-2",
        "title": "High Priority Pin",
        "is_pinned": True,
        "priority_score": 3.0,
        "timestamp": now,
    })
    engine.add_item({
        "id": "pin-3",
        "title": "Mid Priority Pin",
        "is_pinned": True,
        "priority_score": 2.0,
        "timestamp": now - 50,
    })

    anchors = engine.get_header_anchors()
    assert len(anchors) == 3
    # Check ordering: highest priority first
    assert [a.id for a in anchors] == ["pin-2", "pin-3", "pin-1"]

    # Test as_dicts
    anchor_dicts = engine.get_header_anchors(as_dicts=True)
    assert len(anchor_dicts) == 3
    assert anchor_dicts[0]["id"] == "pin-2"
    assert anchor_dicts[0]["isPinned"] is True

    # Unpin pin-2
    engine.unpin_item("pin-2")
    anchors_after = engine.get_header_anchors()
    assert len(anchors_after) == 2
    assert [a.id for a in anchors_after] == ["pin-3", "pin-1"]


def test_flow_stack_query_and_graduation():
    config = FeedConfig(
        max_flow_items=10,
        full_tier_count=2,
        compact_tier_count=5,
        full_recency_threshold_seconds=86400.0,
        compact_recency_threshold_seconds=7 * 86400.0,
    )
    engine = FeedEngine(config=config)
    now = time.time()

    # 1 pinned item (should be excluded from flow stack by default)
    engine.add_item({"id": "pin-item", "title": "Pinned Header", "is_pinned": True, "timestamp": now})

    # Add 12 items spaced in time
    for i in range(12):
        engine.add_item({
            "id": f"flow-{i}",
            "title": f"Flow Item {i}",
            "is_pinned": False,
            "timestamp": now - (i * 3600.0),  # spaced by 1 hour
            "priority_score": 1.0,
        })

    flow = engine.get_flow_stack(now=now)
    # Rolling buffer limited to max_flow_items (10)
    assert len(flow) == 10
    # Pinned item is excluded
    assert all(item.id != "pin-item" for item in flow)

    # First 2 items (indices 0, 1) are recent and within full_tier_count -> FULL
    assert flow[0].view_tier == FeedGraduatedTier.FULL
    assert flow[1].view_tier == FeedGraduatedTier.FULL

    # Next 3 items (indices 2, 3, 4) are within compact_tier_count -> COMPACT
    assert flow[2].view_tier == FeedGraduatedTier.COMPACT
    assert flow[3].view_tier == FeedGraduatedTier.COMPACT
    assert flow[4].view_tier == FeedGraduatedTier.COMPACT

    # Remaining items (indices 5, 6, 7, 8, 9) -> FADING
    for item in flow[5:]:
        assert item.view_tier == FeedGraduatedTier.FADING


def test_flow_stack_30_day_window():
    config = FeedConfig(active_window_seconds=30 * 86400.0)
    engine = FeedEngine(config=config)
    now = time.time()

    # Within 30 days (e.g. 5 days ago)
    engine.add_item({"id": "recent", "title": "Recent Item", "timestamp": now - 5 * 86400.0})

    # Outside 30 days (e.g. 35 days ago)
    engine.add_item({"id": "ancient", "title": "Ancient Item", "timestamp": now - 35 * 86400.0})

    flow = engine.get_flow_stack(now=now)
    assert len(flow) == 1
    assert flow[0].id == "recent"


def test_pruning_and_ring_buffer_cap():
    config = FeedConfig(
        ring_buffer_capacity=5,
        active_window_seconds=30 * 86400.0,
        ephemeral_default_ttl_seconds=3600.0,
    )
    engine = FeedEngine(config=config)
    now = time.time()

    # 1 pinned item (protected from ring buffer overflow eviction)
    engine.add_item({"id": "pin-anchor", "title": "Pinned", "is_pinned": True, "timestamp": now - 1000})

    # 8 unpinned items (capacity is 5, so 3 excess items should be pruned)
    for i in range(8):
        engine.add_item({
            "id": f"unpinned-{i}",
            "title": f"Unpinned {i}",
            "is_pinned": False,
            "timestamp": now - (100 - i * 10),
            "priority_score": 1.0,
        })

    stats = engine.prune(now=now)
    assert stats["capacity_pruned"] == 3
    # Pinned item remains
    assert engine.get_item("pin-anchor") is not None
    # 5 unpinned + 1 pinned = 6 total
    assert engine.count() == 6


def test_ephemeral_pruning():
    config = FeedConfig(ephemeral_default_ttl_seconds=3600.0)
    engine = FeedEngine(config=config)
    now = time.time()

    # Ephemeral item that has expired (2 hours old, default TTL is 1 hour)
    engine.add_item({
        "id": "ephem-expired",
        "title": "Old Ephemeral",
        "is_ephemeral": True,
        "timestamp": now - 7200.0,
    })

    # Ephemeral item with custom TTL still active (100s old, custom TTL 300s)
    engine.add_item({
        "id": "ephem-active",
        "title": "Fresh Ephemeral",
        "is_ephemeral": True,
        "ttl_seconds": 300.0,
        "timestamp": now - 100.0,
    })

    # Non-ephemeral item (same age as expired one)
    engine.add_item({
        "id": "permanent-old",
        "title": "Permanent",
        "is_ephemeral": False,
        "timestamp": now - 7200.0,
    })

    stats = engine.prune(now=now)
    assert stats["ephemeral_pruned"] == 1
    assert engine.get_item("ephem-expired") is None
    assert engine.get_item("ephem-active") is not None
    assert engine.get_item("permanent-old") is not None


def test_sqlite_persistence(tmp_path: Path):
    db_file = tmp_path / "feed.db"
    now = time.time()

    # Session 1: Create engine and write items
    with FeedEngine(db_path=db_file) as engine:
        engine.add_item({"id": "persist-1", "title": "Persist One", "timestamp": now, "is_pinned": True})
        engine.add_item({"id": "persist-2", "title": "Persist Two", "timestamp": now, "is_active_glow": True})
        assert engine.count() == 2

    # Session 2: Reopen from SQLite file
    with FeedEngine(db_path=db_file) as engine2:
        assert engine2.count() == 2
        p1 = engine2.get_item("persist-1")
        assert p1 is not None
        assert p1.title == "Persist One"
        assert p1.is_pinned is True

        p2 = engine2.get_item("persist-2")
        assert p2 is not None
        assert p2.is_active_glow is True

        # Test deletion persists
        engine2.remove_item("persist-1")
        assert engine2.count() == 1

    # Session 3: Confirm deletion persisted
    with FeedEngine(db_path=db_file) as engine3:
        assert engine3.count() == 1
        assert engine3.get_item("persist-1") is None
        assert engine3.get_item("persist-2") is not None


def test_event_ledger_integration():
    from unittest.mock import MagicMock

    engine = FeedEngine()
    fake_ledger = MagicMock()
    fake_ledger.get_recent_events.return_value = [
        {
            "id": 101,
            "timestamp": time.time(),
            "event_type": "omni_query",
            "target_id": 5,
            "archetype": "document",
            "payload": '{"query": "quantum gravity dynamics"}',
        },
        {
            "id": 102,
            "timestamp": time.time(),
            "event_type": "plate_focus",
            "target_id": 12,
            "archetype": "code",
            "payload": {"title": "ast_parser.py"},
        },
    ]

    items = engine.ingest_from_event_ledger(fake_ledger)
    assert len(items) == 2
    assert items[0].id == "ledger_101"
    assert items[0].title == "quantum gravity dynamics"
    assert items[0].type == "omni_query"

    assert items[1].id == "ledger_102"
    assert items[1].title == "ast_parser.py"
    assert items[1].type == "plate_focus"


