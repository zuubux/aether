"""
Plate Engine - Feed Engine Subsystem
Handles header anchor pins, graduated flow stacks, notification states (glow/dot),
and time-decay / pruning logic for The Feed.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger("aia_canvas.plate_engine.feed_engine")


class FeedGraduatedTier(str, Enum):
    """
    Graduated presentation tiers for rolling flow stack items.
    """
    FULL = "full"
    COMPACT = "compact"
    FADING = "fading"

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value.lower() == other.strip().lower()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def from_str(cls, val: str | FeedGraduatedTier | None) -> FeedGraduatedTier:
        """
        Safely resolve a string or enum instance to a FeedGraduatedTier.
        """
        if isinstance(val, cls):
            return val
        if not val:
            return cls.FULL
        norm = str(val).strip().lower()
        mapping = {
            "full": cls.FULL,
            "expanded": cls.FULL,
            "hero": cls.FULL,
            "compact": cls.COMPACT,
            "mid": cls.COMPACT,
            "standard": cls.COMPACT,
            "fading": cls.FADING,
            "dim": cls.FADING,
            "faded": cls.FADING,
            "tail": cls.FADING,
        }
        return mapping.get(norm, cls.FULL)


@dataclass(slots=True)
class FeedItem:
    """
    Canonical data model representing an item in The Feed.
    Encapsulates identity, notification states (glow/dot), pin anchors,
    content payloads, recency/priority scores, and graduated view tiers.
    """
    id: str
    title: str = ""
    type: str = "item"
    timestamp: float = field(default_factory=time.time)
    is_pinned: bool = False
    is_active_glow: bool = False
    has_dot: bool = False
    content_payload: dict[str, Any] = field(default_factory=dict)
    recency_score: float = 1.0
    priority_score: float = 1.0
    view_tier: FeedGraduatedTier = FeedGraduatedTier.FULL
    is_ephemeral: bool = False
    ttl_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def item_id(self) -> str:
        return self.id

    @property
    def payload(self) -> dict[str, Any]:
        return self.content_payload

    @property
    def effective_score(self) -> float:
        """Composite priority and recency score."""
        return self.priority_score * self.recency_score

    def to_dict(self) -> dict[str, Any]:
        """
        Dual snake_case and camelCase serialization for seamless QML/IPC consumption.
        """
        return {
            "id": self.id,
            "itemId": self.id,
            "title": self.title,
            "type": self.type,
            "timestamp": self.timestamp,
            "is_pinned": self.is_pinned,
            "isPinned": self.is_pinned,
            "is_active_glow": self.is_active_glow,
            "isActiveGlow": self.is_active_glow,
            "has_dot": self.has_dot,
            "hasDot": self.has_dot,
            "content_payload": dict(self.content_payload),
            "contentPayload": dict(self.content_payload),
            "payload": dict(self.content_payload),
            "recency_score": self.recency_score,
            "recencyScore": self.recency_score,
            "priority_score": self.priority_score,
            "priorityScore": self.priority_score,
            "effective_score": self.effective_score,
            "effectiveScore": self.effective_score,
            "view_tier": str(self.view_tier),
            "viewTier": str(self.view_tier),
            "is_ephemeral": self.is_ephemeral,
            "isEphemeral": self.is_ephemeral,
            "ttl_seconds": self.ttl_seconds,
            "ttlSeconds": self.ttl_seconds,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FeedItem:
        """
        Strict contract reconstruction using explicit `is not None` lookups.
        """
        raw_id = d.get("id") if d.get("id") is not None else d.get("itemId")
        if raw_id is None:
            raw_id = d.get("item_id") if d.get("item_id") is not None else d.get("node_id")
        if raw_id is None:
            raw_id = d.get("nodeId")
        item_id = str(raw_id) if raw_id is not None else str(uuid.uuid4())

        title_val = d.get("title") if d.get("title") is not None else d.get("display_title")
        if title_val is None:
            title_val = d.get("displayTitle")
        title = str(title_val) if title_val is not None else ""

        type_val = d.get("type") if d.get("type") is not None else d.get("feed_type")
        if type_val is None:
            type_val = d.get("feedType") if d.get("feedType") is not None else d.get("event_type")
        if type_val is None:
            type_val = d.get("eventType")
        item_type = str(type_val) if type_val is not None else "item"

        ts_val = d.get("timestamp") if d.get("timestamp") is not None else d.get("created_at")
        if ts_val is None:
            ts_val = d.get("createdAt")
        timestamp = float(ts_val) if ts_val is not None else time.time()

        pinned_val = d.get("is_pinned") if d.get("is_pinned") is not None else d.get("isPinned")
        if pinned_val is None:
            pinned_val = d.get("pinned")
        is_pinned = bool(pinned_val) if pinned_val is not None else False

        glow_val = d.get("is_active_glow") if d.get("is_active_glow") is not None else d.get("isActiveGlow")
        if glow_val is None:
            glow_val = d.get("glow")
        is_active_glow = bool(glow_val) if glow_val is not None else False

        dot_val = d.get("has_dot") if d.get("has_dot") is not None else d.get("hasDot")
        if dot_val is None:
            dot_val = d.get("dot")
        has_dot = bool(dot_val) if dot_val is not None else False

        payload_val = (
            d.get("content_payload")
            if d.get("content_payload") is not None
            else d.get("contentPayload")
        )
        if payload_val is None:
            payload_val = d.get("payload") if d.get("payload") is not None else d.get("content")
        if isinstance(payload_val, str):
            try:
                content_payload = json.loads(payload_val)
            except Exception:
                content_payload = {"raw": payload_val}
        elif isinstance(payload_val, dict):
            content_payload = dict(payload_val)
        else:
            content_payload = {}

        recency_val = (
            d.get("recency_score")
            if d.get("recency_score") is not None
            else d.get("recencyScore")
        )
        recency_score = float(recency_val) if recency_val is not None else 1.0

        priority_val = (
            d.get("priority_score")
            if d.get("priority_score") is not None
            else d.get("priorityScore")
        )
        priority_score = float(priority_val) if priority_val is not None else 1.0

        tier_val = d.get("view_tier") if d.get("view_tier") is not None else d.get("viewTier")
        view_tier = FeedGraduatedTier.from_str(tier_val)

        ephemeral_val = (
            d.get("is_ephemeral")
            if d.get("is_ephemeral") is not None
            else d.get("isEphemeral")
        )
        is_ephemeral = bool(ephemeral_val) if ephemeral_val is not None else False

        ttl_val = d.get("ttl_seconds") if d.get("ttl_seconds") is not None else d.get("ttlSeconds")
        ttl_seconds = float(ttl_val) if ttl_val is not None else None

        meta_val = d.get("metadata")
        if isinstance(meta_val, str):
            try:
                metadata = json.loads(meta_val)
            except Exception:
                metadata = {}
        elif isinstance(meta_val, dict):
            metadata = dict(meta_val)
        else:
            metadata = {}

        return cls(
            id=item_id,
            title=title,
            type=item_type,
            timestamp=timestamp,
            is_pinned=is_pinned,
            is_active_glow=is_active_glow,
            has_dot=has_dot,
            content_payload=content_payload,
            recency_score=recency_score,
            priority_score=priority_score,
            view_tier=view_tier,
            is_ephemeral=is_ephemeral,
            ttl_seconds=ttl_seconds,
            metadata=metadata,
        )

    @classmethod
    def from_plate_node(
        cls,
        plate: Any,
        view_tier: FeedGraduatedTier = FeedGraduatedTier.FULL,
        is_active_glow: bool = False,
        has_dot: bool = False,
    ) -> FeedItem:
        """
        Instantiate a FeedItem from a PlateNodePayload.
        """
        plate_id = getattr(plate, "node_id", None)
        id_str = str(plate_id) if plate_id is not None else str(uuid.uuid4())
        title = (
            getattr(plate, "display_title", None)
            or getattr(plate, "file_name", None)
            or f"Plate {id_str}"
        )
        arch = getattr(plate, "archetype", None)
        arch_str = arch.value if hasattr(arch, "value") else str(arch or "document")

        temporal = getattr(plate, "temporal", None) or getattr(plate, "temporal_state", None)
        is_pinned = getattr(plate, "is_pinned", False)
        recency_score = 1.0
        ts = time.time()
        if temporal is not None:
            if not is_pinned:
                is_pinned = getattr(temporal, "is_pinned", False)
            recency_score = getattr(temporal, "recency_score", 1.0)
            ts = getattr(temporal, "last_interaction_epoch", ts)

        snippet = getattr(plate, "snippet", "")
        file_path = getattr(plate, "file_path", "")

        return cls(
            id=id_str,
            title=title,
            type=arch_str,
            timestamp=ts,
            is_pinned=is_pinned,
            is_active_glow=is_active_glow,
            has_dot=has_dot,
            content_payload={
                "file_path": file_path,
                "snippet": snippet,
                "archetype": arch_str,
            },
            recency_score=recency_score,
            priority_score=getattr(plate, "mass", 1.0),
            view_tier=view_tier,
            metadata=dict(getattr(plate, "metadata", {})),
        )

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> FeedItem:
        """
        Instantiate a FeedItem from an EventLedger row or event dict.
        """
        return cls.from_dict(event)


@dataclass(slots=True)
class FeedConfig:
    """
    Configuration parameters for feed flow, buffer capacity, time decay, and pruning.
    """
    max_flow_items: int = 24                         # Rolling buffer cap (~24 items)
    ring_buffer_capacity: int = 120                  # Total ring buffer capacity
    active_window_seconds: float = 30.0 * 86400.0      # 30-day active window (2,592,000s)
    ephemeral_default_ttl_seconds: float = 3600.0      # 1 hour active threshold for ephemeral items
    full_tier_count: int = 4                         # Top micro-stack count eligible for FULL view
    compact_tier_count: int = 12                     # Mid-stack count eligible for COMPACT view
    full_recency_threshold_seconds: float = 2.0 * 86400.0    # 48 hours threshold for FULL view
    compact_recency_threshold_seconds: float = 7.0 * 86400.0 # 7 days threshold for COMPACT view
    half_life_seconds: float = 72.0 * 3600.0         # 72 hours for temporal half-life decay
    auto_prune_on_insert: bool = False               # Optional automatic prune check on insertion


class FeedEngine:
    """
    Backend module for The Feed.
    Orchestrates header anchor pins, graduated flow stacks, notification states,
    and ring buffer / time-decay pruning logic.
    """

    def __init__(
        self,
        config: FeedConfig | None = None,
        db_path: Path | str | None = None,
    ) -> None:
        self.config = config or FeedConfig()
        self._items: dict[str, FeedItem] = {}
        self.conn: sqlite3.Connection | None = None
        self.db_path: Path | None = Path(db_path) if db_path is not None else None

        if self.db_path is not None:
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        """Initialize SQLite storage schema with WAL mode and incremental vacuum."""
        if self.db_path is None:
            return

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA auto_vacuum;")
        res = cursor.fetchone()
        if res is not None and res[0] != 2:
            cursor.execute("PRAGMA auto_vacuum = INCREMENTAL;")
            cursor.execute("VACUUM;")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feed_items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                is_pinned INTEGER NOT NULL DEFAULT 0,
                is_active_glow INTEGER NOT NULL DEFAULT 0,
                has_dot INTEGER NOT NULL DEFAULT 0,
                content_payload TEXT NOT NULL DEFAULT '{}',
                recency_score REAL NOT NULL DEFAULT 1.0,
                priority_score REAL NOT NULL DEFAULT 1.0,
                view_tier TEXT NOT NULL DEFAULT 'full',
                is_ephemeral INTEGER NOT NULL DEFAULT 0,
                ttl_seconds REAL,
                metadata TEXT NOT NULL DEFAULT '{}'
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_feed_timestamp ON feed_items(timestamp);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_feed_pinned ON feed_items(is_pinned);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_feed_type ON feed_items(type);"
        )
        self.conn.commit()

        # Load initial items into cache
        self.sync_from_db()

    def sync_from_db(self) -> int:
        """Populate the in-memory cache from the backing SQLite database."""
        if self.conn is None:
            return 0

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM feed_items ORDER BY timestamp DESC;")
        rows = cursor.fetchall()
        for row in rows:
            d = dict(row)
            item = FeedItem.from_dict(d)
            self._items[item.id] = item
        return len(self._items)

    def _persist_item(self, item: FeedItem) -> None:
        """Persist or update an individual item in SQLite."""
        if self.conn is None:
            return

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO feed_items (
                id, title, type, timestamp, is_pinned, is_active_glow, has_dot,
                content_payload, recency_score, priority_score, view_tier,
                is_ephemeral, ttl_seconds, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                type = excluded.type,
                timestamp = excluded.timestamp,
                is_pinned = excluded.is_pinned,
                is_active_glow = excluded.is_active_glow,
                has_dot = excluded.has_dot,
                content_payload = excluded.content_payload,
                recency_score = excluded.recency_score,
                priority_score = excluded.priority_score,
                view_tier = excluded.view_tier,
                is_ephemeral = excluded.is_ephemeral,
                ttl_seconds = excluded.ttl_seconds,
                metadata = excluded.metadata;
            """,
            (
                item.id,
                item.title,
                item.type,
                item.timestamp,
                1 if item.is_pinned else 0,
                1 if item.is_active_glow else 0,
                1 if item.has_dot else 0,
                json.dumps(item.content_payload),
                item.recency_score,
                item.priority_score,
                str(item.view_tier),
                1 if item.is_ephemeral else 0,
                item.ttl_seconds,
                json.dumps(item.metadata),
            ),
        )
        self.conn.commit()

    def _delete_persisted(self, ids: Sequence[str]) -> None:
        """Batch remove items from SQLite and execute incremental vacuum."""
        if self.conn is None or not ids:
            return

        cursor = self.conn.cursor()
        placeholders = ",".join(["?"] * len(ids))
        cursor.execute(
            f"DELETE FROM feed_items WHERE id IN ({placeholders});",
            tuple(ids),
        )
        self.conn.commit()
        cursor.execute("PRAGMA incremental_vacuum(50);")
        self.conn.commit()
    def add_item(self, item: FeedItem | dict[str, Any]) -> FeedItem:
        """
        Add or update an item in The Feed.
        """
        if isinstance(item, dict):
            feed_item = FeedItem.from_dict(item)
        else:
            feed_item = item

        self._items[feed_item.id] = feed_item
        self._persist_item(feed_item)

        if self.config.auto_prune_on_insert:
            self.prune()

        return feed_item

    def upsert_item(self, item: FeedItem | dict[str, Any]) -> FeedItem:
        """Alias for add_item."""
        return self.add_item(item)

    def get_item(self, item_id: str | int) -> FeedItem | None:
        """Retrieve an item by id."""
        return self._items.get(str(item_id))

    def remove_item(self, item_id: str | int) -> bool:
        """Remove an item by id."""
        key = str(item_id)
        if key in self._items:
            del self._items[key]
            self._delete_persisted([key])
            return True
        return False

    def count(self) -> int:
        """Total items currently retained in memory."""
        return len(self._items)

    def all_items(self) -> list[FeedItem]:
        """Return all feed items currently loaded."""
        return list(self._items.values())

    # -------------------------------------------------------------------------
    # Notification States (Glow / Dot)
    # -------------------------------------------------------------------------

    def set_notification_state(
        self,
        item_id: str | int,
        is_active_glow: bool | None = None,
        has_dot: bool | None = None,
    ) -> FeedItem | None:
        """
        Update notification states for an item.
        """
        item = self.get_item(item_id)
        if item is None:
            return None

        changed = False
        if is_active_glow is not None and item.is_active_glow != is_active_glow:
            item.is_active_glow = bool(is_active_glow)
            changed = True
        if has_dot is not None and item.has_dot != has_dot:
            item.has_dot = bool(has_dot)
            changed = True

        if changed:
            self._persist_item(item)
        return item

    def mark_seen(self, item_id: str | int) -> FeedItem | None:
        """
        Clears both active glow and unread dot states.
        """
        return self.set_notification_state(item_id, is_active_glow=False, has_dot=False)

    def trigger_notification(
        self,
        item_id: str | int,
        glow: bool = True,
        dot: bool = True,
    ) -> FeedItem | None:
        """
        Activates notification flags on an item.
        """
        return self.set_notification_state(item_id, is_active_glow=glow, has_dot=dot)

    # -------------------------------------------------------------------------
    # Pinning & Header Anchors
    # -------------------------------------------------------------------------

    def pin_item(self, item_id: str | int, is_pinned: bool = True) -> FeedItem | None:
        """
        Set or clear pinned status on an item.
        """
        item = self.get_item(item_id)
        if item is None:
            return None

        if item.is_pinned != is_pinned:
            item.is_pinned = is_pinned
            self._persist_item(item)
        return item

    def unpin_item(self, item_id: str | int) -> FeedItem | None:
        """Convenience method to unpin an item."""
        return self.pin_item(item_id, is_pinned=False)

    def toggle_pin(self, item_id: str | int) -> FeedItem | None:
        """Toggle pinned status on an item."""
        item = self.get_item(item_id)
        if item is None:
            return None
        return self.pin_item(item_id, is_pinned=not item.is_pinned)

    def get_header_anchors(
        self,
        as_dicts: bool = False,
    ) -> list[FeedItem] | list[dict[str, Any]]:
        """
        Header Anchors Query:
        Fetches pinned items (`is_pinned = True`) for the top micro-pill cluster.
        Returns pinned items ordered descending by priority, recency, and timestamp.
        """
        anchors = [item for item in self._items.values() if item.is_pinned is True]
        anchors.sort(
            key=lambda x: (x.priority_score, x.recency_score, x.timestamp),
            reverse=True,
        )
        if as_dicts:
            return [item.to_dict() for item in anchors]
        return anchors

    # -------------------------------------------------------------------------
    # Flow Stack Query
    # -------------------------------------------------------------------------

    def compute_recency_decay(
        self,
        item_timestamp: float,
        now: float | None = None,
    ) -> float:
        """
        Computes exponential half-life decay factor:
        score = 2^(-delta_t / half_life_seconds), clamped to [0.0, 1.0].
        """
        current_time = float(now) if now is not None else time.time()
        delta_seconds = max(0.0, current_time - item_timestamp)
        half_life = max(1.0, self.config.half_life_seconds)
        decay = 2.0 ** (-delta_seconds / half_life)
        return max(0.0, min(1.0, decay))

    def get_flow_stack(
        self,
        limit: int | None = None,
        now: float | None = None,
        exclude_pinned: bool = True,
        as_dicts: bool = False,
    ) -> list[FeedItem] | list[dict[str, Any]]:
        """
        Flow Stack Query:
        Fetches the rolling buffer (up to ~24 items, within the 30-day active window)
        and assigns graduated view tiers (`full`, `compact`, `fading`) based on list index
        and recency.
        """
        current_time = float(now) if now is not None else time.time()
        active_cutoff = current_time - self.config.active_window_seconds
        max_items = limit if limit is not None else self.config.max_flow_items

        candidates: list[FeedItem] = []
        for item in self._items.values():
            if exclude_pinned and item.is_pinned:
                continue

            # Enforce 30-day active window
            if item.timestamp < active_cutoff:
                continue

            # Update temporal recency decay score in-place
            if not item.is_pinned:
                item.recency_score = self.compute_recency_decay(item.timestamp, now=current_time)
            else:
                item.recency_score = 1.0

            candidates.append(item)

        # Order by composite priority/recency score and timestamp descending
        candidates.sort(
            key=lambda x: (x.effective_score, x.timestamp),
            reverse=True,
        )

        flow_slice = candidates[:max_items]

        # Assign graduated view tiers based on list index and recency
        for idx, item in enumerate(flow_slice):
            age = max(0.0, current_time - item.timestamp)
            if idx < self.config.full_tier_count and age <= self.config.full_recency_threshold_seconds:
                item.view_tier = FeedGraduatedTier.FULL
            elif idx < self.config.compact_tier_count and age <= self.config.compact_recency_threshold_seconds:
                item.view_tier = FeedGraduatedTier.COMPACT
            else:
                item.view_tier = FeedGraduatedTier.FADING

        if as_dicts:
            return [item.to_dict() for item in flow_slice]
        return flow_slice

    # -------------------------------------------------------------------------
    # Pruning & Ring Buffer Enforcement
    # -------------------------------------------------------------------------

    def prune(self, now: float | None = None) -> dict[str, int]:
        """
        Pruning Check:
        1. Strips ephemeral items past their active threshold (ttl_seconds or default).
        2. Strips items older than the 30-day active window (unless pinned).
        3. Enforces the ring buffer cap by evicting excess unpinned items.
        Returns a dictionary of pruning statistics.
        """
        current_time = float(now) if now is not None else time.time()
        active_cutoff = current_time - self.config.active_window_seconds

        to_delete: set[str] = set()
        ephemeral_pruned = 0
        expired_pruned = 0
        capacity_pruned = 0

        # Step 1: Ephemeral items stripping
        for item in self._items.values():
            if item.is_ephemeral:
                ttl = (
                    item.ttl_seconds
                    if item.ttl_seconds is not None
                    else self.config.ephemeral_default_ttl_seconds
                )
                if (current_time - item.timestamp) > ttl:
                    to_delete.add(item.id)
                    ephemeral_pruned += 1

        # Step 2: 30-day active window expiration (protect pinned items)
        for item in self._items.values():
            if item.id in to_delete:
                continue
            if not item.is_pinned and item.timestamp < active_cutoff:
                to_delete.add(item.id)
                expired_pruned += 1

        # Apply deletions from steps 1 & 2
        for item_id in to_delete:
            self._items.pop(item_id, None)

        # Step 3: Ring buffer cap enforcement on remaining unpinned items
        unpinned_remaining = [item for item in self._items.values() if not item.is_pinned]
        excess = len(unpinned_remaining) - self.config.ring_buffer_capacity
        if excess > 0:
            # Sort ascending by effective score and timestamp (evict least relevant / oldest first)
            unpinned_remaining.sort(key=lambda x: (x.effective_score, x.timestamp))
            for item in unpinned_remaining[:excess]:
                to_delete.add(item.id)
                self._items.pop(item.id, None)
                capacity_pruned += 1

        # Persist deletions to backing SQLite
        if to_delete:
            self._delete_persisted(list(to_delete))

        return {
            "ephemeral_pruned": ephemeral_pruned,
            "expired_pruned": expired_pruned,
            "capacity_pruned": capacity_pruned,
            "total_pruned": len(to_delete),
        }

    # -------------------------------------------------------------------------
    # Integrations (EventLedger, PlateNodePayload)
    # -------------------------------------------------------------------------

    def ingest_from_event_ledger(
        self,
        ledger: Any,
        limit: int = 50,
        event_type: str | None = None,
    ) -> list[FeedItem]:
        """
        Pull recent events from an EventLedger instance, construct FeedItems,
        and ingest them into The Feed.
        """
        if not hasattr(ledger, "get_recent_events"):
            return []

        events = ledger.get_recent_events(limit=limit, event_type=event_type)
        ingested: list[FeedItem] = []
        for ev in events:
            raw_payload = ev.get("payload", {})
            if isinstance(raw_payload, str):
                try:
                    payload_dict = json.loads(raw_payload)
                except Exception:
                    payload_dict = {"raw": raw_payload}
            elif isinstance(raw_payload, dict):
                payload_dict = raw_payload
            else:
                payload_dict = {}

            title = (
                payload_dict.get("query")
                or payload_dict.get("title")
                or payload_dict.get("prompt")
                or f"{ev.get('event_type', 'event')} #{ev.get('id', 0)}"
            )

            feed_item = FeedItem(
                id=f"ledger_{ev.get('id', uuid.uuid4())}",
                title=str(title),
                type=str(ev.get("event_type", "event")),
                timestamp=float(ev.get("timestamp", time.time())),
                is_pinned=False,
                is_active_glow=False,
                has_dot=False,
                content_payload=payload_dict,
                recency_score=1.0,
                priority_score=1.0,
                metadata={"ledger_target_id": ev.get("target_id", 0), "archetype": ev.get("archetype", "")},
            )
            self.add_item(feed_item)
            ingested.append(feed_item)

        return ingested

    def ingest_plate_node(
        self,
        plate: Any,
        view_tier: FeedGraduatedTier = FeedGraduatedTier.FULL,
    ) -> FeedItem:
        """
        Convert a PlateNodePayload into a FeedItem and ingest into The Feed.
        """
        feed_item = FeedItem.from_plate_node(plate, view_tier=view_tier)
        self.add_item(feed_item)
        return feed_item

    # -------------------------------------------------------------------------
    # Teardown / Cleanup
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close SQLite database connection if active."""
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def __enter__(self) -> FeedEngine:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()



