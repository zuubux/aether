"""
Feed Controller Implementation
Bridges the FeedEngine subsystem to The Feed presentation surfaces, managing
header anchor pins, graduated 30-day flow stacks, and notification states.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

try:
    from .base_controller import BaseController
except (ImportError, ValueError):
    from controllers.base_controller import BaseController

try:
    from ..plate_engine import (
        FeedConfig,
        FeedEngine,
        FeedGraduatedTier,
        FeedItem,
    )
except (ImportError, ValueError):
    from aia_canvas.src.plate_engine import (
        FeedConfig,
        FeedEngine,
        FeedGraduatedTier,
        FeedItem,
    )

logger = logging.getLogger("aia_canvas.controllers.feed_controller")


class FeedController(BaseController):
    """
    Domain controller bridging FeedEngine to QML presentation components.
    Exposes headerAnchors, graduated rolling flowStack, notification indicators,
    and notification/lifecycle slots.
    """

    headerAnchorsChanged = pyqtSignal()
    flowStackChanged = pyqtSignal()
    unreadCountChanged = pyqtSignal(int)
    feedRefreshed = pyqtSignal()
    itemNotificationChanged = pyqtSignal(str, bool, bool)  # itemId, is_active_glow, has_dot
    itemPinnedChanged = pyqtSignal(str, bool)             # itemId, is_pinned
    itemAdded = pyqtSignal(str)                           # itemId
    itemRemoved = pyqtSignal(str)                         # itemId

    def __init__(
        self,
        bridge: Optional[Any] = None,
        parent: Optional[QObject] = None,
        engine: Optional[FeedEngine] = None,
        config: Optional[FeedConfig] = None,
    ) -> None:
        super().__init__(bridge, parent)
        self.engine: FeedEngine = engine or FeedEngine(config=config)

    # -------------------------------------------------------------------------
    # QML Properties
    # -------------------------------------------------------------------------

    @pyqtProperty(list, notify=headerAnchorsChanged)
    def headerAnchors(self) -> List[Dict[str, Any]]:
        """List[dict]: Pinned items rendered as header anchor micro-pills (defaults to [])."""
        if not hasattr(self, "engine") or self.engine is None:
            return []
        anchors = self.engine.get_header_anchors(as_dicts=True)
        return anchors if anchors is not None else []

    @pyqtProperty(list, notify=flowStackChanged)
    def flowStack(self) -> List[Dict[str, Any]]:
        """List[dict]: Rolling 30-day items graduated into view tiers (full, compact, fading) (defaults to [])."""
        if not hasattr(self, "engine") or self.engine is None:
            return []
        stack = self.engine.get_flow_stack(as_dicts=True)
        return stack if stack is not None else []

    @pyqtProperty(int, notify=unreadCountChanged)
    def unreadCount(self) -> int:
        """int: Number of items with active glow or unread dot indicators."""
        if not hasattr(self, "engine") or self.engine is None:
            return 0
        count = 0
        for item in self.engine.all_items():
            if item.has_dot is True or item.is_active_glow is True:
                count += 1
        return count

    @pyqtProperty(int, notify=flowStackChanged)
    def totalCount(self) -> int:
        """int: Total number of items retained in the feed."""
        if not hasattr(self, "engine") or self.engine is None:
            return 0
        return self.engine.count()

    # -------------------------------------------------------------------------
    # Notification State Manipulation Slots
    # -------------------------------------------------------------------------

    @pyqtSlot(str, result=bool)
    def mark_seen(self, item_id: str) -> bool:
        """Clears both active glow and unread dot states for an item."""
        if item_id is None:
            return False
        key = str(item_id)
        item = self.engine.mark_seen(key)
        if item is not None:
            self.itemNotificationChanged.emit(item.id, False, False)
            self.headerAnchorsChanged.emit()
            self.flowStackChanged.emit()
            self.unreadCountChanged.emit(self.unreadCount)
            return True
        return False

    @pyqtSlot(str, result=bool)
    def markSeen(self, item_id: str) -> bool:
        """CamelCase alias for mark_seen."""
        return self.mark_seen(item_id)

    @pyqtSlot(str, bool, bool, result=bool)
    @pyqtSlot(str, result=bool)
    def trigger_notification(self, item_id: str, glow: bool = True, dot: bool = True) -> bool:
        """Activates notification flags (glow/dot) on an item."""
        if item_id is None:
            return False
        key = str(item_id)
        item = self.engine.trigger_notification(key, glow=bool(glow), dot=bool(dot))
        if item is not None:
            self.itemNotificationChanged.emit(item.id, item.is_active_glow, item.has_dot)
            self.headerAnchorsChanged.emit()
            self.flowStackChanged.emit()
            self.unreadCountChanged.emit(self.unreadCount)
            return True
        return False

    @pyqtSlot(str, bool, bool, result=bool)
    @pyqtSlot(str, result=bool)
    def triggerNotification(self, item_id: str, glow: bool = True, dot: bool = True) -> bool:
        """CamelCase alias for trigger_notification."""
        return self.trigger_notification(item_id, glow, dot)
    # -------------------------------------------------------------------------
    # Refresh & Maintenance Slots
    # -------------------------------------------------------------------------

    @pyqtSlot()
    def refresh(self) -> None:
        """Enforces time-decay pruning and emits synchronization signals."""
        self.engine.prune()
        self.feedRefreshed.emit()
        self.headerAnchorsChanged.emit()
        self.flowStackChanged.emit()
        self.unreadCountChanged.emit(self.unreadCount)

    @pyqtSlot()
    def refreshFeed(self) -> None:
        """CamelCase alias for refresh."""
        self.refresh()

    @pyqtSlot()
    def refresh_feed(self) -> None:
        """Snake_case alias for refresh."""
        self.refresh()

    # -------------------------------------------------------------------------
    # Pinning & Anchor Management Slots
    # -------------------------------------------------------------------------

    @pyqtSlot(str, bool, result=bool)
    @pyqtSlot(str, result=bool)
    def pin_item(self, item_id: str, is_pinned: bool = True) -> bool:
        """Sets or clears pinned status for an item."""
        if item_id is None:
            return False
        key = str(item_id)
        item = self.engine.pin_item(key, is_pinned=bool(is_pinned))
        if item is not None:
            self.itemPinnedChanged.emit(item.id, item.is_pinned)
            self.headerAnchorsChanged.emit()
            self.flowStackChanged.emit()
            return True
        return False

    @pyqtSlot(str, bool, result=bool)
    @pyqtSlot(str, result=bool)
    def pinItem(self, item_id: str, is_pinned: bool = True) -> bool:
        """CamelCase alias for pin_item."""
        return self.pin_item(item_id, is_pinned)

    @pyqtSlot(str, result=bool)
    def unpin_item(self, item_id: str) -> bool:
        """Unpins an item from the header anchors."""
        return self.pin_item(item_id, is_pinned=False)

    @pyqtSlot(str, result=bool)
    def unpinItem(self, item_id: str) -> bool:
        """CamelCase alias for unpin_item."""
        return self.unpin_item(item_id)

    @pyqtSlot(str, result=bool)
    def toggle_pin(self, item_id: str) -> bool:
        """Inverts pinned status for an item."""
        if item_id is None:
            return False
        key = str(item_id)
        item = self.engine.toggle_pin(key)
        if item is not None:
            self.itemPinnedChanged.emit(item.id, item.is_pinned)
            self.headerAnchorsChanged.emit()
            self.flowStackChanged.emit()
            return True
        return False

    @pyqtSlot(str, result=bool)
    def togglePin(self, item_id: str) -> bool:
        """CamelCase alias for toggle_pin."""
        return self.toggle_pin(item_id)

    # -------------------------------------------------------------------------
    # Item Ingestion & CRUD Slots
    # -------------------------------------------------------------------------

    def add_item(self, item_data: Union[dict[str, Any], FeedItem]) -> str:
        """
        Adds or updates a feed item using explicit is not None property parsing.
        Emits appropriate change signals.
        """
        if isinstance(item_data, FeedItem):
            item = self.engine.add_item(item_data)
        elif isinstance(item_data, dict):
            item = self.engine.add_item(item_data)
        else:
            raise TypeError(f"Expected dict or FeedItem, got {type(item_data).__name__}")

        self.itemAdded.emit(item.id)
        self.headerAnchorsChanged.emit()
        self.flowStackChanged.emit()
        self.unreadCountChanged.emit(self.unreadCount)
        return item.id

    @pyqtSlot("QVariantMap", result=str)
    def addItem(self, item_data: dict[str, Any]) -> str:
        """QML invokable slot to add an item."""
        return self.add_item(item_data)

    @pyqtSlot(str, result=bool)
    def remove_item(self, item_id: str) -> bool:
        """Removes an item by identifier."""
        if item_id is None:
            return False
        key = str(item_id)
        res = self.engine.remove_item(key)
        if res:
            self.itemRemoved.emit(key)
            self.headerAnchorsChanged.emit()
            self.flowStackChanged.emit()
            self.unreadCountChanged.emit(self.unreadCount)
            return True
        return False

    @pyqtSlot(str, result=bool)
    def removeItem(self, item_id: str) -> bool:
        """CamelCase alias for remove_item."""
        return self.remove_item(item_id)

    def get_item(self, item_id: str) -> Optional[dict[str, Any]]:
        """Retrieve dictionary representation of a feed item."""
        if item_id is None:
            return None
        item = self.engine.get_item(str(item_id))
        return item.to_dict() if item is not None else None

    @pyqtSlot(str, result="QVariantMap")
    def getItem(self, item_id: str) -> dict[str, Any]:
        """QML invokable slot to retrieve item dictionary."""
        val = self.get_item(item_id)
        return val if val is not None else {}

    @pyqtSlot()
    def clear_all(self) -> None:
        """Clears all items from the feed."""
        for item in self.engine.all_items():
            self.engine.remove_item(item.id)
        self.headerAnchorsChanged.emit()
        self.flowStackChanged.emit()
        self.unreadCountChanged.emit(0)

    @pyqtSlot()
    def clearAll(self) -> None:
        """CamelCase alias for clear_all."""
        self.clear_all()

