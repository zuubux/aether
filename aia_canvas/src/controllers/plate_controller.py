"""
Plate Canvas Controller Implementation
Post-WIMP spatial layout, Bento grid geometry, single-key AI summary extraction,
and plate spatial manipulation for the Aether presentation layer.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Union
import zlib

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

try:
    from .base_controller import BaseController
except (ImportError, ValueError):
    from controllers.base_controller import BaseController

try:
    from ..plate_engine import (
        BentoAllocation,
        BentoAllocator,
        BentoGridConfig,
        PlateGeometry,
        PlateLifecycleManager,
        PlateNodePayload,
        PlateSummaryEngine,
        parse_plate_payload,
    )
except (ImportError, ValueError):
    from aia_canvas.src.plate_engine import (
        BentoAllocation,
        BentoAllocator,
        BentoGridConfig,
        PlateGeometry,
        PlateLifecycleManager,
        PlateNodePayload,
        PlateSummaryEngine,
        parse_plate_payload,
    )

logger = logging.getLogger("aia_canvas.controllers.plate_controller")


class PlateCanvasController(BaseController):
    """
    Domain controller bridging the PlateEngine to QML spatial views.
    Manages active canvas plates, Bento grid allocations, single-key AI summary
    access (ai_summary), and spatial manipulation (move, resize, pin, close).
    """

    activePlatesChanged = pyqtSignal()
    bentoGeometryChanged = pyqtSignal()
    focalPlateChanged = pyqtSignal(int)
    plateMoved = pyqtSignal(int, float, float)
    plateResized = pyqtSignal(int, float, float)
    platePinned = pyqtSignal(int, bool)
    plateClosed = pyqtSignal(int)
    plateOpened = pyqtSignal(int)
    plateEvicted = pyqtSignal(int)
    summaryUpdated = pyqtSignal(int, str)

    def __init__(
        self,
        bridge: Optional[Any] = None,
        parent: Optional[QObject] = None,
        bento_config: Optional[BentoGridConfig] = None,
    ) -> None:
        super().__init__(bridge, parent)
        self._plates: Dict[int, PlateNodePayload] = {}
        self._bento_allocations: List[BentoAllocation] = []
        self._focal_plate_id: int = 0
        self._bento_config: BentoGridConfig = bento_config or BentoGridConfig()
        self._bento_allocator: BentoAllocator = BentoAllocator(self._bento_config)
        self._summary_engine: PlateSummaryEngine = PlateSummaryEngine()
        self._lifecycle_manager: PlateLifecycleManager = PlateLifecycleManager()
        # Payloads of plates auto-evicted to the feed, retained for lossless restoral
        self._evicted_payloads: Dict[int, Dict[str, Any]] = {}

    @pyqtProperty(list, notify=activePlatesChanged)
    def activePlates(self) -> List[Dict[str, Any]]:
        """List[dict]: Active plates currently on canvas serialized for QML."""
        if not hasattr(self, "_plates") or not self._plates:
            return []
        return [self._serialize_plate(plate) for plate in self._plates.values() if plate is not None]

    @pyqtProperty("QVariantMap", notify=bentoGeometryChanged)
    def bentoGeometry(self) -> Dict[str, Any]:
        """Dict[str, Any]: Resolved Bento grid allocations with geometry and spans (defaults to {})."""
        if not hasattr(self, "_bento_allocations") or not self._bento_allocations:
            return {}
        return {
            str(alloc.node_id): {
                "node_id": alloc.node_id,
                "nodeId": alloc.node_id,
                "col_start": alloc.col_start,
                "colStart": alloc.col_start,
                "col_span": alloc.col_span,
                "colSpan": alloc.col_span,
                "row_start": alloc.row_start,
                "rowStart": alloc.row_start,
                "row_span": alloc.row_span,
                "rowSpan": alloc.row_span,
                "x": alloc.x,
                "y": alloc.y,
                "width": alloc.width,
                "height": alloc.height,
            }
            for alloc in self._bento_allocations
            if alloc is not None
        }

    @pyqtProperty(int, notify=focalPlateChanged)
    def focalPlateId(self) -> int:
        """int: ID of the plate occupying focal stage (0 if none)."""
        return getattr(self, "_focal_plate_id", 0) or 0

    @pyqtProperty(bool, notify=activePlatesChanged)
    def hasPreview(self) -> bool:
        """bool: True while a transient search preview plate is mounted."""
        return any(getattr(p, "is_preview", False) for p in getattr(self, "_plates", {}).values())

    @pyqtProperty(int, notify=activePlatesChanged)
    def plateCount(self) -> int:
        """int: Total number of active plates on the canvas."""
        if not hasattr(self, "_plates") or not self._plates:
            return 0
        return len(self._plates)
    def _serialize_plate(self, plate: PlateNodePayload) -> Dict[str, Any]:
        """Serializes PlateNodePayload with explicit single-key ai_summary extraction."""
        d = plate.to_dict()
        meta = plate.metadata if plate.metadata is not None else {}
        raw_summary = meta.get("ai_summary") if meta.get("ai_summary") is not None else meta.get("aiSummary")
        ai_summary_str = str(raw_summary).strip() if raw_summary is not None else ""
        d["ai_summary"] = ai_summary_str
        d["aiSummary"] = ai_summary_str
        is_prev = getattr(plate, "is_preview", False)
        d["is_preview"] = is_prev
        d["isPreview"] = is_prev
        return d

    # -------------------------------------------------------------------------
    # Single-Key Summary Access (@Slot)
    # -------------------------------------------------------------------------

    @pyqtSlot(int, result=str)
    def get_ai_summary(self, node_id: int) -> str:
        """Retrieves or generates 2-sentence extractive summary for a plate."""
        plate = self._plates.get(int(node_id))
        if plate is None:
            return ""

        summary = self._summary_engine.get_or_generate_summary(plate)
        if plate.metadata is None:
            plate.metadata = {}

        if plate.metadata.get("ai_summary") != summary:
            plate.metadata["ai_summary"] = summary
            self.summaryUpdated.emit(plate.node_id, summary)
            self.activePlatesChanged.emit()

        return summary

    @pyqtSlot(int, result=str)
    def getAiSummary(self, node_id: int) -> str:
        return self.get_ai_summary(node_id)

    @pyqtSlot(int, result=str)
    def ai_summary(self, node_id: int) -> str:
        return self.get_ai_summary(node_id)

    # -------------------------------------------------------------------------
    # Spatial Manipulation Slots (Move, Resize, Pin, Close)
    # -------------------------------------------------------------------------

    @pyqtSlot(int, float, float, result=bool)
    def move_plate(self, node_id: int, x: float, y: float) -> bool:
        """Move plate to explicit canvas coordinates."""
        plate = self._plates.get(int(node_id))
        if plate is None:
            return False

        px_x = round(float(x), 2)
        px_y = round(float(y), 2)
        plate.geometry.x = px_x
        plate.geometry.y = px_y
        plate.temporal.is_user_placed = True
        plate.temporal.touch()

        self.plateMoved.emit(plate.node_id, px_x, px_y)
        self.activePlatesChanged.emit()
        return True

    @pyqtSlot(int, float, float, result=bool)
    def movePlate(self, node_id: int, x: float, y: float) -> bool:
        return self.move_plate(node_id, x, y)

    @pyqtSlot(int, float, float, result=bool)
    def resize_plate(self, node_id: int, width: float, height: float) -> bool:
        """Manually resize plate dimensions with safety clamps."""
        plate = self._plates.get(int(node_id))
        if plate is None:
            return False

        clamped_w = round(max(120.0, float(width)), 2)
        clamped_h = round(max(80.0, float(height)), 2)
        plate.geometry.width = clamped_w
        plate.geometry.height = clamped_h
        plate.temporal.is_user_placed = True
        plate.temporal.touch()

        self.plateResized.emit(plate.node_id, clamped_w, clamped_h)
        self.activePlatesChanged.emit()
        return True

    @pyqtSlot(int, float, float, result=bool)
    def resizePlate(self, node_id: int, width: float, height: float) -> bool:
        return self.resize_plate(node_id, width, height)

    @pyqtSlot(int, bool, result=bool)
    @pyqtSlot(int, result=bool)
    def pin_plate(self, node_id: int, is_pinned: bool = True) -> bool:
        """Pin or unpin plate to lock against temporal decay sweeps."""
        plate = self._plates.get(int(node_id))
        if plate is None:
            return False

        pinned_val = bool(is_pinned)
        plate.temporal.is_pinned = pinned_val
        plate.temporal.touch()

        self.platePinned.emit(plate.node_id, pinned_val)
        self.activePlatesChanged.emit()
        return True

    @pyqtSlot(int, bool, result=bool)
    @pyqtSlot(int, result=bool)
    def pinPlate(self, node_id: int, is_pinned: bool = True) -> bool:
        return self.pin_plate(node_id, is_pinned)

    @pyqtSlot(int, result=bool)
    def toggle_pin(self, node_id: int) -> bool:
        """Toggle pinned state for a plate."""
        plate = self._plates.get(int(node_id))
        if plate is None:
            return False
        return self.pin_plate(plate.node_id, not plate.temporal.is_pinned)

    @pyqtSlot(int, result=bool)
    def togglePin(self, node_id: int) -> bool:
        return self.toggle_pin(node_id)

    @pyqtSlot(int, result=bool)
    def close_plate(self, node_id: int) -> bool:
        """Dismisses and removes a plate from the active canvas."""
        nid = int(node_id)
        if nid not in self._plates:
            return False

        del self._plates[nid]

        if self._focal_plate_id == nid:
            self._focal_plate_id = 0
            self.focalPlateChanged.emit(0)

        self.recalculate_bento()
        self.plateClosed.emit(nid)
        self.activePlatesChanged.emit()
        return True

    @pyqtSlot(int, result=bool)
    def closePlate(self, node_id: int) -> bool:
        return self.close_plate(node_id)

    # -------------------------------------------------------------------------
    # Ingestion & Focal Stage Management
    # -------------------------------------------------------------------------

    def _read_snippet_fallback(self, file_path: Optional[str]) -> str:
        """Fallback reading a ~2KB head buffer from filePath if snippet is empty."""
        if not file_path:
            return ""
        try:
            p = Path(file_path)
            if p.is_file():
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(2048).strip()
                    if content and "\x00" not in content:
                        return content
        except Exception as e:
            logger.debug(f"Failed to read snippet fallback from {file_path}: {e}")
        return ""

    def add_plate(self, payload: Union[dict[str, Any], PlateNodePayload]) -> int:
        """Ingest a plate into the active canvas collection using explicit is not None parsing."""
        if isinstance(payload, PlateNodePayload):
            plate = payload
        elif isinstance(payload, dict):
            plate = parse_plate_payload(payload)
        else:
            raise TypeError(f"Expected dict or PlateNodePayload, got {type(payload).__name__}")

        if not plate.snippet and plate.file_path:
            fallback = self._read_snippet_fallback(plate.file_path)
            if fallback:
                plate.snippet = fallback

        self._plates[plate.node_id] = plate
        self.recalculate_bento()
        self.plateOpened.emit(plate.node_id)
        self.activePlatesChanged.emit()
        return plate.node_id

    @pyqtSlot("QVariantMap", result=int)
    def addPlate(self, payload: dict[str, Any]) -> int:
        return self.add_plate(payload)

    def _resolve_payload(self, target: Any) -> Optional[Dict[str, Any]]:
        """Resolves target (int, str, dict, or PlateNodePayload) into a hydrated dict payload."""
        if target is None:
            return None

        if not isinstance(target, (dict, PlateNodePayload, str)):
            try:
                evicted = self._evicted_payloads.get(int(target))
            except (ValueError, TypeError):
                evicted = None
            if evicted is not None:
                return dict(evicted)

        if isinstance(target, PlateNodePayload):
            payload = target.to_dict()
            file_path = payload.get("file_path") or payload.get("filePath")
            if not payload.get("snippet") and file_path:
                fallback = self._read_snippet_fallback(file_path)
                if fallback:
                    payload["snippet"] = fallback
            return payload

        if isinstance(target, dict):
            payload = dict(target)
            file_path = payload.get("file_path") or payload.get("filePath")
            if not payload.get("snippet") and file_path:
                fallback = self._read_snippet_fallback(file_path)
                if fallback:
                    payload["snippet"] = fallback
            return payload

        target_id: Optional[int] = None
        try:
            target_id = int(target)
        except (ValueError, TypeError):
            target_id = None

        payload = None
        db_path = Path.home() / ".config" / "aether" / "weaver_graph.db"
        if db_path.exists():
            try:
                with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                    cursor = conn.cursor()
                    if target_id is not None:
                        cursor.execute(
                            "SELECT id, file_path, file_hash, extension, size_bytes, archetype, snippet, thumbnail_url "
                            "FROM nodes WHERE id = ?;",
                            (target_id,),
                        )
                    else:
                        cursor.execute(
                            "SELECT id, file_path, file_hash, extension, size_bytes, archetype, snippet, thumbnail_url "
                            "FROM nodes WHERE file_path = ?;",
                            (str(target),),
                        )
                    row = cursor.fetchone()
                    if row:
                        payload = {
                            "id": row[0],
                            "file_path": row[1],
                            "file_hash": row[2],
                            "extension": row[3],
                            "size_bytes": row[4],
                            "archetype": row[5],
                            "snippet": row[6] or "",
                            "thumbnail_url": row[7] or "",
                        }
            except Exception as e:
                logger.warning(f"Failed to query SQLite for plate {target}: {e}")

        # Fallback to bridge store if available
        if payload is None and target_id is not None and hasattr(self.bridge, "store") and self.bridge.store:
            try:
                node = self.bridge.store.get_node(target_id)
                if node:
                    payload = {
                        "id": getattr(node, "id", target_id),
                        "file_path": getattr(node, "filePath", getattr(node, "path", "")),
                        "archetype": getattr(node, "archetype", "document"),
                        "snippet": getattr(node, "snippet", ""),
                        "size_bytes": getattr(node, "size_bytes", 0),
                    }
            except Exception:
                pass

        if payload is None:
            if target_id is not None:
                payload = {
                    "id": target_id,
                    "file_path": str(target),
                    "display_title": f"Plate {target_id}",
                }
            else:
                target_str = str(target)
                p = Path(target_str)
                gen_id = (zlib.crc32(target_str.encode("utf-8")) & 0x7FFFFFFF) or 1
                payload = {
                    "id": gen_id,
                    "file_path": target_str,
                    "file_name": p.name,
                    "display_title": p.name,
                    "extension": p.suffix,
                }

        file_path = payload.get("file_path") or payload.get("filePath")
        if not payload.get("snippet") and file_path:
            fallback = self._read_snippet_fallback(file_path)
            if fallback:
                payload["snippet"] = fallback

        return payload

    def _resolve_and_mount_plate(self, target: Any) -> int:
        """Resolves target (int, str, dict, or PlateNodePayload) and mounts it onto the canvas."""
        payload = self._resolve_payload(target)
        if not payload:
            return 0
        payload["is_preview"] = False
        payload["isPreview"] = False
        nid = self.add_plate(payload)
        self._plates[nid].temporal.touch()
        self.set_focal_plate(nid)
        self._restore_from_feed(nid)
        if self._enforce_capacity(protect_id=nid):
            self.recalculate_bento()
            self.activePlatesChanged.emit()
        return nid

    def _restore_from_feed(self, node_id: int) -> None:
        """Drops the feed history chip of a plate that has returned to the stage."""
        self._evicted_payloads.pop(int(node_id), None)
        feed_ctrl = getattr(self.bridge, "feed_ctrl", None)
        if feed_ctrl is not None:
            feed_ctrl.remove_history_chip(node_id)

    @property
    def capacity(self) -> int:
        """int: Dynamic stage capacity for unpinned plates, derived from stage width."""
        return self._bento_allocator.capacity

    def _enforce_capacity(self, protect_id: Optional[int] = None) -> bool:
        """
        Evicts the oldest unpinned plates (lowest last_interaction_epoch) into the feed
        until the unpinned plate count fits the stage capacity. Does not recalculate Bento.
        """
        capacity = self.capacity
        evicted_any = False
        while True:
            unpinned = [p for p in self._plates.values() if not p.temporal.is_pinned and not p.is_preview]
            if len(unpinned) <= capacity:
                break
            candidates = [p for p in unpinned if p.node_id != protect_id] or unpinned
            oldest = min(candidates, key=lambda p: p.temporal.last_interaction_epoch)
            self._evict_plate(oldest.node_id)
            evicted_any = True
        return evicted_any

    def _evict_plate(self, node_id: int) -> None:
        """Removes a plate from the stage and collapses it into the peripheral feed."""
        plate = self._plates.pop(node_id)
        self._bento_allocator.weight_overrides.pop(node_id, None)
        self._bento_allocator.height_overrides.pop(node_id, None)
        self._bento_allocator.row_anchors.pop(node_id, None)
        payload = plate.to_dict()
        self._evicted_payloads[node_id] = payload
        if self._focal_plate_id == node_id:
            self._focal_plate_id = 0
            self.focalPlateChanged.emit(0)
        feed_ctrl = getattr(self.bridge, "feed_ctrl", None)
        if feed_ctrl is not None:
            feed_ctrl.add_history_chip(payload)
        self.plateEvicted.emit(node_id)

    @pyqtSlot(str)
    def shelve_plate(self, plate_id: str) -> None:
        """Manually shelves a committed stage plate to the peripheral rail as a chip."""
        try:
            nid = int(plate_id)
        except (TypeError, ValueError):
            return
        plate = self._plates.get(nid)
        if plate is None or plate.is_preview:
            return
        self._evict_plate(nid)
        self.recalculate_bento()
        self.activePlatesChanged.emit()
        self.bentoGeometryChanged.emit()

    @pyqtSlot("QVariant")
    @pyqtSlot("QVariant", result=int)
    def preview_plate(self, target: Any) -> int:
        """Hydrates and mounts plate with is_preview=True, replacing existing transient previews."""
        if target is None:
            return 0

        payload = self._resolve_payload(target)
        if not payload:
            return 0

        payload["is_preview"] = True
        payload["isPreview"] = True

        target_id: Optional[int] = None
        raw_id = payload.get("id") or payload.get("node_id") or payload.get("nodeId")
        if raw_id is not None:
            try:
                target_id = int(raw_id)
            except (ValueError, TypeError):
                target_id = None

        # If a committed plate with this ID already exists, do not overwrite it with a preview
        if target_id is not None and target_id in self._plates and not getattr(self._plates[target_id], "is_preview", False):
            preview_ids = [nid for nid, p in self._plates.items() if getattr(p, "is_preview", False)]
            for pid in preview_ids:
                del self._plates[pid]
                self.plateClosed.emit(pid)
            if preview_ids:
                self.recalculate_bento()
                self.activePlatesChanged.emit()
            return target_id

        # Replace any existing transient preview plate (except if it matches target_id)
        preview_ids = [nid for nid, p in self._plates.items() if getattr(p, "is_preview", False)]
        removed_any = False
        for pid in preview_ids:
            if target_id is not None and pid == target_id:
                continue
            del self._plates[pid]
            if self._focal_plate_id == pid:
                self._focal_plate_id = 0
                self.focalPlateChanged.emit(0)
            self.plateClosed.emit(pid)
            removed_any = True

        # If target is already the active preview plate, return it
        if target_id is not None and target_id in self._plates and getattr(self._plates[target_id], "is_preview", False):
            if removed_any:
                self.recalculate_bento()
                self.activePlatesChanged.emit()
            return target_id

        plate = parse_plate_payload(payload)
        plate.is_preview = True
        if plate.metadata is None:
            plate.metadata = {}
        plate.metadata["is_preview"] = True
        plate.metadata["isPreview"] = True

        if not plate.snippet and plate.file_path:
            fallback = self._read_snippet_fallback(plate.file_path)
            if fallback:
                plate.snippet = fallback

        self._plates[plate.node_id] = plate
        self.recalculate_bento()
        self.plateOpened.emit(plate.node_id)
        self.activePlatesChanged.emit()
        return plate.node_id

    @pyqtSlot("QVariant")
    @pyqtSlot("QVariant", result=int)
    def previewPlate(self, target: Any) -> int:
        return self.preview_plate(target)

    @pyqtSlot()
    def clear_preview(self) -> None:
        """Removes any plate where is_preview == True."""
        preview_ids = [nid for nid, p in self._plates.items() if getattr(p, "is_preview", False)]
        if not preview_ids:
            return
        for pid in preview_ids:
            del self._plates[pid]
            if self._focal_plate_id == pid:
                self._focal_plate_id = 0
                self.focalPlateChanged.emit(0)
            self.plateClosed.emit(pid)
        self.recalculate_bento()
        self.activePlatesChanged.emit()

    @pyqtSlot()
    def clearPreview(self) -> None:
        self.clear_preview()

    @pyqtSlot("QVariant", result=int)
    def open_plate(self, target: Any) -> int:
        """Mounts and activates a plate by ID, file path, or payload dict."""
        if target is None:
            return 0

        target_id: Optional[int] = None
        target_path: Optional[str] = None
        if isinstance(target, PlateNodePayload):
            target_id = target.node_id
            target_path = target.file_path
        elif isinstance(target, dict):
            raw_id = target.get("node_id") if target.get("node_id") is not None else target.get("id")
            if raw_id is None:
                raw_id = target.get("nodeId")
            try:
                target_id = int(raw_id) if raw_id is not None else None
            except (ValueError, TypeError):
                target_id = None
            target_path = target.get("file_path") or target.get("filePath") or target.get("path")
        else:
            try:
                target_id = int(target)
            except (ValueError, TypeError):
                target_id = None
                target_path = str(target)

        # Check if matching preview plate exists to convert to committed
        matching_plate: Optional[PlateNodePayload] = None
        if target_id is not None and target_id in self._plates:
            matching_plate = self._plates[target_id]
        elif target_path:
            for p in self._plates.values():
                if p.file_path == target_path:
                    matching_plate = p
                    break

        if matching_plate is not None:
            if getattr(matching_plate, "is_preview", False):
                matching_plate.is_preview = False
                if matching_plate.metadata is not None:
                    matching_plate.metadata["is_preview"] = False
                    matching_plate.metadata["isPreview"] = False
            matching_plate.temporal.touch()
            self.set_focal_plate(matching_plate.node_id)

            other_previews = [pid for pid, p in self._plates.items() if pid != matching_plate.node_id and getattr(p, "is_preview", False)]
            for pid in other_previews:
                del self._plates[pid]
                self.plateClosed.emit(pid)
            evicted = self._enforce_capacity(protect_id=matching_plate.node_id)
            if other_previews or evicted:
                self.recalculate_bento()

            self.plateOpened.emit(matching_plate.node_id)
            self.activePlatesChanged.emit()
            return matching_plate.node_id

        # Clear any other preview plates before opening a new plate
        preview_ids = [pid for pid, p in self._plates.items() if getattr(p, "is_preview", False)]
        for pid in preview_ids:
            del self._plates[pid]
            if self._focal_plate_id == pid:
                self._focal_plate_id = 0
                self.focalPlateChanged.emit(0)
            self.plateClosed.emit(pid)

        nid = self._resolve_and_mount_plate(target)
        return nid

    @pyqtSlot("QVariant", result=int)
    def openPlate(self, target: Any) -> int:
        """Alias for open_plate accommodating camelCase and varied argument types."""
        return self._resolve_and_mount_plate(target)

    @pyqtSlot(int)
    def set_focal_plate(self, node_id: int) -> None:
        """Sets the active focal plate ID."""
        nid = int(node_id)
        if self._focal_plate_id != nid:
            self._focal_plate_id = nid
            if nid in self._plates:
                self._plates[nid].temporal.touch()
            self.focalPlateChanged.emit(nid)

    @pyqtSlot(int)
    def setFocalPlate(self, node_id: int) -> None:
        self.set_focal_plate(node_id)

    @pyqtSlot(int)
    def selectPlate(self, node_id: int) -> None:
        """Focuses a plate on stage and refreshes its interaction timestamp."""
        nid = int(node_id)
        if nid == 0:
            # Stage 0 equilibrium: drop focus without touching any plate
            if self._focal_plate_id != 0:
                self._focal_plate_id = 0
                self.focalPlateChanged.emit(0)
                self.bentoGeometryChanged.emit()
            return
        plate = self._plates.get(nid)
        if plate is None:
            return
        plate.temporal.touch()
        self._focal_plate_id = nid
        self.focalPlateChanged.emit(nid)
        self.activePlatesChanged.emit()

    def get_plate(self, node_id: int) -> Optional[PlateNodePayload]:
        return self._plates.get(int(node_id))

    # -------------------------------------------------------------------------
    # Bento Grid Management
    # -------------------------------------------------------------------------

    @pyqtSlot()
    def recalculate_bento(self) -> None:
        """Recalculates Bento grid geometry across all active plates."""
        if not self._plates:
            self._bento_allocations = []
            self.bentoGeometryChanged.emit()
            return

        plates_list = list(self._plates.values())
        allocations = self._bento_allocator.allocate(plates_list)
        self._bento_allocations = allocations
        self.bentoGeometryChanged.emit()

    @pyqtSlot(int, float)
    def adjust_plate_weight(self, node_id: int, delta_ratio: float) -> None:
        """
        Elastic gutter drag: shifts `delta_ratio` of row width between a plate and its right
        neighbour (floor ~0.15 of the row). The last plate of a row instead grows rightward into the
        stage margin with its left edge anchored. A neighbour squeezed below the floor is evicted
        to the feed rail as a history chip. Recalculates Bento and emits bentoGeometryChanged.
        """
        nid = int(node_id)
        if nid not in self._plates or float(delta_ratio) == 0.0:
            return
        evict_id = self._bento_allocator.adjust_weight(list(self._plates.values()), nid, float(delta_ratio))
        if evict_id is not None and evict_id in self._plates:
            self._evict_plate(evict_id)
            self.recalculate_bento()
            self.activePlatesChanged.emit()
            return
        self.recalculate_bento()

    @pyqtSlot(int, float, float)
    def resize_plate_proportional(self, node_id: int, delta_w: float, delta_h: float) -> None:
        """
        Diagonal corner resize. `delta_w` / `delta_h` are ratios of stage width / height.
        Width shifts row share from the immediate row neighbour (evicting it below the 0.15 floor); the
        last plate of a row expands rightward (left edge anchored) until the stage margin, only then
        compressing its left neighbour;
        height changes only this plate (row neighbours keep their own heights), compressing other rows toward their legible floor. Any
        unpinned plate squeezed below the floor or pushed off-stage is evicted (oldest interaction
        first, pinned plates immune) and the layout is re-run with the remaining plates.
        """
        nid = int(node_id)
        dw, dh = float(delta_w), float(delta_h)
        target = self._plates.get(nid)
        if target is None or (dw == 0.0 and dh == 0.0):
            return
        target.temporal.touch()
        allocator = self._bento_allocator
        evicted_any = False

        if dw != 0.0:
            pinned = [p.node_id for p in self._plates.values() if p.temporal.is_pinned]
            evict_id = allocator.adjust_weight(list(self._plates.values()), nid, dw, protected=pinned)
            if evict_id is not None and evict_id in self._plates:
                self._evict_plate(evict_id)
                evicted_any = True

        if dh != 0.0 and allocator.adjust_height(list(self._plates.values()), nid, dh):
            while allocator.rows_overflow(list(self._plates.values())):
                candidates = [
                    p for p in self._plates.values()
                    if p.node_id != nid and not p.temporal.is_pinned and not p.is_preview
                ]
                if not candidates:
                    allocator.fit_height(list(self._plates.values()), nid)
                    break
                oldest = min(candidates, key=lambda p: p.temporal.last_interaction_epoch)
                self._evict_plate(oldest.node_id)
                evicted_any = True
            if nid in self._plates:
                allocator.fit_height(list(self._plates.values()), nid)

        self.recalculate_bento()
        # Membership changes rebuild the Repeater (destroying the dragged card); pure resizes must not
        if evicted_any:
            self.activePlatesChanged.emit()

    @pyqtSlot()
    def recalculateBento(self) -> None:
        self.recalculate_bento()

    @pyqtSlot(float, float)
    def set_viewport_dimensions(self, width: float, height: float) -> None:
        """Update viewport dimensions for Bento grid calculations."""
        w = max(480.0, float(width))
        h = max(320.0, float(height))

        if (
            abs(self._bento_config.viewport_width - w) > 1.0
            or abs(self._bento_config.viewport_height - h) > 1.0
        ):
            self._bento_config.viewport_width = w
            self._bento_config.viewport_height = h
            evicted = self._enforce_capacity()
            self.recalculate_bento()
            if evicted:
                self.activePlatesChanged.emit()

    @pyqtSlot(float, float)
    def setViewportDimensions(self, width: float, height: float) -> None:
        self.set_viewport_dimensions(width, height)

    # -------------------------------------------------------------------------
    # Clear & Reset
    # -------------------------------------------------------------------------

    @pyqtSlot()
    def clear_all(self) -> None:
        """Clears all active plates and resets focal stage."""
        self._plates.clear()
        self._evicted_payloads.clear()
        self._bento_allocator.weight_overrides.clear()
        self._bento_allocator.height_overrides.clear()
        self._bento_allocator.row_anchors.clear()
        self._bento_allocations.clear()
        self._focal_plate_id = 0
        self.focalPlateChanged.emit(0)
        self.bentoGeometryChanged.emit()
        self.activePlatesChanged.emit()

    @pyqtSlot()
    def clearAll(self) -> None:
        self.clear_all()

