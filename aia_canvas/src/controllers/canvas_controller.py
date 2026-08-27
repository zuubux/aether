"""
Canvas Controller Implementation
Manages viewport dimensions, central workbench geometry, wing widths, zoom aperture state, and telemetry metrics.
"""

from typing import Optional
from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from core.telemetry import TelemetrySink
from .base_controller import BaseController


class CanvasController(BaseController):
    """Controller managing viewport coordinates, workbench dimensions, wing width, and viewport aperture state."""

    workbenchDimensionsChanged = pyqtSignal()
    apertureChanged = pyqtSignal(float)
    telemetryChanged = pyqtSignal()

    def __init__(self, bridge, parent: Optional[object] = None):
        """Initialize CanvasController with parent bridge reference.

        Args:
            bridge: CanvasBridge instance owning application state.
            parent: Optional QObject parent.
        """
        super().__init__(bridge, parent)
        self._aperture: float = 1.0
        self._workbench_width: float = 1600.0
        self._workbench_height: float = 1000.0

    @pyqtProperty(float, notify=telemetryChanged)
    def physicsStepMs(self) -> float:
        return TelemetrySink.instance().physics_step_ms

    @pyqtProperty(float, notify=telemetryChanged)
    def renderFps(self) -> float:
        return TelemetrySink.instance().render_fps

    @pyqtProperty(float, notify=telemetryChanged)
    def ipcRttMs(self) -> float:
        return TelemetrySink.instance().ipc_rtt_ms

    @pyqtProperty(float, notify=telemetryChanged)
    def dbQueryMs(self) -> float:
        return TelemetrySink.instance().db_query_ms

    @pyqtProperty(float, notify=telemetryChanged)
    def llmTtftMs(self) -> float:
        return TelemetrySink.instance().llm_ttft_ms

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def workbenchWidth(self) -> float:
        """float: Central focal workbench width in canvas units."""
        return self._workbench_width

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def workbenchHeight(self) -> float:
        """float: Central focal workbench height in canvas units."""
        return self._workbench_height

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def wingWidth(self) -> float:
        """float: Lateral wing margin width computed from viewport dimensions."""
        if hasattr(self.bridge, 'physics') and self.bridge.physics:
            return (self.bridge.physics_engine.viewport_w - self._workbench_width) / 2.0
        return 0.0

    @pyqtProperty(float, notify=apertureChanged)
    def aperture(self) -> float:
        """float: Active viewport aperture zoom ratio [0.20, 2.20]."""
        return self._aperture

    @pyqtSlot(float, float)
    def set_workbench_dimensions(self, width: float, height: float) -> None:
        """Update central workbench card dimensions and notify physics layout.

        Args:
            width: Target workbench width.
            height: Target workbench height.
        """
        if hasattr(self.bridge, '_wake_physics'):
            self.bridge._wake_physics()

        clamped_w = max(480.0, min(2600.0, width))
        clamped_h = max(320.0, min(1600.0, height))

        if abs(self._workbench_width - clamped_w) > 1.0 or abs(self._workbench_height - clamped_h) > 1.0:
            self._workbench_width = clamped_w
            self._workbench_height = clamped_h
            if hasattr(self.bridge, 'physics') and self.bridge.physics:
                self.bridge.physics_engine.set_focal_card_dimensions(clamped_w, clamped_h)
            self.workbenchDimensionsChanged.emit()

    @pyqtSlot(float, float)
    def update_viewport_dimensions(self, width: float, height: float) -> None:
        """Update physical viewport canvas bounds.

        Args:
            width: Outer viewport width in pixels.
            height: Outer viewport height in pixels.
        """
        if hasattr(self.bridge, '_wake_physics'):
            self.bridge._wake_physics()
        if hasattr(self.bridge, 'physics') and self.bridge.physics:
            self.bridge.physics_engine.set_viewport_dimensions(width, height)
        self.workbenchDimensionsChanged.emit()

    @pyqtSlot(float)
    def adjust_aperture(self, delta: float) -> None:
        """Increment or decrement active aperture ratio by delta.

        Args:
            delta: Relative change in aperture ratio.
        """
        new_val = max(0.20, min(2.20, self._aperture + delta))
        if abs(new_val - self._aperture) > 0.005:
            self._aperture = new_val
            if hasattr(self.bridge, 'physics') and self.bridge.physics:
                self.bridge.physics_engine.set_aperture(new_val)
            self.apertureChanged.emit(new_val)
            if hasattr(self.bridge, '_wake_physics'):
                self.bridge._wake_physics()

    @pyqtSlot(float)
    def set_aperture(self, value: float) -> None:
        """Set absolute aperture ratio within bounds [0.20, 2.20].

        Args:
            value: Target aperture float value.
        """
        new_val = max(0.20, min(2.20, value))
        if abs(new_val - self._aperture) > 0.005:
            self._aperture = new_val
            if hasattr(self.bridge, 'physics') and self.bridge.physics:
                self.bridge.physics_engine.set_aperture(new_val)
            self.apertureChanged.emit(new_val)
            if hasattr(self.bridge, '_wake_physics'):
                self.bridge._wake_physics()
