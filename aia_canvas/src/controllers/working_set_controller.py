"""Working Set Controller Implementation.

Manages active working set slates, Tier 1 focal focus, and Tier 1.25 companion satellites.
"""

from collections import OrderedDict
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

try:
    from .base_controller import BaseController
except (ImportError, ValueError):
    from controllers.base_controller import BaseController


class WorkingSetController(BaseController):
    """Controller managing active working set slates, focal stage, and LRU satellite pool."""

    activeSlatesChanged = pyqtSignal()
    focalSlateChanged = pyqtSignal(int)

    MAX_SATELLITES = 6

    def __init__(self, bridge: Any, parent: Optional[object] = None):
        super().__init__(bridge, parent)
        self._focal_slate_id: int = 0
        self._satellites: OrderedDict[int, Dict[str, Any]] = OrderedDict()
        self._slate_meta: Dict[int, Dict[str, Any]] = {}

    @pyqtProperty("QVariantList", notify=activeSlatesChanged)
    def activeSlates(self) -> List[Dict[str, Any]]:
        """List[dict]: Snapshot list of active satellite slates currently in the workspace."""
        return list(self._satellites.values())

    @pyqtProperty(int, notify=focalSlateChanged)
    def focalSlateId(self) -> int:
        """int: ID of the primary node occupying Tier 1 focal center stage."""
        return self._focal_slate_id

    def _resolve_meta(self, node_id: int, archetype: str = "", title: str = "") -> Dict[str, Any]:
        """Resolve or synthesize metadata dictionary for a given slate node."""
        if not archetype or not title:
            existing = self._slate_meta.get(node_id, {})
            if not archetype and "archetype" in existing:
                archetype = existing["archetype"]
            if not title and "title" in existing:
                title = existing["title"]

        if (not archetype or not title) and hasattr(self.bridge, "store") and self.bridge.store:
            try:
                node = self.bridge.store.get_node(node_id)
                if node:
                    if not archetype:
                        archetype = getattr(node, "archetype", "document")
                    if not title:
                        fpath = getattr(node, "filePath", "") or getattr(node, "path", "")
                        if fpath:
                            import os
                            title = os.path.basename(fpath)
            except Exception as e:
                self.log_debug(f"Could not resolve store metadata for node {node_id}: {e}")

        return {
            "node_id": node_id,
            "nodeId": node_id,
            "archetype": archetype or "document",
            "title": title or f"Node {node_id}",
        }

    @pyqtSlot(int, str, str)
    @pyqtSlot(int)
    def open_slate(self, node_id: int, archetype: str = "", title: str = "") -> None:
        """Promotes a node to primary focal center stage, pushing the previous focal node
        into the Tier 1.25 satellite pool (max 6 satellites, LRU eviction).
        """
        if node_id <= 0:
            return

        meta = self._resolve_meta(node_id, archetype, title)
        self._slate_meta[node_id] = meta

        if self._focal_slate_id == node_id:
            return

        if node_id in self._satellites:
            del self._satellites[node_id]

        prev_focal = self._focal_slate_id
        if prev_focal > 0 and prev_focal != node_id:
            prev_meta = self._slate_meta.get(prev_focal) or self._resolve_meta(prev_focal)
            if prev_focal in self._satellites:
                del self._satellites[prev_focal]
            self._satellites[prev_focal] = prev_meta

            while len(self._satellites) > self.MAX_SATELLITES:
                evicted_id, _ = self._satellites.popitem(last=False)
                self.log_debug(f"LRU eviction: satellite slate {evicted_id} evicted")

        self._focal_slate_id = node_id
        self.focalSlateChanged.emit(self._focal_slate_id)
        self.activeSlatesChanged.emit()

    @pyqtSlot(int, str, str)
    @pyqtSlot(int)
    def openSlate(self, node_id: int, archetype: str = "", title: str = "") -> None:
        self.open_slate(node_id, archetype, title)

    @pyqtSlot(int)
    def promote_to_focal(self, node_id: int) -> None:
        """Swaps an active Tier 1.25 satellite directly into Tier 1 focal center stage."""
        if node_id <= 0 or node_id == self._focal_slate_id:
            return

        if node_id not in self._satellites:
            self.log_debug(f"promote_to_focal: node {node_id} is not an active satellite")
            return

        promoted_meta = self._satellites.pop(node_id)
        self._slate_meta[node_id] = promoted_meta

        prev_focal = self._focal_slate_id
        if prev_focal > 0:
            prev_meta = self._slate_meta.get(prev_focal) or self._resolve_meta(prev_focal)
            self._satellites[prev_focal] = prev_meta

            while len(self._satellites) > self.MAX_SATELLITES:
                self._satellites.popitem(last=False)

        self._focal_slate_id = node_id
        self.focalSlateChanged.emit(self._focal_slate_id)
        self.activeSlatesChanged.emit()

    @pyqtSlot(int)
    def promoteToFocal(self, node_id: int) -> None:
        self.promote_to_focal(node_id)

    @pyqtSlot(int)
    def dismiss_slate(self, node_id: int) -> None:
        """Dismisses an active satellite slate."""
        if node_id in self._satellites:
            del self._satellites[node_id]
            self.activeSlatesChanged.emit()

        if node_id == self._focal_slate_id:
            self._focal_slate_id = 0
            self.focalSlateChanged.emit(0)

    @pyqtSlot(int)
    def dismissSlate(self, node_id: int) -> None:
        self.dismiss_slate(node_id)

    @pyqtSlot()
    def clear_all(self) -> None:
        """Resets all active slates and focal state."""
        self._satellites.clear()
        self._slate_meta.clear()
        self._focal_slate_id = 0
        self.focalSlateChanged.emit(0)
        self.activeSlatesChanged.emit()

    @pyqtSlot()
    def clearAll(self) -> None:
        self.clear_all()

