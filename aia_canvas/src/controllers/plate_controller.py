"""
Plate Canvas Controller Implementation
Post-WIMP spatial layout, Bento grid geometry, single-key AI summary extraction,
and plate spatial manipulation for the Aether presentation layer.
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

    def add_plate(self, payload: Union[dict[str, Any], PlateNodePayload]) -> int:
        """Ingest a plate into the active canvas collection using explicit is not None parsing."""
        if isinstance(payload, PlateNodePayload):
            plate = payload
        elif isinstance(payload, dict):
            plate = parse_plate_payload(payload)
        else:
            raise TypeError(f"Expected dict or PlateNodePayload, got {type(payload).__name__}")

        self._plates[plate.node_id] = plate
        self.recalculate_bento()
        self.plateOpened.emit(plate.node_id)
        self.activePlatesChanged.emit()
        return plate.node_id

    @pyqtSlot("QVariantMap", result=int)
    def addPlate(self, payload: dict[str, Any]) -> int:
        return self.add_plate(payload)

    @pyqtSlot("QVariantMap", result=int)
    def openPlate(self, payload: dict[str, Any]) -> int:
        return self.add_plate(payload)

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
            self.recalculate_bento()

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
        self._bento_allocations.clear()
        self._focal_plate_id = 0
        self.focalPlateChanged.emit(0)
        self.bentoGeometryChanged.emit()
        self.activePlatesChanged.emit()

    @pyqtSlot()
    def clearAll(self) -> None:
        self.clear_all()

